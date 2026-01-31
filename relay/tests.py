from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from .models import Client, APIKey, TwilioAccount, RoutingRule, CommunicationLog
from django.conf import settings

class StatusCallbackTests(TestCase):
    def setUp(self):
        self.client_model = Client.objects.create(name="Test Client", balance=10.00)
        self.account = TwilioAccount.objects.create(
            sid="ACtest", 
            encrypted_token="testToken",
            phone_number="+15005550006"
        )
        self.account.set_token("testCrypted")
        self.account.save()
        
        self.routing_rule = RoutingRule.objects.create(
            pattern=".*",
            account=self.account,
            priority=1
        )
        
        self.api_key, self.key_val = APIKey.generate_key(client=self.client_model)
        
        self.client = APIClient()
        self.client.credentials(HTTP_X_PROXY_AUTH=self.key_val)

    @patch('relay.views.TwilioClient')
    def test_sms_default_status_callback(self, MockTwilioClient):
        # Setup Mock
        mock_messages = MagicMock()
        mock_messages.create.return_value.sid = "SMtest"
        mock_messages.create.return_value.status = "queued"
        MockTwilioClient.return_value.messages = mock_messages
        
        # Request
        data = {
            "To": "+1234567890",
            "Body": "Test Message"
        }
        response = self.client.post('/relay/api/sms', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify
        expected_callback = f"{settings.PUBLIC_HOST}/relay/twilio/webhook"
        mock_messages.create.assert_called_once()
        call_kwargs = mock_messages.create.call_args[1]
        self.assertEqual(call_kwargs['status_callback'], expected_callback)

class WebhookTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create a log to update
        self.client_model = Client.objects.create(name="Test Client", balance=10.00)
        self.log = CommunicationLog.objects.create(
            client=self.client_model,
            communication_type='sms',
            to_number='+1234567890',
            twilio_sid='SMtestWebhook',
            status='queued'
        )

    def test_webhook_public_access(self):
        # Ensure no auth headers are needed
        self.client.credentials() 
        data = {
            'MessageSid': 'SMtestWebhook',
            'SmsStatus': 'sent'
        }
        response = self.client.post('/relay/twilio/webhook', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, 'sent')

    def test_webhook_whatsapp_status(self):
        # WhatsApp uses MessageStatus
        self.log.twilio_sid = 'SMwhatsapp'
        self.log.save()
        
        data = {
            'MessageSid': 'SMwhatsapp',
            'MessageStatus': 'read'
        }
        response = self.client.post('/relay/twilio/webhook', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, 'read')

    def test_webhook_old_sms_status(self):
        # SMS sometimes uses SmsSid and SmsStatus
        self.log.twilio_sid = 'SMoldest'
        self.log.save()
        
        data = {
            'SmsSid': 'SMoldest',
            'SmsStatus': 'delivered'
        }
        response = self.client.post('/relay/twilio/webhook', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, 'delivered')
