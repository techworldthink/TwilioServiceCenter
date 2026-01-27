import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twilio_service_center.settings')
django.setup()

from relay.models import Client

try:
    c = Client.objects.get(name='TestClient')
    c.balance = 10.0
    c.save()
    print(f"Funds Added! New Balance: {c.balance}")
except Exception as e:
    print(f"Error: {e}")
