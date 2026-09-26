from django.conf import settings
from django.db import models
from django.db.models import F, Q


class ConnectionManager(models.Manager):
    def between(self, a, b):
        return self.filter(
            Q(requester=a, addressee=b) | Q(requester=b, addressee=a)
        ).first()

    def are_connected(self, a, b):
        return self.filter(status=Connection.Status.ACCEPTED).filter(
            Q(requester=a, addressee=b) | Q(requester=b, addressee=a)
        ).exists()

    def connected_ids(self, user):
        rows = (
            self.filter(status=Connection.Status.ACCEPTED)
            .filter(Q(requester=user) | Q(addressee=user))
            .values_list("requester_id", "addressee_id")
        )
        ids = {uid for row in rows for uid in row}
        ids.discard(user.pk)
        return ids

    def state(self, viewer, other):
        connection = self.between(viewer, other)
        if connection is None:
            return "none", None
        if connection.status == Connection.Status.ACCEPTED:
            return "connected", connection
        if connection.requester_id == viewer.pk:
            return "pending_out", connection
        return "pending_in", connection


class Connection(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Connected"

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="connections_sent")
    addressee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="connections_received")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    objects = ConnectionManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["requester", "addressee"], name="unique_connection_direction"),
            models.CheckConstraint(condition=~Q(requester=F("addressee")), name="no_self_connection"),
        ]
        indexes = [models.Index(fields=["addressee", "status"])]

    def __str__(self):
        return f"{self.requester} to {self.addressee} ({self.status})"