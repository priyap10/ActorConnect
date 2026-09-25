
from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import redirect


def _needs_verification(request):
    messages.info(request, "Please verify your email address to use this feature.")
    return redirect("accounts:verification_sent")


def verified_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_email_verified:
            return _needs_verification(request)
        return view(request, *args, **kwargs)

    return wrapper


def role_required(role, verified=False):
    """Restrict a view to one account role, optionally requiring a verified email."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role != role:
                raise PermissionDenied
            if verified and not request.user.is_email_verified:
                return _needs_verification(request)
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


class VerifiedRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_email_verified:
            return _needs_verification(request)
        return super().dispatch(request, *args, **kwargs)


class RoleRequiredMixin(VerifiedRequiredMixin):
    required_role = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != self.required_role:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ActorRequiredMixin(RoleRequiredMixin):
    required_role = "actor"


class CastingRequiredMixin(RoleRequiredMixin):
    required_role = "casting"


def can_message(a, b):
    """Two people may message each other if they are connected, or if one has
    applied to a casting call posted by the other."""
    if a.pk == b.pk:
        return False
    from apps.casting.models import Application
    from apps.network.models import Connection

    if Connection.objects.are_connected(a, b):
        return True
    return Application.objects.filter(
        Q(actor=a, role__call__poster=b) | Q(actor=b, role__call__poster=a)
    ).exists()