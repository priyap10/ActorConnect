from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Report(models.Model):
    class Reason(models.TextChoices):
        SPAM = "spam", "Spam or scam"
        HARASSMENT = "harassment", "Harassment or abuse"
        IMPERSONATION = "impersonation", "Pretending to be someone else"
        INAPPROPRIATE = "inappropriate", "Inappropriate content"
        FAKE_CALL = "fake_call", "Fake or misleading casting call"
        OTHER = "other", "Something else"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACTIONED = "actioned", "Action taken"
        DISMISSED = "dismissed", "Dismissed"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    reason = models.CharField(max_length=15, choices=Reason.choices)
    details = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["reporter", "content_type", "object_id"],
                condition=models.Q(status="open"),
                name="one_open_report_per_target",
            )
        ]

    def __str__(self):
        return f"{self.get_reason_display()} on {self.content_type.model} {self.object_id}"