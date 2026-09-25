from django.contrib import admin, messages

from .models import ActorProfile, CastingProfile, Language, Skill


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name",)


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(ActorProfile)
class ActorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "headline", "location", "experience_level", "is_public", "updated_at")
    list_filter = ("is_public", "experience_level", "gender")
    search_fields = ("user__full_name", "user__email", "headline")
    exclude = ("embedding",)
    raw_id_fields = ("user",)


@admin.register(CastingProfile)
class CastingProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "organisation", "position", "is_verified")
    list_filter = ("is_verified",)
    search_fields = ("user__full_name", "user__email", "organisation")
    raw_id_fields = ("user",)
    actions = ["mark_verified", "mark_unverified"]

    @admin.action(description="Mark selected as verified")
    def mark_verified(self, request, queryset):
        count = queryset.update(is_verified=True)
        self.message_user(request, f"{count} profile(s) verified.", messages.SUCCESS)

    @admin.action(description="Remove verification from selected")
    def mark_unverified(self, request, queryset):
        count = queryset.update(is_verified=False)
        self.message_user(request, f"{count} profile(s) unverified.", messages.SUCCESS)