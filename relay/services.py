from django.db import transaction
from .models import Client, TwilioAccount, RoutingRule, APIKey, CommunicationLog, AuditLog
from cryptography.fernet import Fernet
from django.conf import settings
import re
import logging
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

class BillingService:
    @staticmethod
    def deduct_balance(client_id, amount):
        with transaction.atomic():
            client = Client.objects.select_for_update().get(id=client_id)
            if client.balance >= amount:
                client.balance -= amount
                client.save()
                return True, client.balance
            return False, client.balance

class RouterService:
    @staticmethod
    def get_account_for_number(to_number, api_key=None):
        if api_key and api_key.forced_account:
            return api_key.forced_account
        rules = RoutingRule.objects.all().select_related('account')
        for rule in rules:
            if re.match(rule.pattern, to_number):
                return rule.account
        return None

    @staticmethod
    def get_decrypted_token(account):
        return account.get_token()

class LogService:
    @staticmethod
    def log_communication(client, api_key, account, comm_type, to_num, from_num, body, twilio_sid='', status='pending', cost=0, error=''):
        # Handle both model instances and objects with 'id' attribute (like cached KeyStruct), and None values
        client_id = client.id if (client and hasattr(client, 'id')) else None
        api_key_id = api_key.id if (api_key and hasattr(api_key, 'id')) else None
        account_id = None
        if account:
            account_id = account.sid if hasattr(account, 'sid') else (account.id if hasattr(account, 'id') else account)
        
        return CommunicationLog.objects.create(
            client_id=client_id,
            api_key_id=api_key_id,
            account_id=account_id,
            communication_type=comm_type,
            to_number=to_num,
            from_number=from_num,
            body=body,
            twilio_sid=twilio_sid,
            status=status,
            cost=cost,
            error_message=error
        )

    @staticmethod
    def update_log_status(twilio_sid, status, error=''):
        try:
            log = CommunicationLog.objects.get(twilio_sid=twilio_sid)
            log.status = status
            if error:
                log.error_message = error
            log.save()
            return log
        except CommunicationLog.DoesNotExist:
            return None

    @staticmethod
    def sync_status_from_twilio(log):
        """Fetch latest status from Twilio API and update log."""
        if not log.twilio_sid or not log.account:
             return False

        try:
             token = RouterService.get_decrypted_token(log.account)
             client = TwilioClient(log.account.sid, token)
             
             resource = None
             if log.communication_type in ['sms', 'whatsapp']:
                 resource = client.messages(log.twilio_sid).fetch()
             elif log.communication_type == 'call':
                 resource = client.calls(log.twilio_sid).fetch()
                 
             if resource:
                 log.status = resource.status
                 if hasattr(resource, 'error_code') and resource.error_code:
                     error_text = f"Error {resource.error_code}"
                     if hasattr(resource, 'error_message') and resource.error_message:
                         error_text += f": {resource.error_message}"
                     log.error_message = error_text
                 
                 # Cost might update later?
                 if hasattr(resource, 'price') and resource.price:
                     log.cost = abs(float(resource.price))
                     
                 log.save()
                 return True
                 
        except TwilioRestException as e:
             # If 404, maybe it doesn't exist?
             logger.error(f"Twilio Sync Error for {log.twilio_sid}: {e}")
             if e.status == 404:
                 log.status = 'not_found'
                 log.error_message = 'Resource not found in Twilio'
                 log.save()
        except Exception as e:
             logger.error(f"Sync Error: {e}")
             
        return False

    @staticmethod
    def log_action(action, details='', request=None):
        log = AuditLog(action=action, details=details)
        if request:
            log.ip_address = request.META.get('REMOTE_ADDR')
            log.user_agent = request.META.get('HTTP_USER_AGENT', '')
        log.save()
        return log

class AuthService:
    @staticmethod
    def validate_api_key(key_value):
        import hashlib
        key_hash = hashlib.sha256(key_value.encode()).hexdigest()
        try:
            api_key = APIKey.objects.select_related('client', 'forced_account').get(key_hash=key_hash, is_active=True)
            return api_key
        except APIKey.DoesNotExist:
            return None
