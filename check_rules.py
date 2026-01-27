import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twilio_service_center.settings')
django.setup()

from relay.models import RoutingRule, TwilioAccount

print("Existing Routing Rules:")
for rule in RoutingRule.objects.all():
    print(f"Rule: {rule}")

if not RoutingRule.objects.exists():
    print("No rules found!")
    # Create default rule if none exist
    # Need a TwilioAccount first
    if not TwilioAccount.objects.exists():
        TwilioAccount.objects.create(
            sid='AC_TEST_ACCOUNT',
            encrypted_token='dummy_token',
            name='Test Account',
            description='Created for testing'
        )
    account = TwilioAccount.objects.first()
    
    # Create default catch-all rule
    RoutingRule.objects.create(
        priority=100,
        pattern='.*',
        account=account,
        description='Default Catch-All'
    )
    print(f"Created Default Rule: .* -> {account.sid}")
