from django.urls import path

from . import views

app_name = "casting"

urlpatterns = [
    path("", views.call_list, name="call_list"),
    path("mine/", views.my_calls, name="my_calls"),
    path("new/", views.call_create, name="call_create"),
    path("brief/", views.brief, name="brief"),
    path("recommended/", views.recommended, name="recommended"),
    path("applications/", views.my_applications, name="my_applications"),
    path("applications/<int:pk>/withdraw/", views.application_withdraw, name="application_withdraw"),
    path("applications/<int:pk>/status/", views.application_status, name="application_status"),
    path("<int:pk>/", views.call_detail, name="call_detail"),
    path("<int:pk>/edit/", views.call_edit, name="call_edit"),
    path("<int:pk>/publish/", views.call_publish, name="call_publish"),
    path("<int:pk>/close/", views.call_close, name="call_close"),
    path("<int:pk>/delete/", views.call_delete, name="call_delete"),
    path("<int:pk>/applicants/", views.applicants, name="applicants"),
    path("<int:call_pk>/roles/new/", views.role_create, name="role_create"),
    path("roles/<int:pk>/edit/", views.role_edit, name="role_edit"),
    path("roles/<int:pk>/delete/", views.role_delete, name="role_delete"),
    path("roles/<int:pk>/suggested/", views.role_suggested, name="role_suggested"),
    path("roles/<int:role_id>/apply/", views.apply, name="apply"),
]