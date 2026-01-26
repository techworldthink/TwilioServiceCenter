from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .services import BillingService, RouterService
from twilio.rest import Client as TwilioClient
import decimal

class SendSMSView(APIView):
    def post(self, request):
        # request.client_id is set by middleware
        client_id = request.client_id
        to_number = request.data.get('To')
        body = request.data.get('Body')
        
        if not to_number or not body:
            return Response({'error': 'To and Body are required'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Estimate Cost (Simple logic: 0.0075 per segment)
        # In real world, query Twilio pricing API or internal rate card
        estimated_cost = decimal.Decimal('0.0075')
        
        # 2. Billing Check & Deduct
        success, balance = BillingService.deduct_balance(client_id, estimated_cost)
        if not success:
            return Response({'error': 'Insufficient Funds', 'balance': balance}, status=status.HTTP_402_PAYMENT_REQUIRED)

        # 3. Routing
        account = RouterService.get_account_for_number(to_number)
        if not account:
            # Refund? Or just fail. Let's fail for now. 
            # Ideally we should reverse the transaction or not commit it until send is success.
            # But for Relay performance, we usually deduct first.
            return Response({'error': 'No Route Found'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            # 4. Send via Twilio
            token = RouterService.get_decrypted_token(account)
            client = TwilioClient(account.sid, token)
            
            message = client.messages.create(
                to=to_number,
                from_=request.data.get('From'), # Optional, or use Account default
                body=body
            )
            
            return Response({
                'sid': message.sid,
                'status': message.status,
                'cost': estimated_cost,
                'remaining_balance': balance
            })
            
        except Exception as e:
            # TODO: Refund logic here
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from drf_spectacular.utils import extend_schema
from .serializers import TwilioMessageSerializer, TwilioCallSerializer, SMSSerializer, WhatsAppSerializer, CallSerializer

# ... [Previous Views] ...

# ---- Simplified Standard APIs ----

class StandardSMSView(APIView):
    @extend_schema(
        request=SMSSerializer,
        responses={200: dict, 400: dict, 401: dict, 402: dict, 503: dict},
        description="Send a standard SMS message."
    )
    def post(self, request):
        client_id = getattr(request, 'client_id', None)
        api_key = getattr(request, 'api_key', None)
        
        if not client_id or not api_key:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        if not api_key.allow_sms:
            return Response({'error': 'SMS capability disabled for this API Key'}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = SMSSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        data = serializer.validated_data
        
        # 1. Billing
        estimated_cost = decimal.Decimal('0.0075')
        success, balance = BillingService.deduct_balance(client_id, estimated_cost)
        if not success:
            return Response({'error': 'Insufficient Funds'}, status=status.HTTP_402_PAYMENT_REQUIRED)
            
        # 2. Routing
        account = RouterService.get_account_for_number(data['To'], api_key)
        if not account:
            BillingService.deduct_balance(client_id, -estimated_cost)
            return Response({'error': 'No Route Found'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
        try:
            token = RouterService.get_decrypted_token(account)
            client = TwilioClient(account.sid, token)
            
            # Determine From number
            from_number = data.get('From')
            if not from_number and account.phone_number:
                from_number = account.phone_number
            
            msg = client.messages.create(
                to=data['To'],
                from_=from_number,
                body=data['Body']
            )
            return Response({'status': 'sent', 'sid': msg.sid, 'cost': estimated_cost}, status=status.HTTP_200_OK)
        except Exception as e:
            BillingService.deduct_balance(client_id, -estimated_cost)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StandardWhatsAppView(APIView):
    @extend_schema(
        request=WhatsAppSerializer,
        responses={200: dict, 400: dict, 401: dict, 402: dict, 503: dict},
        description="Send a WhatsApp message. Automatically handles 'whatsapp:' prefixes."
    )
    def post(self, request):
        client_id = getattr(request, 'client_id', None)
        api_key = getattr(request, 'api_key', None)
        
        if not client_id or not api_key:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        if not api_key.allow_whatsapp:
            return Response({'error': 'WhatsApp capability disabled for this API Key'}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = WhatsAppSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        data = serializer.validated_data
        
        # 1. Billing
        estimated_cost = decimal.Decimal('0.0050')
        success, balance = BillingService.deduct_balance(client_id, estimated_cost)
        if not success:
            return Response({'error': 'Insufficient Funds'}, status=status.HTTP_402_PAYMENT_REQUIRED)

        # 2. Routing (Route by raw number, excluding 'whatsapp:' prefix)
        raw_to_number = data['To'].replace('whatsapp:', '')
        account = RouterService.get_account_for_number(raw_to_number, api_key)
        if not account:
            BillingService.deduct_balance(client_id, -estimated_cost)
            return Response({'error': 'No Route Found'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 3. Format numbers for WhatsApp
        to_num = data['To']
        if not to_num.startswith('whatsapp:'):
            to_num = f"whatsapp:{to_num}"
            
        from_num = data.get('From')
        if not from_num and account.phone_number:
             from_num = account.phone_number
             
        if from_num and not from_num.startswith('whatsapp:'):
            from_num = f"whatsapp:{from_num}"
            
        try:
            token = RouterService.get_decrypted_token(account)
            client = TwilioClient(account.sid, token)
            
            create_kwargs = {
                'to': to_num,
                'body': data['Body']
            }
            if from_num:
                create_kwargs['from_'] = from_num
            if 'MediaUrl' in data:
                create_kwargs['media_url'] = data['MediaUrl']
                
            msg = client.messages.create(**create_kwargs)
            return Response({'status': 'sent', 'sid': msg.sid, 'cost': estimated_cost}, status=status.HTTP_200_OK)
        except Exception as e:
            BillingService.deduct_balance(client_id, -estimated_cost)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StandardCallView(APIView):
    @extend_schema(
        request=CallSerializer,
        responses={200: dict, 400: dict, 401: dict, 402: dict, 503: dict},
        description="Initiate a voice call."
    )
    def post(self, request):
        client_id = getattr(request, 'client_id', None)
        api_key = getattr(request, 'api_key', None)
        
        if not client_id or not api_key:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not api_key.allow_voice:
            return Response({'error': 'Voice capability disabled for this API Key'}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = CallSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # 1. Billing
        estimated_cost = decimal.Decimal('0.015')
        success, balance = BillingService.deduct_balance(client_id, estimated_cost)
        if not success:
            return Response({'error': 'Insufficient Funds'}, status=status.HTTP_402_PAYMENT_REQUIRED)
            
        # 2. Routing
        account = RouterService.get_account_for_number(data['To'], api_key)
        if not account:
            BillingService.deduct_balance(client_id, -estimated_cost)
            return Response({'error': 'No Route Found'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
        try:
            token = RouterService.get_decrypted_token(account)
            client = TwilioClient(account.sid, token)
            
            # Determine From number
            from_number = data.get('From')
            if not from_number and account.phone_number:
                from_number = account.phone_number
            
            create_kwargs = {
                'to': data['To'],
                'from_': from_number
            }
            if 'Twiml' in data:
                create_kwargs['twiml'] = data['Twiml']
            if 'Url' in data:
                create_kwargs['url'] = data['Url']
                
            call = client.calls.create(**create_kwargs)
            return Response({'status': 'initiated', 'sid': call.sid, 'cost': estimated_cost}, status=status.HTTP_200_OK)
        except Exception as e:
            BillingService.deduct_balance(client_id, -estimated_cost)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TwilioMessagesView(APIView):
    @extend_schema(
        request=TwilioMessageSerializer,
        responses={
            201: TwilioMessageSerializer, # In reality, returns Twilio format, but this helps docs
            400: dict,
            401: dict,
            402: dict,
            503: dict
        },
        description="Send a message (SMS/WhatsApp) via Twilio Relay"
    )
    def post(self, request, account_sid=None):
        """
        Handle Twilio Messages (SMS/WhatsApp)
        URL: /2010-04-01/Accounts/{AccountSid}/Messages.json
        """
        client_id = getattr(request, 'client_id', None)
        if not client_id:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        to_number = request.data.get('To')
        body = request.data.get('Body')
        from_number = request.data.get('From')
        
        if not to_number:
            return Response({'error': 'To parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Estimate Cost
        estimated_cost = decimal.Decimal('0.0075') # Default SMS rate
        
        # 2. Billing
        success, balance = BillingService.deduct_balance(client_id, estimated_cost)
        if not success:
            return Response(
                {'code': 20003, 'message': 'Permission Denied - Insufficient Funds', 'more_info': 'https://www.twilio.com/docs/errors/20003', 'status': 402}, 
                status=status.HTTP_402_PAYMENT_REQUIRED
            )

        # 3. Routing
        account = RouterService.get_account_for_number(to_number)
        if not account:
            # Auto-refund if no route? 
            BillingService.deduct_balance(client_id, -estimated_cost) # Refund
            return Response({'error': 'No Route Found'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            # 4. Forward to Twilio
            token = RouterService.get_decrypted_token(account)
            twilio_client = TwilioClient(account.sid, token)
            
            # Forward all compatible parameters
            # Twilio SDK create method arguments:
            # to, from_, body, media_url, status_callback, application_sid, etc.
            
            create_kwargs = {
                'to': to_number,
                'from_': from_number,
                'body': body
            }
            
            if 'MediaUrl' in request.data:
                create_kwargs['media_url'] = request.data.getlist('MediaUrl')
                
            if 'StatusCallback' in request.data:
                create_kwargs['status_callback'] = request.data.get('StatusCallback')

            message = twilio_client.messages.create(**create_kwargs)
            
            # 5. Return Twilio-like Response
            return Response({
                'sid': message.sid,
                'date_created': str(message.date_created),
                'date_updated': str(message.date_updated),
                'date_sent': str(message.date_sent),
                'account_sid': message.account_sid,
                'to': message.to,
                'from': message.from_,
                'body': message.body,
                'status': message.status,
                'num_segments': message.num_segments,
                'num_media': message.num_media,
                'direction': message.direction,
                'api_version': message.api_version,
                'price': str(message.price) if message.price else None,
                'price_unit': message.price_unit,
                'error_code': message.error_code,
                'error_message': message.error_message,
                'uri': message.uri,
                'subresource_uris': message.subresource_uris,
                # Custom fields
                '_relay_cost': str(estimated_cost),
                '_client_balance': str(balance)
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Refund on failure
            BillingService.deduct_balance(client_id, -estimated_cost)
            return Response({'code': 500, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TwilioCallsView(APIView):
    @extend_schema(
        request=TwilioCallSerializer,
        responses={
            201: TwilioCallSerializer,
            400: dict,
            401: dict,
            402: dict,
            503: dict
        },
        description="Initiate a voice call via Twilio Relay"
    )
    def post(self, request, account_sid=None):
        """
        Handle Twilio Voice Calls
        URL: /2010-04-01/Accounts/{AccountSid}/Calls.json
        """
        client_id = getattr(request, 'client_id', None)
        if not client_id:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        to_number = request.data.get('To')
        from_number = request.data.get('From')
        twiml = request.data.get('Twiml')
        url = request.data.get('Url')
        
        if not to_number or (not twiml and not url):
             return Response({'error': 'To and Url/Twiml are required'}, status=status.HTTP_400_BAD_REQUEST)
             
        # 1. Estimate Cost (Voice setup fee ?)
        estimated_cost = decimal.Decimal('0.015') 
        
        # 2. Billing
        success, balance = BillingService.deduct_balance(client_id, estimated_cost)
        if not success:
            return Response({'error': 'Insufficient Funds'}, status=status.HTTP_402_PAYMENT_REQUIRED)
            
        # 3. Routing
        account = RouterService.get_account_for_number(to_number)
        if not account:
            BillingService.deduct_balance(client_id, -estimated_cost)
            return Response({'error': 'No Route Found'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            # 4. Forward to Twilio
            token = RouterService.get_decrypted_token(account)
            twilio_client = TwilioClient(account.sid, token)
            
            create_kwargs = {
                'to': to_number,
                'from_': from_number,
            }
            if twiml:
                create_kwargs['twiml'] = twiml
            if url:
                create_kwargs['url'] = url
                
            # Forward other common params
            if 'StatusCallback' in request.data:
                create_kwargs['status_callback'] = request.data.get('StatusCallback')
            if 'StatusCallbackEvent' in request.data:
                create_kwargs['status_callback_event'] = request.data.getlist('StatusCallbackEvent')

            call = twilio_client.calls.create(**create_kwargs)
            
            return Response({
                'sid': call.sid,
                'date_created': str(call.date_created),
                'date_updated': str(call.date_updated),
                'parent_call_sid': call.parent_call_sid,
                'account_sid': call.account_sid,
                'to': call.to,
                'from': call.from_,
                'phone_number_sid': call.phone_number_sid,
                'status': call.status,
                'start_time': str(call.start_time) if call.start_time else None,
                'end_time': str(call.end_time) if call.end_time else None,
                'duration': call.duration,
                'price': str(call.price) if call.price else None,
                'direction': call.direction,
                'api_version': call.api_version,
                'forwarded_from': call.forwarded_from,
                'caller_name': call.caller_name,
                'uri': call.uri,
                 # Custom fields
                '_relay_cost': str(estimated_cost),
                '_client_balance': str(balance)
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            BillingService.deduct_balance(client_id, -estimated_cost)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WebhookView(APIView):
    # No Auth required for Twilio webhooks usually, but should validate signature.
    # For now, let's just log it.
    def post(self, request):
        data = request.data
        print(f"Webhook Received: {data}")
        return Response({'status': 'received'})

# Template-based views for UI pages
from django.views.generic import TemplateView
from .models import Client, APIKey

class HomeView(TemplateView):
    template_name = 'home.html'

class DashboardView(TemplateView):
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get first client for demo (in production, use authenticated user)
        try:
            client = Client.objects.first()
            if client:
                context['balance'] = client.balance
                context['api_keys'] = APIKey.objects.filter(client=client)
                context['api_keys_count'] = context['api_keys'].count()
            else:
                context['balance'] = 0
                context['api_keys'] = []
                context['api_keys_count'] = 0
        except:
            context['balance'] = 0
            context['api_keys'] = []
            context['api_keys_count'] = 0
            
        # Mock data for demo
        context['messages_sent'] = 0
        context['success_rate'] = 99.9
        context['transactions'] = []
        
        return context

class APIDocsView(TemplateView):
    template_name = 'api_docs.html'
