from django.contrib import admin

from .models import Application, CastingCall, Role


class RoleInline(admin.TabularInline):
    model = Role
    extra = 0
    fields = ("name", "gender_preference", "age_min", "age_max", "slots")
    show_change_link = True


@admin.register(CastingCall)
class CastingCallAdmin(admin.ModelAdmin):
    list_display = ("title", "poster", "production_type", "status", "deadline", "created_at")
    list_filter = ("status", "production_type", "audition_mode", "compensation")
    search_fields = ("title", "poster__email", "poster__full_name")
    raw_id_fields = ("poster",)
    inlines = [RoleInline]
    actions = ["close_calls"]

    @admin.action(description="Close selected calls")
    def close_calls(self, request, queryset):
        queryset.update(status=CastingCall.Status.CLOSED)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "call", "gender_preference", "age_min", "age_max")
    search_fields = ("name", "call__title")
    exclude = ("embedding",)
    raw_id_fields = ("call",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("actor", "role", "status", "match_score", "created_at")
    list_filter = ("status",)
    search_fields = ("actor__email", "actor__full_name", "role__name")
    raw_id_fields = ("actor", "role")