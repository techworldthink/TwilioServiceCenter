from django.db import transaction
from .models import Client, TwilioAccount, RoutingRule, APIKey
from cryptography.fernet import Fernet
from django.conf import settings
import re
import logging

logger = logging.getLogger(__name__)

class BillingService:
    @staticmethod
    def deduct_balance(client_id, amount):
        with transaction.atomic():
            # Lock the client row for update
            client = Client.objects.select_for_update().get(id=client_id)
            if client.balance >= amount:
                client.balance -= amount
                client.save()
                return True, client.balance
            return False, client.balance

class RouterService:
    @staticmethod
    def get_account_for_number(to_number, api_key=None):
        # 1. Check if allowed by API key forced routing
        if api_key and api_key.forced_account:
            return api_key.forced_account

        # 2. Allow default rules or specific pattern matching
        rules = RoutingRule.objects.all().select_related('account')
        for rule in rules:
            if re.match(rule.pattern, to_number):
                return rule.account
        return None

    @staticmethod
    def get_decrypted_token(account):
        return account.get_token()

class AuthService:
    @staticmethod
    def validate_api_key(key_value):
        # In a real impl, we'd hash key_value and lookup APIKey.key_hash
        # For this demo, let's assume key_value IS the key_hash for simplicity 
        # or that we can lookup by a prefix and verify the hash.
        # Implementation depends on how keys are generated. 
        # Let's assume passed key is the raw key, we hash it here.
        import hashlib
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()
        
        try:
            api_key = APIKey.objects.select_related('client', 'forced_account').get(key_hash=key_hash, is_active=True)
            return api_key
        except APIKey.DoesNotExist:
            return None
