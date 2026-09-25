import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeDoneView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core import signing
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import FormView

from .forms import DeleteAccountForm, EmailAuthenticationForm, RegistrationForm

logger = logging.getLogger(__name__)
User = get_user_model()

VERIFY_SALT = "actorconnect.email-verification"


def send_verification_email(request, user):
    token = signing.dumps({"uid": user.pk, "email": user.email}, salt=VERIFY_SALT)
    link = request.build_absolute_uri(reverse("accounts:verify_email", args=[token]))
    body = render_to_string(
        "accounts/emails/verify_email.txt",
        {"user": user, "link": link, "days": settings.EMAIL_VERIFICATION_MAX_AGE // 86400},
    )
    try:
        send_mail("Verify your ActorConnect email address", body, None, [user.email])
    except Exception:
        logger.exception("Could not send verification email to user %s", user.pk)
        return False
    return True


class RegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = RegistrationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("feed:home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        send_verification_email(self.request, user)
        return redirect("accounts:verification_sent")


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class SignOutView(LogoutView):
    pass


@login_required
def verification_sent(request):
    if request.user.is_email_verified:
        return redirect("feed:home")
    return render(request, "accounts/verification_sent.html")


def verify_email(request, token):
    try:
        data = signing.loads(token, salt=VERIFY_SALT, max_age=settings.EMAIL_VERIFICATION_MAX_AGE)
        user = User.objects.get(pk=data["uid"], email=data["email"])
    except (signing.BadSignature, User.DoesNotExist, KeyError):
        return render(request, "accounts/verify_failed.html", status=400)
    if not user.is_email_verified:
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
    messages.success(request, "Your email address is verified. Welcome to ActorConnect.")
    return redirect("feed:home" if request.user.is_authenticated else "accounts:login")


@login_required
@require_POST
def resend_verification(request):
    if request.user.is_email_verified:
        return redirect("feed:home")
    if not cache.add(f"verify-resend:{request.user.pk}", 1, 60):
        messages.info(request, "A verification email was just sent. Please wait a minute before requesting another.")
    elif send_verification_email(request, request.user):
        messages.success(request, "We've sent a new verification link to your email address.")
    else:
        messages.error(request, "We couldn't send the email right now. Please try again shortly.")
    return redirect("accounts:verification_sent")


@login_required
def account_settings(request):
    return render(request, "accounts/settings.html")


@login_required
def delete_account(request):
    form = DeleteAccountForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Your account and all its content have been deleted.")
        return redirect("core:landing")
    return render(request, "accounts/delete_account.html", {"form": form})


class ChangePasswordView(PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:password_change_done")


class ChangePasswordDoneView(PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"


class ResetPasswordView(PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class ResetPasswordDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class ResetPasswordConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class ResetPasswordCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"