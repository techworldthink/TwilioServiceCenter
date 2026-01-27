import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twilio_service_center.settings')
django.setup()

from relay.services import AuthService

key = "TESTKEY_BSd1aR-QddDjkTAUCpY4D_kcRitCgMn0sfoOllsrnVI"
print(f"Testing Key: {key}")

api_key = AuthService.validate_api_key(key)
if api_key:
    print(f"Key Valid! ID: {api_key.id}, Client: {api_key.client.name}")
else:
    print("Key Invalid according to AuthService")
