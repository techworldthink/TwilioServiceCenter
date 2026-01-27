from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.views import View
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from decimal import Decimal

from .models import Client, APIKey, TwilioAccount, RoutingRule, CommunicationLog, AuditLog
from .forms import (
    ClientForm, TwilioAccountForm, RoutingRuleForm, 
    APIKeyGenerateForm, APIKeyUpdateForm, BalanceAdjustmentForm
)
from .services import LogService
from .decorators import ajax_required


class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin to require staff status for admin views"""
    login_url = '/admin/login/'
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff


# ============================================================================
# Dashboard Home
# ============================================================================

class AdminDashboardView(StaffRequiredMixin, TemplateView):
    """Main admin dashboard with statistics and overview"""
    template_name = 'admin/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        context['total_clients'] = Client.objects.count()
        context['active_api_keys'] = APIKey.objects.filter(is_active=True).count()
        context['total_twilio_accounts'] = TwilioAccount.objects.count()
        context['total_routing_rules'] = RoutingRule.objects.count()
        
        # Total balance across all clients
        total_balance = Client.objects.aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')
        context['total_balance'] = total_balance
        
        # Recent clients
        context['recent_clients'] = Client.objects.order_by('-created_at')[:5]
        
        # Recent API keys
        context['recent_api_keys'] = APIKey.objects.select_related('client').order_by('-created_at')[:5]
        
        # Recent Communications
        context['recent_communications'] = CommunicationLog.objects.select_related('client').order_by('-created_at')[:5]
        
        # Low balance clients (less than $10)
        context['low_balance_clients'] = Client.objects.filter(balance__lt=10).order_by('balance')[:5]
        
        return context


# ============================================================================
# Client Management
# ============================================================================

class ClientListView(StaffRequiredMixin, ListView):
    """List all clients with search and filter"""
    model = Client
    template_name = 'admin/client_list.html'
    context_object_name = 'clients'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Client.objects.annotate(
            active_keys_count=Count('api_keys', filter=Q(api_keys__is_active=True))
        ).order_by('-created_at')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset


class ClientCreateView(StaffRequiredMixin, CreateView):
    """Create a new client"""
    model = Client
    form_class = ClientForm
    template_name = 'admin/client_form.html'
    success_url = reverse_lazy('admin_dashboard:client_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        LogService.log_action(
            action="Create Client",
            details=f"Created client {form.instance.name}",
            request=self.request
        )
        messages.success(self.request, f'Client "{form.instance.name}" created successfully!')
        return response


class ClientUpdateView(StaffRequiredMixin, UpdateView):
    """Update an existing client"""
    model = Client
    form_class = ClientForm
    template_name = 'admin/client_form.html'
    success_url = reverse_lazy('admin_dashboard:client_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        LogService.log_action(
            action="Update Client",
            details=f"Updated client {form.instance.name}",
            request=self.request
        )
        messages.success(self.request, f'Client "{form.instance.name}" updated successfully!')
        return response


class ClientDeleteView(StaffRequiredMixin, DeleteView):
    """Delete a client"""
    model = Client
    template_name = 'admin/client_confirm_delete.html'
    success_url = reverse_lazy('admin_dashboard:client_list')
    
    def delete(self, request, *args, **kwargs):
        client = self.get_object()
        LogService.log_action(
            action="Delete Client",
            details=f"Deleted client {client.name}",
            request=request
        )
        messages.success(request, f'Client "{client.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


class ClientBalanceAdjustView(StaffRequiredMixin, View):
    """Adjust client balance"""
    
    def get(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = BalanceAdjustmentForm()
        return render(request, 'admin/balance_adjust.html', {
            'client': client,
            'form': form,
        })
    
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = BalanceAdjustmentForm(request.POST)
        
        if form.is_valid():
            adjustment_type = form.cleaned_data['adjustment_type']
            amount = form.cleaned_data['amount']
            note = form.cleaned_data.get('note', '')
            
            old_balance = client.balance
            new_balance = client.adjust_balance(amount, adjustment_type)
            
            LogService.log_action(
                action="Adjust Balance",
                details=f"Adjusted balance for {client.name} ({adjustment_type} {amount})",
                request=request
            )
            messages.success(
                request, 
                f'Balance adjusted for "{client.name}": ${old_balance} → ${new_balance}'
            )
            return redirect('admin_dashboard:client_list')
        
        return render(request, 'admin/balance_adjust.html', {
            'client': client,
            'form': form,
        })


# ============================================================================
# Twilio Account Management
# ============================================================================

class TwilioAccountListView(StaffRequiredMixin, ListView):
    """List all Twilio accounts"""
    model = TwilioAccount
    template_name = 'admin/twilio_account_list.html'
    context_object_name = 'accounts'
    
    def get_queryset(self):
        return TwilioAccount.objects.annotate(
            routing_rules_count=Count('routing_rules')
        ).order_by('-created_at')


class TwilioAccountCreateView(StaffRequiredMixin, CreateView):
    """Create a new Twilio account"""
    model = TwilioAccount
    form_class = TwilioAccountForm
    template_name = 'admin/twilio_account_form.html'
    success_url = reverse_lazy('admin_dashboard:twilio_account_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        LogService.log_action(
            action="Add Twilio Account",
            details=f"Added Twilio account {form.instance.sid}",
            request=self.request
        )
        messages.success(self.request, f'Twilio account "{form.instance.sid}" added successfully!')
        return response


class TwilioAccountUpdateView(StaffRequiredMixin, UpdateView):
    """Update an existing Twilio account"""
    model = TwilioAccount
    form_class = TwilioAccountForm
    template_name = 'admin/twilio_account_form.html'
    success_url = reverse_lazy('admin_dashboard:twilio_account_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        LogService.log_action(
            action="Update Twilio Account",
            details=f"Updated Twilio account {form.instance.sid}",
            request=self.request
        )
        messages.success(self.request, f'Twilio account "{form.instance.sid}" updated successfully!')
        return response


class TwilioAccountDeleteView(StaffRequiredMixin, DeleteView):
    """Delete a Twilio account"""
    model = TwilioAccount
    template_name = 'admin/twilio_account_confirm_delete.html'
    success_url = reverse_lazy('admin_dashboard:twilio_account_list')
    
    def delete(self, request, *args, **kwargs):
        account = self.get_object()
        messages.success(request, f'Twilio account "{account.sid}" deleted successfully!')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# Routing Rule Management
# ============================================================================

class RoutingRuleListView(StaffRequiredMixin, ListView):
    """List all routing rules"""
    model = RoutingRule
    template_name = 'admin/routing_rule_list.html'
    context_object_name = 'rules'
    
    def get_queryset(self):
        return RoutingRule.objects.select_related('account').order_by('priority')


class RoutingRuleCreateView(StaffRequiredMixin, CreateView):
    """Create a new routing rule"""
    model = RoutingRule
    form_class = RoutingRuleForm
    template_name = 'admin/routing_rule_form.html'
    success_url = reverse_lazy('admin_dashboard:routing_rule_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Routing rule created successfully!')
        return super().form_valid(form)


class RoutingRuleUpdateView(StaffRequiredMixin, UpdateView):
    """Update an existing routing rule"""
    model = RoutingRule
    form_class = RoutingRuleForm
    template_name = 'admin/routing_rule_form.html'
    success_url = reverse_lazy('admin_dashboard:routing_rule_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Routing rule updated successfully!')
        return super().form_valid(form)


class RoutingRuleDeleteView(StaffRequiredMixin, DeleteView):
    """Delete a routing rule"""
    model = RoutingRule
    template_name = 'admin/routing_rule_confirm_delete.html'
    success_url = reverse_lazy('admin_dashboard:routing_rule_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Routing rule deleted successfully!')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# API Key Management
# ============================================================================

class APIKeyListView(StaffRequiredMixin, ListView):
    """List all API keys"""
    model = APIKey
    template_name = 'admin/apikey_list.html'
    context_object_name = 'api_keys'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = APIKey.objects.select_related('client').order_by('-created_at')
        
        # Filter by client if specified
        client_id = self.request.GET.get('client')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'revoked':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clients'] = Client.objects.all()
        return context


class APIKeyGenerateView(StaffRequiredMixin, View):
    """Generate a new API key"""
    
    def get(self, request):
        form = APIKeyGenerateForm()
        return render(request, 'admin/apikey_generate.html', {'form': form})
    
    def post(self, request):
        form = APIKeyGenerateForm(request.POST)
        
        if form.is_valid():
            client = form.cleaned_data['client']
            prefix = form.cleaned_data.get('prefix')
            
            # Extract permissions and forced settings
            kwargs = {
                'forced_account': form.cleaned_data.get('forced_account'),
                'allow_sms': form.cleaned_data.get('allow_sms', True),
                'allow_voice': form.cleaned_data.get('allow_voice', True),
                'allow_whatsapp': form.cleaned_data.get('allow_whatsapp', True),
            }
            
            # Generate the key with granular permissions
            api_key, plain_key = APIKey.generate_key(client, prefix, **kwargs)
            
            LogService.log_action(
                action="Generate API Key",
                details=f"Generated API key {api_key.prefix}... for {client.name}",
                request=request
            )
            
            messages.success(
                request,
                f'API key generated successfully for "{client.name}"!'
            )
            
            # Show the plain key (only time it's visible)
            return render(request, 'admin/apikey_generated.html', {
                'api_key': api_key,
                'plain_key': plain_key,
                'client': client,
            })
        
        return render(request, 'admin/apikey_generate.html', {'form': form})


class APIKeyUpdateView(StaffRequiredMixin, UpdateView):
    """Update an existing API key"""
    model = APIKey
    form_class = APIKeyUpdateForm
    template_name = 'admin/apikey_form.html'
    success_url = reverse_lazy('admin_dashboard:apikey_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'API key settings for "{form.instance.prefix}..." updated successfully!')
        return super().form_valid(form)


class APIKeyRevokeView(StaffRequiredMixin, View):
    """Revoke an API key"""
    
    def post(self, request, pk):
        api_key = get_object_or_404(APIKey, pk=pk)
        api_key.revoke()
        
        messages.success(
            request,
            f'API key "{api_key.prefix}..." for "{api_key.client.name}" has been revoked.'
        )
        
        return redirect('admin_dashboard:apikey_list')


# ============================================================================
# System Monitoring
# ============================================================================

class SystemMonitoringView(StaffRequiredMixin, TemplateView):
    """System monitoring and statistics"""
    template_name = 'admin/system_monitoring.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # System statistics
        context['stats'] = {
            'total_clients': Client.objects.count(),
            'active_clients': Client.objects.filter(balance__gt=0).count(),
            'total_api_keys': APIKey.objects.count(),
            'active_api_keys': APIKey.objects.filter(is_active=True).count(),
            'revoked_api_keys': APIKey.objects.filter(is_active=False).count(),
            'total_twilio_accounts': TwilioAccount.objects.count(),
            'total_routing_rules': RoutingRule.objects.count(),
            'total_balance': Client.objects.aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00'),
        }
        
        # Top clients by balance
        context['top_clients'] = Client.objects.order_by('-balance')[:10]
        
        # Clients with most API keys
        context['clients_by_keys'] = Client.objects.annotate(
            keys_count=Count('api_keys')
        ).order_by('-keys_count')[:10]
        
        return context


# ============================================================================
# Communication & Audit Logs
# ============================================================================

class CommunicationHistoryView(StaffRequiredMixin, ListView):
    """View all communication logs with filtering"""
    model = CommunicationLog
    template_name = 'admin/communication_history.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        queryset = CommunicationLog.objects.select_related('client', 'account').all()
        
        # Filter by type
        comm_type = self.request.GET.get('type')
        if comm_type:
            queryset = queryset.filter(communication_type=comm_type)
            
        # Filter by client
        client_id = self.request.GET.get('client')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
            
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(twilio_sid__icontains=search) | 
                Q(to_number__icontains=search) | 
                Q(body__icontains=search)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current filter values
        selected_type = self.request.GET.get('type', '')
        selected_client = self.request.GET.get('client', '')
        selected_status = self.request.GET.get('status', '')
        
        # Prepare list of clients with selected state
        context['clients_options'] = [
            {
                'id': str(c.id), 
                'name': c.name, 
                'selected': str(c.id) == selected_client
            } for c in Client.objects.all()
        ]
        
        # Prepare list of communication types with selected state
        context['comm_types_options'] = [
            {
                'code': code, 
                'name': name, 
                'selected': code == selected_type
            } for code, name in CommunicationLog.COMM_TYPES
        ]
        
        # Prepare status options with selected state
        status_choices = [
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('failed', 'Failed'),
            ('pending', 'Pending'),
        ]
        context['status_options'] = [
            {
                'code': code, 
                'name': name, 
                'selected': code == selected_status
            } for code, name in status_choices
        ]
        
        return context


class AuditLogListView(StaffRequiredMixin, ListView):
    """View all audit logs with search"""
    model = AuditLog
    template_name = 'admin/audit_log_list.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        queryset = AuditLog.objects.all()
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(action__icontains=search) | 
                Q(details__icontains=search)
            )
            
        return queryset
