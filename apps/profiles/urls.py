from django.urls import path

from . import views

app_name = "profiles"

urlpatterns = [
    path("me/", views.my_profile, name="my_profile"),
    path("actors/<int:pk>/", views.actor_detail, name="actor_detail"),
    path("actors/edit/", views.actor_edit, name="actor_edit"),
    path("insights/", views.actor_insights, name="actor_insights"),
    path("casting/<int:pk>/", views.casting_detail, name="casting_detail"),
    path("casting/edit/", views.casting_edit, name="casting_edit"),
]