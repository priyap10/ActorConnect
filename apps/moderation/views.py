from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.casting.models import CastingCall
from apps.core.mixins import safe_next
from apps.core.permissions import verified_required
from apps.feed.models import Comment, Post
from apps.portfolio.models import MediaItem

from .models import Report

User = get_user_model()

TARGETS = {
    "post": Post,
    "comment": Comment,
    "media": MediaItem,
    "call": CastingCall,
    "user": User,
}


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ("reason", "details")
        widgets = {"details": forms.Textarea(attrs={"rows": 4})}
        labels = {"details": "Anything else we should know?"}


@verified_required
def report(request, target, pk):
    model = TARGETS.get(target)
    if model is None:
        raise Http404
    obj = get_object_or_404(model, pk=pk)
    if isinstance(obj, User) and obj.pk == request.user.pk:
        raise Http404

    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.reporter = request.user
        item.content_type = ContentType.objects.get_for_model(model)
        item.object_id = obj.pk
        try:
            with transaction.atomic():
                item.save()
        except IntegrityError:
            messages.info(request, "You've already reported this. Our team will review it.")
        else:
            messages.success(request, "Thank you. Our team will review your report.")
        return redirect(safe_next(request, "feed:home"))
    return render(request, "moderation/report.html", {"form": form, "obj": obj, "target": target})