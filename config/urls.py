from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("profiles/", include("apps.profiles.urls")),
    path("portfolio/", include("apps.portfolio.urls")),
    path("feed/", include("apps.feed.urls")),
    path("network/", include("apps.network.urls")),
    path("casting/", include("apps.casting.urls")),
    path("messages/", include("apps.messaging.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("search/", include("apps.search.urls")),
    path("moderation/", include("apps.moderation.urls")),
]

handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"

if settings.DEBUG:
    # In production, serve /media/ from nginx or object storage instead.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)