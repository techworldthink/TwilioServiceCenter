from django.db import models
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import secrets
import hashlib

class Client(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    balance = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    def get_active_api_keys_count(self):
        return self.api_keys.filter(is_active=True).count()
    
    def adjust_balance(self, amount, adjustment_type='add'):
        if adjustment_type == 'add':
            self.balance += amount
        elif adjustment_type == 'deduct':
            self.balance -= amount
        elif adjustment_type == 'set':
            self.balance = amount
        self.save()
        return self.balance

class APIKey(models.Model):
    client = models.ForeignKey(Client, related_name='api_keys', on_delete=models.CASCADE)
    key_hash = models.CharField(max_length=128, db_index=True)
    prefix = models.CharField(max_length=8)
    allow_sms = models.BooleanField(default=True)
    allow_voice = models.BooleanField(default=True)
    allow_whatsapp = models.BooleanField(default=True)
    forced_account = models.ForeignKey('TwilioAccount', null=True, blank=True, on_delete=models.SET_NULL, related_name='forced_keys')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client.name} - {self.prefix}..."
    
    @staticmethod
    def generate_key(client, custom_prefix=None, **kwargs):
        plain_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        prefix = custom_prefix if custom_prefix else plain_key[:8]
        api_key = APIKey.objects.create(
            client=client,
            key_hash=key_hash,
            prefix=prefix,
            is_active=True,
            **kwargs
        )
        return api_key, plain_key
    
    def revoke(self):
        self.is_active = False
        self.save()

class TwilioAccount(models.Model):
    sid = models.CharField(max_length=64, primary_key=True)
    encrypted_token = models.TextField()
    name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    description = models.CharField(max_length=255, blank=True)
    capability_sms = models.BooleanField(default=True)
    capability_voice = models.BooleanField(default=True)
    capability_whatsapp = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_token(self, token):
        f = Fernet(settings.MASTER_ENCRYPTION_KEY)
        self.encrypted_token = f.encrypt(token.encode()).decode()

    def get_token(self):
        f = Fernet(settings.MASTER_ENCRYPTION_KEY)
        return f.decrypt(self.encrypted_token.encode()).decode()

    def __str__(self):
        return f"{self.sid} ({self.description})"

class RoutingRule(models.Model):
    priority = models.IntegerField(default=100)
    pattern = models.CharField(max_length=255)
    account = models.ForeignKey(TwilioAccount, related_name='routing_rules', on_delete=models.CASCADE)
    description = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['priority']

    def __str__(self):
        return f"{self.priority}: {self.pattern} -> {self.account.sid}"

class CommunicationLog(models.Model):
    COMM_TYPES = [
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('call', 'Voice Call'),
    ]
    client = models.ForeignKey(Client, related_name='communication_logs', on_delete=models.CASCADE)
    api_key = models.ForeignKey(APIKey, null=True, blank=True, on_delete=models.SET_NULL)
    account = models.ForeignKey(TwilioAccount, null=True, blank=True, on_delete=models.SET_NULL)
    communication_type = models.CharField(max_length=20, choices=COMM_TYPES)
    to_number = models.CharField(max_length=50)
    from_number = models.CharField(max_length=50, blank=True)
    body = models.TextField(blank=True)
    twilio_sid = models.CharField(max_length=64, db_index=True, blank=True)
    status = models.CharField(max_length=50, default='pending')
    cost = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.communication_type} to {self.to_number} ({self.status})"

class AuditLog(models.Model):
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} at {self.timestamp}"
