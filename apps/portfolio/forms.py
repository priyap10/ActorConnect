from django import forms

from .models import Achievement, Credit, MediaItem
from .validators import validate_media_upload


class MediaItemForm(forms.ModelForm):
    class Meta:
        model = MediaItem
        fields = ("title", "category", "file", "description", "is_public")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._detected_kind = None
        if self.instance.pk:
            del self.fields["file"]
            del self.fields["category"]
        else:
            self.fields["file"].help_text = (
                "Video: MP4, MOV or WebM up to 200 MB. Audio: MP3, WAV, M4A or OGG up to 50 MB. "
                "Photos: JPEG, PNG or WebP up to 8 MB."
            )

    def clean(self):
        cleaned = super().clean()
        uploaded, category = cleaned.get("file"), cleaned.get("category")
        if uploaded and category and not self.errors.get("file"):
            try:
                self._detected_kind = validate_media_upload(uploaded, category)
            except forms.ValidationError as exc:
                self.add_error("file", exc)
        return cleaned

    def save(self, commit=True):
        item = super().save(commit=False)
        if self._detected_kind:
            item.file_kind = self._detected_kind
        if commit:
            item.save()
        return item


class CreditForm(forms.ModelForm):
    class Meta:
        model = Credit
        fields = ("project", "role_name", "credit_type", "year", "director", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class AchievementForm(forms.ModelForm):
    class Meta:
        model = Achievement
        fields = ("title", "issuer", "year", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}