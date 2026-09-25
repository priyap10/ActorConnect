from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", views.SignOutView.as_view(), name="logout"),
    path("verify/sent/", views.verification_sent, name="verification_sent"),
    path("verify/resend/", views.resend_verification, name="resend_verification"),
    path("verify/<str:token>/", views.verify_email, name="verify_email"),
    path("settings/", views.account_settings, name="settings"),
    path("delete/", views.delete_account, name="delete_account"),
    path("password-change/", views.ChangePasswordView.as_view(), name="password_change"),
    path("password-change/done/", views.ChangePasswordDoneView.as_view(), name="password_change_done"),
    path("password-reset/", views.ResetPasswordView.as_view(), name="password_reset"),
    path("password-reset/done/", views.ResetPasswordDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", views.ResetPasswordConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", views.ResetPasswordCompleteView.as_view(), name="password_reset_complete"),
]