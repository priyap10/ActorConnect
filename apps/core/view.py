from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render


def landing(request):
    if request.user.is_authenticated:
        return redirect("feed:home")
    return render(request, "core/landing.html")


def healthz(request):
    """Used by load balancers and container health checks."""
    try:
        connection.ensure_connection()
    except Exception:  # noqa: BLE001
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


def error_403(request, exception=None):
    return render(request, "core/403.html", status=403)


def error_403_csrf(request, reason=""):
    return render(request, "core/403.html", {"csrf_failure": True}, status=403)


def error_404(request, exception=None):
    return render(request, "core/404.html", status=404)


def error_500(request):
    return render(request, "core/500.html", status=500)