import os
import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from pgvector.django import HnswIndex, VectorField


def avatar_upload_path(instance, filename):
    extension = os.path.splitext(filename)[1].lower()
    return f"avatars/{uuid.uuid4().hex}{extension}"


class Skill(models.Model):
    name = models.CharField(max_length=60, unique=True)
    category = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class Language(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ActorProfile(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        NON_BINARY = "non_binary", "Non-binary"
        UNSPECIFIED = "unspecified", "Prefer not to say"

    class Experience(models.TextChoices):
        BEGINNER = "beginner", "Beginner (up to 2 years)"
        INTERMEDIATE = "intermediate", "Intermediate (2 to 5 years)"
        PROFESSIONAL = "professional", "Professional (5+ years)"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="actor_profile")
    headline = models.CharField(max_length=120, blank=True, help_text="For example: Stage and screen actor, trained in Meisner technique.")
    bio = models.TextField(max_length=2000, blank=True)
    location = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=12, choices=Gender.choices, blank=True)
    playing_age_min = models.PositiveSmallIntegerField(
        "playing age from", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    playing_age_max = models.PositiveSmallIntegerField(
        "playing age to", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    height_cm = models.PositiveSmallIntegerField(
        "height (cm)", null=True, blank=True, validators=[MinValueValidator(90), MaxValueValidator(250)]
    )
    experience_level = models.CharField(max_length=14, choices=Experience.choices, blank=True)
    skills = models.ManyToManyField(Skill, blank=True, related_name="actor_profiles")
    languages = models.ManyToManyField(Language, blank=True, related_name="actor_profiles")
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True)
    is_public = models.BooleanField(
        "visible in search and to other members",
        default=True,
        help_text="If you turn this off, only you can see your profile.",
    )

    embedding = VectorField(dimensions=384, null=True, blank=True)
    embedding_updated_at = models.DateTimeField(null=True, blank=True)
    ai_suggestions = models.JSONField(default=dict, blank=True)
    ai_suggestions_at = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            HnswIndex(
                name="actor_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        ]

    def __str__(self):
        return self.user.full_name

    def get_absolute_url(self):
        return reverse("profiles:actor_detail", args=[self.pk])

    @property
    def playing_age_display(self):
        low, high = self.playing_age_min, self.playing_age_max
        if low and high:
            return f"{low} to {high}"
        return str(low or high or "")


class CastingProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="casting_profile")
    organisation = models.CharField("company or production house", max_length=150, blank=True)
    position = models.CharField("your role", max_length=100, blank=True, help_text="For example: Casting director.")
    website = models.URLField(blank=True)
    bio = models.TextField(max_length=1500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True)
    is_verified = models.BooleanField(
        default=False,
        help_text="Set by ActorConnect staff after checking the person or company is genuine.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.full_name

    def get_absolute_url(self):
        return reverse("profiles:casting_detail", args=[self.pk])