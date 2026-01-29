"""
Custom Admin Middleware
Enforces authentication and role-based access at the middleware level
"""
from django.shortcuts import redirect
from django.http import HttpResponseForbidden


class AdminAccessMiddleware:
    """
    Middleware to enforce admin panel access control.
    Runs before any view logic executes.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only check paths that start with /admin/ or /admin-custom/ but not /django-admin/
        if (request.path.startswith('/admin/') or request.path.startswith('/admin-custom/')) and not request.path.startswith('/django-admin/'):
            
            # 1. If user is NOT authenticated, they MUST go to login
            if not request.user.is_authenticated:
                # Avoid infinite redirect if already on login page or accessing static files
                if request.path == '/admin-custom/login/' or request.path.startswith('/admin-custom/static/') or request.path.startswith('/static/'):
                    return self.get_response(request)
                return redirect('admin-custom:login')
            
            # 2. If user IS authenticated but NOT staff, block them
            if not request.user.is_staff:
                return HttpResponseForbidden(
                    "<h1>Access Denied</h1><p>You do not have permission to access the admin panel.</p>"
                )
        
        return self.get_response(request)
