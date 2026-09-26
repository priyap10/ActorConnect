from django.urls import path

from . import views

app_name = "moderation"

urlpatterns = [path("report/<str:target>/<int:pk>/", views.report, name="report")]