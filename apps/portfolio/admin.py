from django.contrib import admin

from .models import Achievement, Credit, MediaItem


@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "category", "file_kind", "is_public", "ai_status", "created_at")
    list_filter = ("category", "file_kind", "is_public", "ai_status")
    search_fields = ("title", "owner__email", "owner__full_name")
    readonly_fields = ("created_at", "transcript", "ai_feedback")


@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    list_display = ("project", "role_name", "owner", "credit_type", "year")
    list_filter = ("credit_type",)
    search_fields = ("project", "owner__email")


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "year")
    search_fields = ("title", "owner__email")