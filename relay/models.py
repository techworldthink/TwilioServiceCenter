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
        """Get count of active API keys for this client"""
        return self.api_keys.filter(is_active=True).count()
    
    def adjust_balance(self, amount, adjustment_type='add'):
        """
        Adjust client balance
        adjustment_type: 'add', 'deduct', or 'set'
        """
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
    key_hash = models.CharField(max_length=128, db_index=True)  # Store SHA256 hash of the key
    prefix = models.CharField(max_length=8) # Store first few chars for identification
    
    # Permissions
    allow_sms = models.BooleanField(default=True)
    allow_voice = models.BooleanField(default=True)
    allow_whatsapp = models.BooleanField(default=True)
    
    # Forced Routing (Optional)
    forced_account = models.ForeignKey('TwilioAccount', null=True, blank=True, on_delete=models.SET_NULL, related_name='forced_keys')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client.name} - {self.prefix}..."
    
    @staticmethod
    def generate_key(client, custom_prefix=None, **kwargs):
        """
        Generate a new API key for a client
        Returns: (api_key_instance, plain_key)
        Note: plain_key is only returned once and cannot be retrieved later
        """
        # Generate secure random key
        plain_key = secrets.token_urlsafe(32)
        
        # Create hash for storage
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        
        # Use custom prefix or generate from key
        prefix = custom_prefix if custom_prefix else plain_key[:8]
        
        # Create API key instance
        api_key = APIKey.objects.create(
            client=client,
            key_hash=key_hash,
            prefix=prefix,
            is_active=True,
            **kwargs
        )
        
        return api_key, plain_key
    
    def revoke(self):
        """Revoke this API key"""
        self.is_active = False
        self.save()

class TwilioAccount(models.Model):
    sid = models.CharField(max_length=34, primary_key=True)
    encrypted_token = models.TextField()
    name = models.CharField(max_length=255, blank=True, help_text="Friendly name for identification")
    phone_number = models.CharField(max_length=20, blank=True, help_text="Primary Twilio phone number for this account")
    description = models.CharField(max_length=255, blank=True)
    
    # Capabilities
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
    priority = models.IntegerField(default=100, help_text="Lower number means higher priority")
    pattern = models.CharField(max_length=255, help_text="Regex pattern to match To number")
    account = models.ForeignKey(TwilioAccount, related_name='routing_rules', on_delete=models.CASCADE)
    description = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['priority']

    def __str__(self):
        return f"{self.priority}: {self.pattern} -> {self.account.sid}"
