"""
Health check and diagnostic endpoints
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from relay.models import Client, APIKey, TwilioAccount, RoutingRule
import logging

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Health check endpoint - no authentication required
    Returns system status and configuration checks
    """
    
    def get(self, request):
        """
        GET /relay/api/health
        
        Returns:
        - status: "healthy" or "unhealthy"
        - checks: dict of individual component statuses
        """
        checks = {}
        overall_healthy = True
        
        # 1. Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks['database'] = {
                'status': 'ok',
                'message': 'Database connection successful'
            }
        except Exception as e:
            checks['database'] = {
                'status': 'error',
                'message': f'Database error: {str(e)}'
            }
            overall_healthy = False
        
        # 2. Redis/Cache check
        try:
            cache_key = 'health_check_test'
            cache.set(cache_key, 'test_value', timeout=10)
            value = cache.get(cache_key)
            if value == 'test_value':
                checks['cache'] = {
                    'status': 'ok',
                    'message': 'Cache connection successful'
                }
            else:
                checks['cache'] = {
                    'status': 'warning',
                    'message': 'Cache read/write mismatch'
                }
        except Exception as e:
            checks['cache'] = {
                'status': 'error',
                'message': f'Cache error: {str(e)}'
            }
            overall_healthy = False
        
        # 3. Encryption key check
        try:
            from cryptography.fernet import Fernet
            if settings.MASTER_ENCRYPTION_KEY:
                # Try to create a Fernet instance
                f = Fernet(settings.MASTER_ENCRYPTION_KEY.encode() if isinstance(settings.MASTER_ENCRYPTION_KEY, str) else settings.MASTER_ENCRYPTION_KEY)
                # Test encryption/decryption
                test_data = b"test"
                encrypted = f.encrypt(test_data)
                decrypted = f.decrypt(encrypted)
                if decrypted == test_data:
                    checks['encryption'] = {
                        'status': 'ok',
                        'message': 'Encryption key valid'
                    }
                else:
                    checks['encryption'] = {
                        'status': 'error',
                        'message': 'Encryption/decryption failed'
                    }
                    overall_healthy = False
            else:
                checks['encryption'] = {
                    'status': 'error',
                    'message': 'MASTER_ENCRYPTION_KEY not set'
                }
                overall_healthy = False
        except Exception as e:
            checks['encryption'] = {
                'status': 'error',
                'message': f'Encryption error: {str(e)}'
            }
            overall_healthy = False
        
        # 4. Configuration checks
        try:
            client_count = Client.objects.count()
            api_key_count = APIKey.objects.filter(is_active=True).count()
            account_count = TwilioAccount.objects.count()
            routing_rule_count = RoutingRule.objects.count()
            
            config_warnings = []
            if client_count == 0:
                config_warnings.append('No clients configured')
            if api_key_count == 0:
                config_warnings.append('No active API keys')
            if account_count == 0:
                config_warnings.append('No Twilio accounts configured')
            if routing_rule_count == 0:
                config_warnings.append('No routing rules configured')
            
            checks['configuration'] = {
                'status': 'warning' if config_warnings else 'ok',
                'message': '; '.join(config_warnings) if config_warnings else 'Configuration complete',
                'details': {
                    'clients': client_count,
                    'active_api_keys': api_key_count,
                    'twilio_accounts': account_count,
                    'routing_rules': routing_rule_count
                }
            }
            
            if config_warnings:
                overall_healthy = False
                
        except Exception as e:
            checks['configuration'] = {
                'status': 'error',
                'message': f'Configuration check error: {str(e)}'
            }
            overall_healthy = False
        
        # 5. Environment info (non-sensitive)
        checks['environment'] = {
            'status': 'info',
            'debug_mode': settings.DEBUG,
            'python_version': __import__('sys').version.split()[0],
            'django_version': __import__('django').get_version(),
        }
        
        response_data = {
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'checks': checks
        }
        
        response_status = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return Response(response_data, status=response_status)


class DiagnosticView(APIView):
    """
    Diagnostic endpoint - requires authentication
    Returns detailed system information for troubleshooting
    """
    
    def get(self, request):
        """
        GET /relay/api/diagnostic
        
        Requires: X-Proxy-Auth header
        
        Returns detailed diagnostic information
        """
        client_id = getattr(request, 'client_id', None)
        api_key = getattr(request, 'api_key', None)
        
        if not client_id or not api_key:
            return Response({
                'error': 'Authentication required',
                'message': 'This endpoint requires X-Proxy-Auth header'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # Get client info
            client = Client.objects.get(id=client_id)
            
            # Get routing rules
            routing_rules = []
            for rule in RoutingRule.objects.all().select_related('account'):
                routing_rules.append({
                    'pattern': rule.pattern,
                    'priority': rule.priority,
                    'account_name': rule.account.name if rule.account else None,
                    'account_sid': rule.account.sid if rule.account else None,
                })
            
            # Get API key permissions
            permissions = {
                'allow_sms': api_key.allow_sms,
                'allow_voice': api_key.allow_voice,
                'allow_whatsapp': api_key.allow_whatsapp,
                'forced_account': api_key.forced_account.name if api_key.forced_account else None,
            }
            
            diagnostic_data = {
                'client': {
                    'name': client.name,
                    'balance': str(client.balance),
                    'is_active': client.is_active,
                },
                'api_key': {
                    'prefix': api_key.prefix,
                    'permissions': permissions,
                    'is_active': api_key.is_active,
                },
                'routing': {
                    'total_rules': len(routing_rules),
                    'rules': routing_rules,
                },
                'accounts': {
                    'total': TwilioAccount.objects.count(),
                    'active': TwilioAccount.objects.filter(capability_whatsapp=True).count(),
                }
            }
            
            return Response(diagnostic_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Diagnostic error: {str(e)}", exc_info=True)
            return Response({
                'error': 'Diagnostic failed',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
