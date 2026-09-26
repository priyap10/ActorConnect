from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from pgvector.django import HnswIndex, VectorField


class CastingCall(models.Model):
    class ProductionType(models.TextChoices):
        FILM = "film", "Film"
        TELEVISION = "television", "Television"
        THEATRE = "theatre", "Theatre"
        WEB_SERIES = "web_series", "Web series"
        COMMERCIAL = "commercial", "Commercial"
        VOICEOVER = "voiceover", "Voiceover"
        MUSIC_VIDEO = "music_video", "Music video"
        OTHER = "other", "Other"

    class AuditionMode(models.TextChoices):
        IN_PERSON = "in_person", "In person"
        SELF_TAPE = "self_tape", "Self-tape"
        HYBRID = "hybrid", "In person or self-tape"

    class Compensation(models.TextChoices):
        PAID = "paid", "Paid"
        STIPEND = "stipend", "Stipend or expenses"
        UNPAID = "unpaid", "Unpaid"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    poster = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="casting_calls")
    title = models.CharField(max_length=150)
    production_type = models.CharField(max_length=12, choices=ProductionType.choices)
    description = models.TextField(max_length=3000)
    location = models.CharField(max_length=100, blank=True)
    audition_mode = models.CharField(max_length=10, choices=AuditionMode.choices, default=AuditionMode.SELF_TAPE)
    compensation = models.CharField(max_length=10, choices=Compensation.choices, default=Compensation.PAID)
    deadline = models.DateField("application deadline", null=True, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("casting:call_detail", args=[self.pk])

    @property
    def is_accepting(self):
        if self.status != self.Status.OPEN:
            return False
        return self.deadline is None or self.deadline >= timezone.localdate()

    @property
    def is_past_deadline(self):
        return self.deadline is not None and self.deadline < timezone.localdate()


class Role(models.Model):
    class GenderPreference(models.TextChoices):
        ANY = "any", "Any"
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        NON_BINARY = "non_binary", "Non-binary"

    call = models.ForeignKey(CastingCall, on_delete=models.CASCADE, related_name="roles")
    name = models.CharField("role name", max_length=100)
    description = models.TextField(max_length=600, blank=True)
    gender_preference = models.CharField(max_length=10, choices=GenderPreference.choices, default=GenderPreference.ANY)
    age_min = models.PositiveSmallIntegerField(
        "playing age from", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    age_max = models.PositiveSmallIntegerField(
        "playing age to", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    skills = models.ManyToManyField("profiles.Skill", blank=True, related_name="roles")
    languages = models.ManyToManyField("profiles.Language", blank=True, related_name="roles")
    requirements = models.TextField("other requirements", max_length=800, blank=True)
    slots = models.PositiveSmallIntegerField("number of actors needed", default=1, validators=[MinValueValidator(1)])
    embedding = VectorField(dimensions=384, null=True, blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            HnswIndex(
                name="role_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.call.title})"

    @property
    def age_display(self):
        if self.age_min and self.age_max:
            return f"{self.age_min} to {self.age_max}"
        return str(self.age_min or self.age_max or "")


class Application(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        SHORTLISTED = "shortlisted", "Shortlisted"
        SELECTED = "selected", "Selected"
        REJECTED = "rejected", "Not selected"

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="applications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    cover_note = models.TextField(max_length=1500, blank=True)
    media = models.ManyToManyField("portfolio.MediaItem", blank=True, related_name="applications")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUBMITTED)
    match_score = models.PositiveSmallIntegerField(null=True, blank=True)
    match_detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-match_score", "created_at"]
        constraints = [models.UniqueConstraint(fields=["role", "actor"], name="one_application_per_role")]

    def __str__(self):
        return f"{self.actor} for {self.role}"