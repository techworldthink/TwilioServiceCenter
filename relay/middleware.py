from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.core.cache import cache
from .services import AuthService
import hashlib

class RelayAuthMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Apply to /relay/ paths AND Twilio-compatible paths
        if not request.path.startswith('/relay/') and not request.path.startswith('/2010-04-01/'):
            return None
        
        # Exempt health check endpoint from authentication
        if request.path == '/relay/api/health':
            return None

        auth_header = request.headers.get('X-Proxy-Auth')
        if not auth_header:
            return JsonResponse({'error': 'Missing Authorization Header'}, status=401)

        # check cache first
        # We hash the auth header for cache key safety
        cache_key = f"auth:{hashlib.sha256(auth_header.encode()).hexdigest()}"
        cached_data = cache.get(cache_key)

        if cached_data:
            request.client_id = cached_data['client_id']
            # Reconstruct a lightweight object for permission checks
            class APIKeyContext:
                def __init__(self, data):
                    self.id = data['id']
                    self.allow_sms = data['allow_sms']
                    self.allow_voice = data['allow_voice']
                    self.allow_whatsapp = data['allow_whatsapp']
                    self.forced_account = data['forced_account'] # This is an object or None? 
                    # If we cache objects, we need to be careful. Better to cache forced_account_id and fetch if needed?
                    # For high perf, forced_account in service `get_account_for_number` expects an object with `.sid` or similar? 
                    # Actually `get_account_for_number` returns `rule.account`.
                    # To support caching, `forced_account` here should probably be a SimpleNamespace or similar if we want to avoid DB hit.
                    # Let's verify `get_account_for_number` usage in `views.py`.
                    pass
            
            # Simple struct for views
            class KeyStruct:
                pass
            k = KeyStruct()
            k.id = cached_data['id']
            k.allow_sms = cached_data['allow_sms']
            k.allow_voice = cached_data['allow_voice']
            k.allow_whatsapp = cached_data['allow_whatsapp']
            # forced_account handling:
            # If we cached the ID, we might need to fetch the account object if forced routing is used.
            # However, for now, let's just CACHE THE OBJECT (Django cache can pickle). 
            # If using Redis/Memcached, value size is small enough.
            k.forced_account = cached_data.get('forced_account_obj')
            # Add client object for views that need api_key.client
            k.client = cached_data['client_obj']
            
            request.api_key = k
            return None

        # Check DB
        api_key = AuthService.validate_api_key(auth_header)
        if api_key:
            # Cache payload
            cache_payload = {
                'id': api_key.id,
                'client_id': api_key.client.id,
                'allow_sms': api_key.allow_sms,
                'allow_voice': api_key.allow_voice,
                'allow_whatsapp': api_key.allow_whatsapp,
                'forced_account_obj': api_key.forced_account, # Caching the actual model instance
                'client_obj': api_key.client # Caching the client object for views that need api_key.client
            }
            # Cache for 5 minutes
            cache.set(cache_key, cache_payload, timeout=300)
            
            request.client_id = api_key.client.id
            request.api_key = api_key
            return None
        
        return JsonResponse({'error': 'Invalid API Key'}, status=401)
