from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("with/<int:user_id>/", views.start, name="start"),
    path("<int:pk>/", views.conversation, name="conversation"),
    path("<int:pk>/poll/", views.poll, name="poll"),
]