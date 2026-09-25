from django import forms

from apps.portfolio.validators import validate_image_upload

from .models import ActorProfile, CastingProfile


class _AvatarMixin:
    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and hasattr(avatar, "content_type"):
            validate_image_upload(avatar)
        return avatar


class ActorProfileForm(_AvatarMixin, forms.ModelForm):
    class Meta:
        model = ActorProfile
        fields = (
            "avatar",
            "headline",
            "bio",
            "location",
            "gender",
            "playing_age_min",
            "playing_age_max",
            "height_cm",
            "experience_level",
            "skills",
            "languages",
            "is_public",
        )
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 6}),
            "skills": forms.CheckboxSelectMultiple,
            "languages": forms.CheckboxSelectMultiple,
        }

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("playing_age_min"), cleaned.get("playing_age_max")
        if low and high and low > high:
            self.add_error("playing_age_max", "This must be the same as or higher than the lower age.")
        return cleaned


class CastingProfileForm(_AvatarMixin, forms.ModelForm):
    class Meta:
        model = CastingProfile
        fields = ("avatar", "organisation", "position", "website", "location", "bio")
        widgets = {"bio": forms.Textarea(attrs={"rows": 5})}