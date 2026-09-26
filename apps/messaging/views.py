from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, OuterRef, Q, Subquery
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timesince import timesince

from apps.core.permissions import can_message, verified_required

from .forms import MessageForm
from .models import Conversation, Message

User = get_user_model()
HISTORY_LIMIT = 200


def _conversation_for(user, pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related(
            "user_a", "user_b", "user_a__actor_profile", "user_a__casting_profile",
            "user_b__actor_profile", "user_b__casting_profile",
        ),
        pk=pk,
    )
    if not conversation.includes(user):
        raise Http404
    return conversation


@verified_required
def inbox(request):
    last = Message.objects.filter(conversation=OuterRef("pk")).order_by("-id")
    conversations = (
        request.user.conversations()
        .select_related(
            "user_a", "user_b", "user_a__actor_profile", "user_a__casting_profile",
            "user_b__actor_profile", "user_b__casting_profile",
        )
        .annotate(
            last_body=Subquery(last.values("body")[:1]),
            unread=Count("messages", filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender=request.user)),
        )
        .filter(messages__isnull=False)
        .distinct()
    )
    items = [{"conversation": c, "other": c.other(request.user)} for c in conversations]
    return render(request, "messaging/inbox.html", {"items": items})


@verified_required
def start(request, user_id):
    other = get_object_or_404(User, pk=user_id, is_active=True)
    if not can_message(request.user, other):
        messages.error(request, "You can message people once you're connected, or when an application links you.")
        return redirect(other.get_absolute_url())
    return redirect("messaging:conversation", pk=Conversation.objects.between(request.user, other).pk)


@verified_required
def conversation(request, pk):
    convo = _conversation_for(request.user, pk)
    other = convo.other(request.user)
    allowed = other.is_active and can_message(request.user, other)

    form = MessageForm(request.POST or None)
    if request.method == "POST":
        if not allowed:
            messages.error(request, "You can't message this person any more.")
        elif form.is_valid():
            message = form.save(commit=False)
            message.conversation, message.sender = convo, request.user
            message.save()
            convo.save(update_fields=["updated_at"])
            return redirect("messaging:conversation", pk=convo.pk)

    convo.messages.filter(read_at__isnull=True).exclude(sender=request.user).update(read_at=timezone.now())
    history = list(convo.messages.select_related("sender").order_by("-id")[:HISTORY_LIMIT])[::-1]
    return render(
        request,
        "messaging/conversation.html",
        {"conversation": convo, "other": other, "history": history, "form": form, "allowed": allowed,
         "last_id": history[-1].pk if history else 0},
    )


@verified_required
def poll(request, pk):
    convo = _conversation_for(request.user, pk)
    try:
        after = int(request.GET.get("after", 0))
    except ValueError:
        after = 0
    new = list(convo.messages.filter(id__gt=after).select_related("sender"))
    convo.messages.filter(id__in=[m.pk for m in new]).exclude(sender=request.user).update(read_at=timezone.now())
    return JsonResponse(
        {
            "messages": [
                {
                    "id": m.pk,
                    "mine": m.sender_id == request.user.pk,
                    "body": m.body,
                    "sent": timesince(m.created_at) + " ago",
                }
                for m in new
            ]
        }
    )