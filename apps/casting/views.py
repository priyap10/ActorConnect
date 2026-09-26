import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import Role as AccountRole
from apps.ai.embeddings import refresh_actor_embedding
from apps.ai.llm import AIError
from apps.ai.matching import rank_actors_for_role, rank_roles_for_actor, score_actor_for_role
from apps.ai.role_breakdown import parse_brief
from apps.core.mixins import safe_next
from apps.core.permissions import role_required, verified_required
from apps.profiles.models import Language, Skill

from .forms import ApplicationForm, BriefForm, CallFilterForm, CastingCallForm, RoleForm
from .models import Application, CastingCall, Role
from .tasks import refresh_role_embedding_task, score_application_task

logger = logging.getLogger(__name__)

casting_only = role_required(AccountRole.CASTING, verified=True)
actor_only = role_required(AccountRole.ACTOR, verified=True)


def _open_calls():
    today = timezone.localdate()
    return CastingCall.objects.filter(status=CastingCall.Status.OPEN).filter(
        Q(deadline__isnull=True) | Q(deadline__gte=today)
    )


def _queue_role_embedding(role_id):
    transaction.on_commit(lambda: refresh_role_embedding_task.delay(role_id))


@verified_required
def call_list(request):
    form = CallFilterForm(request.GET or None)
    calls = (
        _open_calls()
        .select_related("poster", "poster__casting_profile")
        .annotate(role_count=Count("roles", distinct=True))
    )
    if form.is_valid():
        data = form.cleaned_data
        if data["q"]:
            calls = calls.filter(
                Q(title__icontains=data["q"]) | Q(description__icontains=data["q"]) | Q(roles__name__icontains=data["q"])
            ).distinct()
        for field in ("production_type", "audition_mode", "compensation"):
            if data[field]:
                calls = calls.filter(**{field: data[field]})
        if data["location"]:
            calls = calls.filter(location__icontains=data["location"])
    calls = calls.order_by("-created_at", "pk")
    page = Paginator(calls, 10).get_page(request.GET.get("page"))
    return render(request, "casting/call_list.html", {"page_obj": page, "form": form})


@verified_required
def call_detail(request, pk):
    call = get_object_or_404(CastingCall.objects.select_related("poster", "poster__casting_profile"), pk=pk)
    is_owner = call.poster_id == request.user.pk
    if call.status == CastingCall.Status.DRAFT and not is_owner:
        raise Http404

    roles = list(
        call.roles.prefetch_related("skills", "languages").annotate(applicant_count=Count("applications"))
    )
    if request.user.is_actor:
        profile = request.user.actor_profile
        applied = {a.role_id: a for a in Application.objects.filter(actor=request.user, role__call=call)}
        for role in roles:
            role.my_application = applied.get(role.pk)
            match = None if role.my_application else score_actor_for_role(profile, role)
            role.my_match = match if match and match.components else None
    return render(request, "casting/call_detail.html", {"call": call, "roles": roles, "is_owner": is_owner})


@casting_only
def my_calls(request):
    calls = request.user.casting_calls.annotate(
        role_count=Count("roles", distinct=True), applicant_count=Count("roles__applications", distinct=True)
    )
    return render(request, "casting/my_calls.html", {"calls": calls})


@casting_only
def call_create(request):
    form = CastingCallForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        call = form.save(commit=False)
        call.poster = request.user
        call.save()
        messages.success(request, "Draft saved. Add at least one role, then publish the call.")
        return redirect(call)
    return render(request, "casting/call_form.html", {"form": form, "creating": True})


@casting_only
def call_edit(request, pk):
    call = get_object_or_404(CastingCall, pk=pk, poster=request.user)
    form = CastingCallForm(request.POST or None, instance=call)
    if request.method == "POST" and form.is_valid():
        form.save()
        for role_id in call.roles.values_list("pk", flat=True):
            _queue_role_embedding(role_id)
        messages.success(request, "Changes saved.")
        return redirect(call)
    return render(request, "casting/call_form.html", {"form": form, "call": call})


@require_POST
@casting_only
def call_publish(request, pk):
    call = get_object_or_404(CastingCall, pk=pk, poster=request.user)
    if not call.roles.exists():
        messages.error(request, "Add at least one role before publishing.")
    elif call.is_past_deadline:
        messages.error(request, "The deadline has passed. Edit the call to set a new one before publishing.")
    else:
        call.status = CastingCall.Status.OPEN
        call.save(update_fields=["status", "updated_at"])
        messages.success(request, "Your casting call is now open to applications.")
    return redirect(call)


@require_POST
@casting_only
def call_close(request, pk):
    call = get_object_or_404(CastingCall, pk=pk, poster=request.user)
    call.status = CastingCall.Status.CLOSED
    call.save(update_fields=["status", "updated_at"])
    messages.success(request, "The call is closed. Actors can no longer apply.")
    return redirect(call)


@casting_only
def call_delete(request, pk):
    call = get_object_or_404(CastingCall, pk=pk, poster=request.user)
    if request.method == "POST":
        call.delete()
        messages.success(request, "The casting call was deleted.")
        return redirect("casting:my_calls")
    return render(request, "casting/confirm_delete.html", {"object": call, "kind": "casting call"})


@casting_only
def brief(request):
    form = BriefForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            data = parse_brief(form.cleaned_data["brief"])
        except AIError as exc:
            form.add_error(None, str(exc))
        else:
            call = CastingCall.objects.create(
                poster=request.user,
                title=data["title"],
                production_type=data["production_type"],
                description=data["description"],
                location=data["location"],
                audition_mode=data["audition_mode"],
                compensation=data["compensation"],
            )
            skills = {s.name.lower(): s for s in Skill.objects.all()}
            languages = {l.name.lower(): l for l in Language.objects.all()}
            for item in data["roles"]:
                role = Role.objects.create(
                    call=call,
                    name=item["name"],
                    description=item["description"],
                    gender_preference=item["gender_preference"],
                    age_min=item["age_min"],
                    age_max=item["age_max"],
                    requirements=item["requirements"],
                    slots=item["slots"],
                )
                matched_skills = [skills[n.lower()] for n in item["skills"] if n.lower() in skills]
                unmatched = [n for n in item["skills"] if n.lower() not in skills]
                role.skills.set(matched_skills)
                role.languages.set([languages[n.lower()] for n in item["languages"] if n.lower() in languages])
                if unmatched:
                    extra = "Also wanted: " + ", ".join(unmatched)
                    role.requirements = (role.requirements + "\n" + extra).strip()[:800]
                    role.save(update_fields=["requirements"])
                _queue_role_embedding(role.pk)
            messages.success(
                request,
                f"We built a draft with {len(data['roles'])} role(s) from your brief. Check every detail before you publish.",
            )
            return redirect(call)
    return render(request, "casting/brief.html", {"form": form})


@casting_only
def role_create(request, call_pk):
    call = get_object_or_404(CastingCall, pk=call_pk, poster=request.user)
    form = RoleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        role = form.save(commit=False)
        role.call = call
        role.save()
        form.save_m2m()
        _queue_role_embedding(role.pk)
        messages.success(request, "Role added.")
        return redirect(call)
    return render(request, "casting/role_form.html", {"form": form, "call": call, "creating": True})


@casting_only
def role_edit(request, pk):
    role = get_object_or_404(Role.objects.select_related("call"), pk=pk, call__poster=request.user)
    form = RoleForm(request.POST or None, instance=role)
    if request.method == "POST" and form.is_valid():
        form.save()
        _queue_role_embedding(role.pk)
        messages.success(request, "Role updated.")
        return redirect(role.call)
    return render(request, "casting/role_form.html", {"form": form, "call": role.call, "role": role})


@casting_only
def role_delete(request, pk):
    role = get_object_or_404(Role.objects.select_related("call"), pk=pk, call__poster=request.user)
    call = role.call
    if request.method == "POST":
        role.delete()
        messages.success(request, "Role deleted.")
        return redirect(call)
    return render(request, "casting/confirm_delete.html", {"object": role, "kind": "role"})


@casting_only
def role_suggested(request, pk):
    role = get_object_or_404(
        Role.objects.select_related("call").prefetch_related("skills", "languages"), pk=pk, call__poster=request.user
    )
    try:
        matches = rank_actors_for_role(role, limit=20)
    except Exception:
        logger.exception("Could not rank actors for role %s", pk)
        matches = []
        messages.error(request, "Suggestions aren't available right now. Please try again later.")
    applied = set(role.applications.values_list("actor_id", flat=True))
    return render(request, "casting/role_suggested.html", {"role": role, "matches": matches, "applied": applied})


@actor_only
def apply(request, role_id):
    role = get_object_or_404(
        Role.objects.select_related("call", "call__poster").prefetch_related("skills", "languages"), pk=role_id
    )
    call = role.call
    if not call.is_accepting:
        messages.error(request, "This call is no longer accepting applications.")
        return redirect(call)
    if Application.objects.filter(role=role, actor=request.user).exists():
        messages.info(request, "You've already applied for this role.")
        return redirect("casting:my_applications")

    form = ApplicationForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                application = form.save(commit=False)
                application.role, application.actor = role, request.user
                application.save()
                form.save_m2m()
        except IntegrityError:
            messages.info(request, "You've already applied for this role.")
            return redirect("casting:my_applications")
        transaction.on_commit(lambda: score_application_task.delay(application.pk))
        messages.success(request, "Your application is sent.")
        return redirect("casting:my_applications")
    return render(request, "casting/apply.html", {"form": form, "role": role, "call": call})


@actor_only
def my_applications(request):
    applications = request.user.applications.select_related("role", "role__call", "role__call__poster")
    return render(request, "casting/my_applications.html", {"applications": applications})


@require_POST
@actor_only
def application_withdraw(request, pk):
    application = get_object_or_404(
        Application, pk=pk, actor=request.user, status=Application.Status.SUBMITTED
    )
    application.delete()
    messages.success(request, "Application withdrawn.")
    return redirect("casting:my_applications")


@actor_only
def recommended(request):
    profile = request.user.actor_profile
    matches = []
    try:
        if profile.embedding is None:
            refresh_actor_embedding(profile)
        matches = rank_roles_for_actor(profile, limit=20)
    except Exception:
        logger.exception("Could not rank roles for actor profile %s", profile.pk)
        messages.error(request, "Recommendations aren't available right now. Please try again later.")
    return render(request, "casting/recommended.html", {"matches": matches, "profile": profile})


@casting_only
def applicants(request, pk):
    call = get_object_or_404(CastingCall, pk=pk, poster=request.user)
    roles = call.roles.prefetch_related(
        "applications__actor__actor_profile", "applications__media"
    )
    return render(request, "casting/applicants.html", {"call": call, "roles": roles})


@require_POST
@casting_only
def application_status(request, pk):
    application = get_object_or_404(
        Application.objects.select_related("role__call"), pk=pk, role__call__poster=request.user
    )
    new_status = request.POST.get("status")
    if new_status not in Application.Status.values:
        messages.error(request, "That isn't a valid status.")
    else:
        application.status = new_status
        application.save(update_fields=["status", "updated_at"])
        messages.success(request, f"{application.actor.full_name} marked as {application.get_status_display().lower()}.")
    return redirect(safe_next(request, application.role.call.get_absolute_url()))