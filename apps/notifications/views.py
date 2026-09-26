from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.permissions import verified_required

from .models import Notification


@verified_required
def notification_list(request):
    page = Paginator(Notification.objects.filter(recipient=request.user), 20).get_page(request.GET.get("page"))
    return render(request, "notifications/list.html", {"page_obj": page})


@verified_required
def open_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return redirect(notification.url or "notifications:list")


@require_POST
@verified_required
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")