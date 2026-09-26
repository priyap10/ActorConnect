from django.urls import path

from . import views

app_name = "network"

urlpatterns = [
    path("", views.connections, name="connections"),
    path("requests/", views.requests_view, name="requests"),
    path("connect/<int:user_id>/", views.send_request, name="send_request"),
    path("requests/<int:pk>/accept/", views.accept, name="accept"),
    path("requests/<int:pk>/decline/", views.decline, name="decline"),
    path("requests/<int:pk>/cancel/", views.cancel, name="cancel"),
    path("connections/<int:pk>/remove/", views.remove, name="remove"),
]