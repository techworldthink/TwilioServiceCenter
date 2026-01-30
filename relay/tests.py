from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from .models import Client, APIKey, TwilioAccount, RoutingRule
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

    @patch('relay.views.TwilioClient')
    def test_sms_explicit_status_callback(self, MockTwilioClient):
        # Setup Mock
        mock_messages = MagicMock()
        mock_messages.create.return_value.sid = "SMtest"
        mock_messages.create.return_value.status = "queued"
        MockTwilioClient.return_value.messages = mock_messages
        
        # Request
        data = {
            "To": "+1234567890",
            "Body": "Test Message",
            "StatusCallback": "https://example.com/callback"
        }
        response = self.client.post('/relay/api/sms', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify
        mock_messages.create.assert_called_once()
        call_kwargs = mock_messages.create.call_args[1]
        self.assertEqual(call_kwargs['status_callback'], "https://example.com/callback")

    @patch('relay.views.TwilioClient')
    def test_whatsapp_default_status_callback(self, MockTwilioClient):
        # Setup Mock
        mock_messages = MagicMock()
        mock_messages.create.return_value.sid = "SMtest"
        mock_messages.create.return_value.status = "queued"
        MockTwilioClient.return_value.messages = mock_messages
        
        # Request
        data = {
            "To": "whatsapp:+1234567890",
            "Body": "Test WhatsApp"
        }
        response = self.client.post('/relay/api/whatsapp', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify
        expected_callback = f"{settings.PUBLIC_HOST}/relay/twilio/webhook"
        mock_messages.create.assert_called_once()
        call_kwargs = mock_messages.create.call_args[1]
        self.assertEqual(call_kwargs['status_callback'], expected_callback)
