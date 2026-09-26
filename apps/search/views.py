from django import forms
from django.shortcuts import render

from apps.core.permissions import verified_required
from apps.profiles.models import ActorProfile, Language, Skill

from .services import run_talent_search


class TalentSearchForm(forms.Form):
    q = forms.CharField(
        label="Describe who you're looking for",
        required=False,
        max_length=300,
        widget=forms.TextInput(attrs={"placeholder": "For example: a Marathi-speaking actor in her thirties with stage combat"}),
    )
    age = forms.IntegerField(label="Playing age", required=False, min_value=5, max_value=100)
    gender = forms.ChoiceField(
        label="Gender", required=False, choices=[("", "Any gender")] + ActorProfile.Gender.choices[:3]
    )
    language = forms.ModelChoiceField(
        label="Language", required=False, queryset=Language.objects.all(), empty_label="Any language"
    )
    skill = forms.ModelChoiceField(label="Skill", required=False, queryset=Skill.objects.all(), empty_label="Any skill")
    experience_level = forms.ChoiceField(
        label="Experience", required=False, choices=[("", "Any experience")] + ActorProfile.Experience.choices
    )
    location = forms.CharField(label="Location", required=False, max_length=100)


@verified_required
def talent(request):
    form = TalentSearchForm(request.GET or None)
    context = {"form": form, "searched": False}
    if request.GET and form.is_valid():
        use_ai = request.GET.get("interpret") != "off"
        result = run_talent_search(form.cleaned_data, request.GET.get("page"), use_ai=use_ai)
        context.update(searched=True, use_ai=use_ai, **result)
    return render(request, "search/talent.html", context)