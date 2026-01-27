"""
Global exception handler middleware to ensure API endpoints always return JSON
"""
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
import logging
import traceback

logger = logging.getLogger(__name__)


class APIExceptionMiddleware(MiddlewareMixin):
    """
    Catch all unhandled exceptions in /relay/api/ endpoints and return JSON
    instead of HTML error pages
    """
    
    def process_exception(self, request, exception):
        # Only handle exceptions for API endpoints
        if not request.path.startswith('/relay/api/'):
            return None
        
        # Log the full exception
        logger.error(
            f"Unhandled exception in {request.path}: {str(exception)}",
            exc_info=True,
            extra={
                'path': request.path,
                'method': request.method,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'remote_addr': request.META.get('REMOTE_ADDR', ''),
            }
        )
        
        # Determine error type and appropriate status code
        error_message = str(exception)
        status_code = 500
        
        # Common exception types
        if 'DoesNotExist' in exception.__class__.__name__:
            error_message = "Resource not found"
            status_code = 404
        elif 'ValidationError' in exception.__class__.__name__:
            error_message = f"Validation error: {error_message}"
            status_code = 400
        elif 'PermissionDenied' in exception.__class__.__name__:
            error_message = "Permission denied"
            status_code = 403
        elif 'Fernet' in exception.__class__.__name__ or 'InvalidToken' in error_message:
            error_message = "Encryption configuration error - check MASTER_ENCRYPTION_KEY"
            status_code = 500
        elif 'database' in error_message.lower() or 'connection' in error_message.lower():
            error_message = "Database connection error"
            status_code = 503
        elif 'redis' in error_message.lower() or 'cache' in error_message.lower():
            error_message = "Cache service unavailable"
            status_code = 503
        
        # Build error response
        error_response = {
            'error': error_message,
            'type': exception.__class__.__name__,
        }
        
        # Include traceback in debug mode
        from django.conf import settings
        if settings.DEBUG:
            error_response['traceback'] = traceback.format_exc()
            error_response['path'] = request.path
            error_response['method'] = request.method
        
        return JsonResponse(error_response, status=status_code)
