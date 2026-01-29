"""
Custom Admin Permission Decorators
"""
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def require_super_admin(view_func):
    """Requires user to be a superuser"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/admin/login/')
        if not request.user.is_superuser:
            return HttpResponseForbidden("Super Admin access required")
        return view_func(request, *args, **kwargs)
    return wrapper


def require_admin_or_above(view_func):
    """Requires user to be admin or superuser"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/admin/login/')
        if not request.user.is_staff:
            return HttpResponseForbidden("Admin access required")
        return view_func(request, *args, **kwargs)
    return wrapper


def require_staff_or_above(view_func):
    """Requires user to be staff, admin, or superuser"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/admin/login/')
        if not request.user.is_staff:
            return HttpResponseForbidden("Staff access required")
        return view_func(request, *args, **kwargs)
    return wrapper
