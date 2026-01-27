import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twilio_service_center.settings')
django.setup()

from relay.models import Client, APIKey

client, _ = Client.objects.get_or_create(name='TestClient')
api_key, raw_key = APIKey.generate_key(client, custom_prefix='TESTKEY_')
print(f"KEY: {raw_key}")
