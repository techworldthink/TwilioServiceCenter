from rest_framework import serializers

class TwilioMessageSerializer(serializers.Serializer):
    To = serializers.CharField(help_text="The destination phone number (E.164 format).", required=True)
    From = serializers.CharField(help_text="The sender phone number (E.164 format) or sender ID.", required=False)
    Body = serializers.CharField(help_text="The text body of the message.", required=True)
    MediaUrl = serializers.ListField(
        child=serializers.URLField(),
        help_text="A list of media URLs to include in the message.",
        required=False
    )
    StatusCallback = serializers.URLField(
        help_text="A URL where Twilio will send status updates.",
        required=False
    )

class SMSSerializer(serializers.Serializer):
    To = serializers.CharField(help_text="The destination phone number (E.164 format).", required=True)
    Body = serializers.CharField(help_text="The text content of the SMS.", required=True)
    From = serializers.CharField(help_text="Sender ID or phone number.", required=False)

class WhatsAppSerializer(serializers.Serializer):
    To = serializers.CharField(help_text="The destination WhatsApp number (e.g. +1234567890). Do not include 'whatsapp:' prefix.", required=True)
    Body = serializers.CharField(help_text="The content of the WhatsApp message.", required=True)
    From = serializers.CharField(help_text="Sender WhatsApp number. Do not include 'whatsapp:' prefix.", required=False)
    MediaUrl = serializers.ListField(child=serializers.URLField(), required=False)

class CallSerializer(serializers.Serializer):
    To = serializers.CharField(help_text="The number to call.", required=True)
    From = serializers.CharField(help_text="The caller ID.", required=False)
    Twiml = serializers.CharField(help_text="TwiML XML instructions for the call.", required=False)
    Url = serializers.URLField(help_text="URL returning TwiML.", required=False)
    
    def validate(self, data):
        if not data.get('Url') and not data.get('Twiml'):
            raise serializers.ValidationError("Either 'Url' or 'Twiml' must be provided.")
        return data

class TwilioCallSerializer(serializers.Serializer):
    To = serializers.CharField(help_text="The destination phone number (E.164 format).", required=True)
    From = serializers.CharField(help_text="The caller phone number (E.164 format).", required=True)
    Url = serializers.URLField(help_text="The absolute URL that returns TwiML for this call.", required=False)
    Twiml = serializers.CharField(help_text="TwiML instructions for the call.", required=False)
    StatusCallback = serializers.URLField(
        help_text="A URL where Twilio will send status updates.",
        required=False
    )
    StatusCallbackEvent = serializers.ListField(
        child=serializers.CharField(),
        help_text="The call progress events that trigger a status callback.",
        required=False
    )

    def validate(self, data):
        """
        Check that either Url or Twiml is provided.
        """
        if not data.get('Url') and not data.get('Twiml'):
            raise serializers.ValidationError("Either 'Url' or 'Twiml' must be provided.")
        return data
