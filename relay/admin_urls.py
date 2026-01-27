from django.urls import path
from . import admin_views

app_name = 'admin_dashboard'

urlpatterns = [
    # Dashboard Home
    path('', admin_views.AdminDashboardView.as_view(), name='dashboard'),
    
    # Client Management
    path('clients/', admin_views.ClientListView.as_view(), name='client_list'),
    path('clients/create/', admin_views.ClientCreateView.as_view(), name='client_create'),
    path('clients/<int:pk>/edit/', admin_views.ClientUpdateView.as_view(), name='client_edit'),
    path('clients/<int:pk>/delete/', admin_views.ClientDeleteView.as_view(), name='client_delete'),
    path('clients/<int:pk>/balance/', admin_views.ClientBalanceAdjustView.as_view(), name='client_balance'),
    
    # Twilio Account Management
    path('twilio-accounts/', admin_views.TwilioAccountListView.as_view(), name='twilio_account_list'),
    path('twilio-accounts/create/', admin_views.TwilioAccountCreateView.as_view(), name='twilio_account_create'),
    path('twilio-accounts/<str:pk>/edit/', admin_views.TwilioAccountUpdateView.as_view(), name='twilio_account_edit'),
    path('twilio-accounts/<str:pk>/delete/', admin_views.TwilioAccountDeleteView.as_view(), name='twilio_account_delete'),
    
    # Routing Rule Management
    path('routing-rules/', admin_views.RoutingRuleListView.as_view(), name='routing_rule_list'),
    path('routing-rules/create/', admin_views.RoutingRuleCreateView.as_view(), name='routing_rule_create'),
    path('routing-rules/<int:pk>/edit/', admin_views.RoutingRuleUpdateView.as_view(), name='routing_rule_edit'),
    path('routing-rules/<int:pk>/delete/', admin_views.RoutingRuleDeleteView.as_view(), name='routing_rule_delete'),
    
    # API Key Management
    path('api-keys/', admin_views.APIKeyListView.as_view(), name='apikey_list'),
    path('api-keys/generate/', admin_views.APIKeyGenerateView.as_view(), name='apikey_generate'),
    path('api-keys/<int:pk>/edit/', admin_views.APIKeyUpdateView.as_view(), name='apikey_edit'),
    path('api-keys/<int:pk>/revoke/', admin_views.APIKeyRevokeView.as_view(), name='apikey_revoke'),
    
    # System Monitoring
    path('monitoring/', admin_views.SystemMonitoringView.as_view(), name='monitoring'),
    
    # Communication & Audit Logs
    path('history/', admin_views.CommunicationHistoryView.as_view(), name='communication_history'),
    path('audit-logs/', admin_views.AuditLogListView.as_view(), name='audit_log_list'),
]
