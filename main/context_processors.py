from .models import Notification
from .view_helpers import user_display_name


def app_context(request):
    if request.user.is_authenticated:
        return {
            'unread_count': Notification.objects.filter(
                user=request.user, is_read=False
            ).count(),
            'display_name': user_display_name(request.user),
        }
    return {'unread_count': 0, 'display_name': ''}
