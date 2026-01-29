from .models import SavedItem, Notification, WebsiteContent

def global_context(request):
    """Available in all templates"""
    context = {}
    context['site_content'] = WebsiteContent.objects.first()
    
    if request.user.is_authenticated:
        context['saved_count'] = SavedItem.objects.filter(user=request.user).count()
        unread_notifs = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
        context['notif_count'] = unread_notifs.count()
        context['notifications'] = unread_notifs[:5]
    else:
        context['saved_count'] = 0
        context['notif_count'] = 0
        context['notifications'] = []
    return context
