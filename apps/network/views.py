from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.mixins import safe_next
from apps.core.permissions import verified_required

from .models import Connection

User = get_user_model()


@verified_required
def connections(request):
    accepted = (
        Connection.objects.filter(status=Connection.Status.ACCEPTED)
        .filter(Q(requester=request.user) | Q(addressee=request.user))
        .select_related(
            "requester", "addressee",
            "requester__actor_profile", "requester__casting_profile",
            "addressee__actor_profile", "addressee__casting_profile",
        )
        .order_by("-responded_at")
    )
    items = [
        {"person": c.addressee if c.requester_id == request.user.pk else c.requester, "connection_pk": c.pk}
        for c in accepted
    ]
    return render(request, "network/connections.html", {"items": items})


@verified_required
def requests_view(request):
    pending = Connection.objects.filter(status=Connection.Status.PENDING).select_related(
        "requester", "addressee",
        "requester__actor_profile", "requester__casting_profile",
        "addressee__actor_profile", "addressee__casting_profile",
    )
    return render(
        request,
        "network/requests.html",
        {
            "incoming": pending.filter(addressee=request.user),
            "outgoing": pending.filter(requester=request.user),
        },
    )


@require_POST
@verified_required
def send_request(request, user_id):
    target = get_object_or_404(User, pk=user_id, is_active=True)
    fallback = target.get_absolute_url()
    if target.pk == request.user.pk:
        messages.error(request, "You can't connect with yourself.")
        return redirect(safe_next(request, fallback))

    existing = Connection.objects.between(request.user, target)
    if existing is None:
        Connection.objects.create(requester=request.user, addressee=target)
        messages.success(request, f"Connection request sent to {target.full_name}.")
    elif existing.status == Connection.Status.ACCEPTED:
        messages.info(request, f"You're already connected with {target.full_name}.")
    elif existing.addressee_id == request.user.pk:
        existing.status = Connection.Status.ACCEPTED
        existing.responded_at = timezone.now()
        existing.save(update_fields=["status", "responded_at"])
        messages.success(request, f"You're now connected with {target.full_name}.")
    else:
        messages.info(request, "Your request is already waiting for a reply.")
    return redirect(safe_next(request, fallback))


@require_POST
@verified_required
def accept(request, pk):
    connection = get_object_or_404(
        Connection, pk=pk, addressee=request.user, status=Connection.Status.PENDING
    )
    connection.status = Connection.Status.ACCEPTED
    connection.responded_at = timezone.now()
    connection.save(update_fields=["status", "responded_at"])
    messages.success(request, f"You're now connected with {connection.requester.full_name}.")
    return redirect("network:requests")


@require_POST
@verified_required
def decline(request, pk):
    connection = get_object_or_404(
        Connection, pk=pk, addressee=request.user, status=Connection.Status.PENDING
    )
    connection.delete()
    messages.success(request, "Request declined.")
    return redirect("network:requests")


@require_POST
@verified_required
def cancel(request, pk):
    connection = get_object_or_404(
        Connection, pk=pk, requester=request.user, status=Connection.Status.PENDING
    )
    connection.delete()
    messages.success(request, "Request withdrawn.")
    return redirect("network:requests")


@require_POST
@verified_required
def remove(request, pk):
    connection = get_object_or_404(
        Connection.objects.filter(Q(requester=request.user) | Q(addressee=request.user)),
        pk=pk,
        status=Connection.Status.ACCEPTED,
    )
    connection.delete()
    messages.success(request, "Connection removed.")
    return redirect(safe_next(request, "network:connections"))