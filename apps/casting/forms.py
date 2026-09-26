from django import forms
from django.utils import timezone

from apps.portfolio.models import MediaItem
from apps.profiles.models import Language, Skill

from .models import Application, CastingCall, Role


class CastingCallForm(forms.ModelForm):
    class Meta:
        model = CastingCall
        fields = ("title", "production_type", "description", "location", "audition_mode", "compensation", "deadline")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 7}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {"deadline": "Leave blank if there's no fixed deadline."}

    def clean_deadline(self):
        deadline = self.cleaned_data.get("deadline")
        if deadline and deadline < timezone.localdate() and (not self.instance.pk or deadline != self.instance.deadline):
            raise forms.ValidationError("The deadline can't be in the past.")
        return deadline


class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = (
            "name", "description", "gender_preference", "age_min", "age_max",
            "skills", "languages", "requirements", "slots",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "requirements": forms.Textarea(attrs={"rows": 3}),
            "skills": forms.CheckboxSelectMultiple,
            "languages": forms.CheckboxSelectMultiple,
        }

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("age_min"), cleaned.get("age_max")
        if low and high and low > high:
            self.add_error("age_max", "This must be the same as or higher than the lower age.")
        return cleaned


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ("cover_note", "media")
        widgets = {
            "cover_note": forms.Textarea(attrs={"rows": 5}),
            "media": forms.CheckboxSelectMultiple,
        }
        labels = {"cover_note": "Note to the casting team", "media": "Attach performances"}
        help_texts = {"media": "Choose the recordings you want the casting team to watch."}

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["media"].queryset = MediaItem.objects.filter(owner=actor).exclude(category="photo")
        self.fields["media"].required = False


class BriefForm(forms.Form):
    brief = forms.CharField(
        label="Casting brief",
        min_length=40,
        max_length=8000,
        widget=forms.Textarea(attrs={"rows": 14}),
        help_text="Paste the brief you'd send to an agency: the production, the roles and what you need from each actor.",
    )


class CallFilterForm(forms.Form):
    q = forms.CharField(label="Search", required=False, max_length=100)
    production_type = forms.ChoiceField(
        label="Production", required=False, choices=[("", "Any production")] + CastingCall.ProductionType.choices
    )
    audition_mode = forms.ChoiceField(
        label="Audition", required=False, choices=[("", "Any audition type")] + CastingCall.AuditionMode.choices
    )
    compensation = forms.ChoiceField(
        label="Pay", required=False, choices=[("", "Any pay")] + CastingCall.Compensation.choices
    )
    location = forms.CharField(label="Location", required=False, max_length=100)