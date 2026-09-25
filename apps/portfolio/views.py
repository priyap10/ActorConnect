from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import Role
from apps.ai.tasks import refresh_actor_embedding_task
from apps.core.permissions import role_required, verified_required

from .forms import AchievementForm, CreditForm, MediaItemForm
from .models import Achievement, Credit, MediaItem
from .tasks import analyze_media_task

actor_only = role_required(Role.ACTOR)
verified_actor_only = role_required(Role.ACTOR, verified=True)


@actor_only
def manage(request):
    return render(
        request,
        "portfolio/manage.html",
        {
            "media_items": request.user.media_items.all(),
            "credits": request.user.credits.all(),
            "achievements": request.user.achievements.all(),
        },
    )


@verified_required
def media_detail(request, pk):
    item = get_object_or_404(MediaItem.objects.select_related("owner"), pk=pk, owner__is_active=True)
    is_owner = item.owner_id == request.user.pk
    if not is_owner:
        profile = item.owner.profile
        if not item.is_public or profile is None or not getattr(profile, "is_public", True):
            raise Http404
    return render(request, "portfolio/media_detail.html", {"item": item, "is_owner": is_owner})


@verified_actor_only
def media_create(request):
    form = MediaItemForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.owner = request.user
        item.save()
        messages.success(request, "Your upload is saved to your portfolio.")
        return redirect(item)
    return render(request, "portfolio/media_form.html", {"form": form, "creating": True})


@verified_actor_only
def media_edit(request, pk):
    item = get_object_or_404(MediaItem, pk=pk, owner=request.user)
    form = MediaItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Changes saved.")
        return redirect(item)
    return render(request, "portfolio/media_form.html", {"form": form, "item": item})


@verified_actor_only
def media_delete(request, pk):
    item = get_object_or_404(MediaItem, pk=pk, owner=request.user)
    if request.method == "POST":
        item.delete()
        messages.success(request, "The item was deleted.")
        return redirect("portfolio:manage")
    return render(request, "portfolio/confirm_delete.html", {"object": item, "kind": "upload"})


@require_POST
@verified_actor_only
def media_feedback(request, pk):
    item = get_object_or_404(MediaItem, pk=pk, owner=request.user)
    if not item.can_request_feedback:
        messages.info(request, "AI feedback isn't available for this item right now.")
        return redirect(item)
    item.ai_status = MediaItem.AIStatus.PENDING
    item.ai_error = ""
    item.save(update_fields=["ai_status", "ai_error"])
    transaction.on_commit(lambda: analyze_media_task.delay(item.pk))
    messages.success(request, "Analysis started. This page updates when your feedback is ready.")
    return redirect(item)


def _queue_embedding(user):
    profile_id = user.actor_profile.pk
    transaction.on_commit(lambda: refresh_actor_embedding_task.delay(profile_id))


def _crud(model, form_class, name, label):
    @verified_actor_only
    def create(request):
        form = form_class(request.POST or None)
        if request.method == "POST" and form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            _queue_embedding(request.user)
            messages.success(request, f"{label.capitalize()} added.")
            return redirect("portfolio:manage")
        return render(request, "portfolio/simple_form.html", {"form": form, "label": label, "creating": True})

    @verified_actor_only
    def edit(request, pk):
        obj = get_object_or_404(model, pk=pk, owner=request.user)
        form = form_class(request.POST or None, instance=obj)
        if request.method == "POST" and form.is_valid():
            form.save()
            _queue_embedding(request.user)
            messages.success(request, "Changes saved.")
            return redirect("portfolio:manage")
        return render(request, "portfolio/simple_form.html", {"form": form, "label": label})

    @verified_actor_only
    def delete(request, pk):
        obj = get_object_or_404(model, pk=pk, owner=request.user)
        if request.method == "POST":
            obj.delete()
            _queue_embedding(request.user)
            messages.success(request, f"{label.capitalize()} deleted.")
            return redirect("portfolio:manage")
        return render(request, "portfolio/confirm_delete.html", {"object": obj, "kind": label})

    create.__name__, edit.__name__, delete.__name__ = f"{name}_create", f"{name}_edit", f"{name}_delete"
    return create, edit, delete


credit_create, credit_edit, credit_delete = _crud(Credit, CreditForm, "credit", "credit")
achievement_create, achievement_edit, achievement_delete = _crud(
    Achievement, AchievementForm, "achievement", "achievement"
)