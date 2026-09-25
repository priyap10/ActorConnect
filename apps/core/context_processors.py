from django.conf import settings


def site(request):
    return {"SITE_NAME": settings.SITE_NAME}


def counters(request):
   
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    from apps.messaging.models import Message
    from apps.notifications.models import Notification

    return {
        "unread_notifications": Notification.objects.filter(recipient=user, is_read=False).count(),
        "unread_messages": Message.objects.filter(
            conversation__in=user.conversations(), read_at__isnull=True
        )
        .exclude(sender=user)
        .count(),
    }