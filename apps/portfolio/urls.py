from django.urls import path

from . import views

app_name = "portfolio"

urlpatterns = [
    path("", views.manage, name="manage"),
    path("media/new/", views.media_create, name="media_create"),
    path("media/<int:pk>/", views.media_detail, name="media_detail"),
    path("media/<int:pk>/edit/", views.media_edit, name="media_edit"),
    path("media/<int:pk>/delete/", views.media_delete, name="media_delete"),
    path("media/<int:pk>/feedback/", views.media_feedback, name="media_feedback"),
    path("credits/new/", views.credit_create, name="credit_create"),
    path("credits/<int:pk>/edit/", views.credit_edit, name="credit_edit"),
    path("credits/<int:pk>/delete/", views.credit_delete, name="credit_delete"),
    path("achievements/new/", views.achievement_create, name="achievement_create"),
    path("achievements/<int:pk>/edit/", views.achievement_edit, name="achievement_edit"),
    path("achievements/<int:pk>/delete/", views.achievement_delete, name="achievement_delete"),
]