from django.contrib import admin
from .models import Client, APIKey, TwilioAccount, RoutingRule, CommunicationLog, AuditLog

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'company_name', 'balance', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'email', 'company_name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('client', 'prefix', 'allow_sms', 'allow_voice', 'allow_whatsapp', 'is_active', 'created_at')
    list_filter = ('is_active', 'allow_sms', 'allow_voice', 'allow_whatsapp', 'created_at')
    search_fields = ('client__name', 'prefix')
    readonly_fields = ('created_at', 'key_hash')

@admin.register(TwilioAccount)
class TwilioAccountAdmin(admin.ModelAdmin):
    list_display = ('sid', 'name', 'phone_number', 'capability_sms', 'capability_voice', 'capability_whatsapp')
    list_filter = ('capability_sms', 'capability_voice', 'capability_whatsapp')
    search_fields = ('sid', 'name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(RoutingRule)
class RoutingRuleAdmin(admin.ModelAdmin):
    list_display = ('priority', 'pattern', 'account', 'description')
    list_filter = ('account',)
    search_fields = ('pattern', 'description')
    ordering = ('priority',)

@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'communication_type', 'client', 'to_number', 'from_number', 'status', 'cost', 'error_message')
    list_filter = ('communication_type', 'status', 'created_at')
    search_fields = ('to_number', 'from_number', 'twilio_sid', 'client__name', 'error_message')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('client', 'api_key', 'account')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'ip_address', 'user_agent')
    list_filter = ('timestamp',)
    search_fields = ('action', 'details', 'ip_address')
    readonly_fields = ('timestamp',)
