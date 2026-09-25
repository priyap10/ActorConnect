import os
import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone


def media_upload_path(instance, filename):
    extension = os.path.splitext(filename)[1].lower()
    return f"portfolio/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{extension}"


class MediaItem(models.Model):
    class Category(models.TextChoices):
        MONOLOGUE = "monologue", "Monologue"
        SCENE = "scene", "Scene"
        SHOWREEL = "showreel", "Showreel"
        VOICE_REEL = "voice_reel", "Voice reel"
        PHOTO = "photo", "Photo"

    class FileKind(models.TextChoices):
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"
        IMAGE = "image", "Image"

    class AIStatus(models.TextChoices):
        NONE = "none", "Not requested"
        PENDING = "pending", "Queued"
        PROCESSING = "processing", "Analysing"
        DONE = "done", "Ready"
        FAILED = "failed", "Failed"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="media_items")
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=1000, blank=True)
    category = models.CharField(max_length=12, choices=Category.choices)
    file = models.FileField(upload_to=media_upload_path)
    file_kind = models.CharField(max_length=6, choices=FileKind.choices)
    is_public = models.BooleanField(
        "visible on my profile",
        default=True,
        help_text="Turn this off to keep the item private. You can still attach it to applications.",
    )

    transcript = models.TextField(blank=True)
    ai_feedback = models.JSONField(default=dict, blank=True)
    ai_status = models.CharField(max_length=12, choices=AIStatus.choices, default=AIStatus.NONE)
    ai_error = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "-created_at"])]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("portfolio:media_detail", args=[self.pk])

    @property
    def can_request_feedback(self):
        return self.file_kind in (self.FileKind.VIDEO, self.FileKind.AUDIO) and self.ai_status not in (
            self.AIStatus.PENDING,
            self.AIStatus.PROCESSING,
        )

    @property
    def ai_in_progress(self):
        return self.ai_status in (self.AIStatus.PENDING, self.AIStatus.PROCESSING)


@receiver(post_delete, sender=MediaItem)
def delete_media_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)


class Credit(models.Model):
    class CreditType(models.TextChoices):
        FILM = "film", "Film"
        TELEVISION = "television", "Television"
        THEATRE = "theatre", "Theatre"
        WEB = "web", "Web series"
        COMMERCIAL = "commercial", "Commercial"
        OTHER = "other", "Other"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="credits")
    project = models.CharField("project title", max_length=150)
    role_name = models.CharField("role", max_length=100)
    credit_type = models.CharField("type", max_length=12, choices=CreditType.choices)
    year = models.PositiveSmallIntegerField(validators=[MinValueValidator(1950), MaxValueValidator(2100)])
    director = models.CharField(max_length=100, blank=True)
    description = models.TextField(max_length=600, blank=True)

    class Meta:
        ordering = ["-year", "project"]

    def __str__(self):
        return f"{self.role_name} in {self.project} ({self.year})"


class Achievement(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievements")
    title = models.CharField(max_length=150)
    issuer = models.CharField("awarded by", max_length=120, blank=True)
    year = models.PositiveSmallIntegerField(validators=[MinValueValidator(1950), MaxValueValidator(2100)])
    description = models.TextField(max_length=600, blank=True)

    class Meta:
        ordering = ["-year", "title"]

    def __str__(self):
        return f"{self.title} ({self.year})"