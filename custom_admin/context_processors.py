"""
Custom Admin Context Processors
"""
from inventory.models import Profile


def admin_context(request):
    """
    Add admin-specific context variables to all templates
    """
    context = {}
    
    if request.user.is_authenticated and request.user.is_staff:
        # Count pending staff approvals (for badge in sidebar)
        if request.user.is_superuser:
            pending_staff = Profile.objects.filter(
                is_approved=False,
                user__is_staff=True
            ).count()
            context['pending_staff'] = pending_staff
    
    return context
