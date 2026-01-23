from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps


def admin_required(function=None, login_url='/admin/login/'):
    """
    Decorator for views that checks that the user is logged in and is a staff member.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url=login_url,
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def ajax_required(function):
    """
    Decorator that checks if the request is an AJAX request.
    """
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            raise PermissionDenied('This endpoint only accepts AJAX requests')
        return function(request, *args, **kwargs)
    return wrap
