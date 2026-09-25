import logging

from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import Role
from apps.ai.llm import AIError
from apps.ai.profile_insights import compute_strength, generate_suggestions
from apps.ai.tasks import refresh_actor_embedding_task
from apps.core.permissions import can_message, role_required, verified_required
from apps.network.models import Connection

from .forms import ActorProfileForm, CastingProfileForm
from .models import ActorProfile, CastingProfile

logger = logging.getLogger(__name__)


@verified_required
def my_profile(request):
    return redirect(request.user.get_absolute_url())


@verified_required
def actor_detail(request, pk):
    profile = get_object_or_404(
        ActorProfile.objects.select_related("user").prefetch_related("skills", "languages"),
        pk=pk,
        user__is_active=True,
    )
    is_owner = profile.user_id == request.user.pk
    if not profile.is_public and not is_owner:
        raise Http404

    owner = profile.user
    media_items = owner.media_items.all() if is_owner else owner.media_items.filter(is_public=True)
    state, connection = ("self", None) if is_owner else Connection.objects.state(request.user, owner)
    return render(
        request,
        "profiles/actor_detail.html",
        {
            "profile": profile,
            "owner": owner,
            "is_owner": is_owner,
            "media_items": media_items,
            "credits": owner.credits.all(),
            "achievements": owner.achievements.all(),
            "connection_state": state,
            "connection": connection,
            "can_message": (not is_owner) and can_message(request.user, owner),
        },
    )


@role_required(Role.ACTOR, verified=True)
def actor_edit(request):
    profile = request.user.actor_profile
    form = ActorProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        transaction.on_commit(lambda: refresh_actor_embedding_task.delay(profile.pk))
        messages.success(request, "Your profile is updated.")
        return redirect(profile)
    return render(request, "profiles/actor_edit.html", {"form": form, "profile": profile})


@verified_required
def casting_detail(request, pk):
    profile = get_object_or_404(CastingProfile.objects.select_related("user"), pk=pk, user__is_active=True)
    is_owner = profile.user_id == request.user.pk
    owner = profile.user
    state, connection = ("self", None) if is_owner else Connection.objects.state(request.user, owner)
    from apps.casting.models import CastingCall

    open_calls = [c for c in CastingCall.objects.filter(poster=owner, status=CastingCall.Status.OPEN) if c.is_accepting]
    return render(
        request,
        "profiles/casting_detail.html",
        {
            "profile": profile,
            "owner": owner,
            "is_owner": is_owner,
            "open_calls": open_calls,
            "connection_state": state,
            "connection": connection,
            "can_message": (not is_owner) and can_message(request.user, owner),
        },
    )


@role_required(Role.CASTING, verified=True)
def casting_edit(request):
    profile = request.user.casting_profile
    form = CastingProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile is updated.")
        return redirect(profile)
    return render(request, "profiles/casting_edit.html", {"form": form, "profile": profile})


@role_required(Role.ACTOR, verified=True)
def actor_insights(request):
    profile = request.user.actor_profile
    if request.method == "POST":
        try:
            generate_suggestions(profile)
            messages.success(request, "Your suggestions are ready.")
        except AIError as exc:
            messages.error(request, str(exc))
        return redirect("profiles:actor_insights")

    score, checklist = compute_strength(profile)
    return render(
        request,
        "profiles/actor_insights.html",
        {
            "profile": profile,
            "score": score,
            "checklist": checklist,
            "suggestions": profile.ai_suggestions or {},
            "suggestions_at": profile.ai_suggestions_at,
        },
    )