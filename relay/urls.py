from django.urls import path
from .views import SendSMSView, WebhookView, HomeView, DashboardView, APIDocsView, StandardSMSView, StandardWhatsAppView, StandardCallView
from .health_views import HealthCheckView, DiagnosticView
# TwilioMessagesView and TwilioCallsView can be imported if we want to keep them, but user said "I don't need this kind of endpoints"

urlpatterns = [
    # Health & Diagnostics (no auth required for health)
    path('api/health', HealthCheckView.as_view(), name='api_health'),
    path('api/diagnostic', DiagnosticView.as_view(), name='api_diagnostic'),
    
    # Standard Simplified APIs
    path('api/sms', StandardSMSView.as_view(), name='api_sms'),
    path('api/whatsapp', StandardWhatsAppView.as_view(), name='api_whatsapp'),
    path('api/call', StandardCallView.as_view(), name='api_call'),

    # Webhook
    path('twilio/webhook', WebhookView.as_view(), name='twilio_webhook'),
]
