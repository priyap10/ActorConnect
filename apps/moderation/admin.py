from django.contrib import admin, messages
from django.utils import timezone

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("created_at", "reason", "content_type", "object_id", "reporter", "status")
    list_filter = ("status", "reason", "content_type")
    search_fields = ("details", "reporter__email")
    readonly_fields = ("reporter", "content_type", "object_id", "target", "reason", "details", "created_at")
    actions = ["mark_actioned", "mark_dismissed"]

    def _resolve(self, request, queryset, status):
        count = queryset.update(status=status, reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"{count} report(s) updated.", messages.SUCCESS)

    @admin.action(description="Mark as action taken")
    def mark_actioned(self, request, queryset):
        self._resolve(request, queryset, Report.Status.ACTIONED)

    @admin.action(description="Dismiss reports")
    def mark_dismissed(self, request, queryset):
        self._resolve(request, queryset, Report.Status.DISMISSED)