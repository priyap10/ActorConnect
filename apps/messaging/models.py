from django.conf import settings
from django.db import models
from django.db.models import F, Q


class ConversationManager(models.Manager):
    def between(self, a, b):
        low, high = (a, b) if a.pk < b.pk else (b, a)
        conversation, _ = self.get_or_create(user_a=low, user_b=high)
        return conversation


class Conversation(models.Model):
    user_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    user_b = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    objects = ConversationManager()

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["user_a", "user_b"], name="unique_conversation_pair"),
            models.CheckConstraint(condition=Q(user_a__lt=F("user_b")), name="conversation_users_ordered"),
        ]

    def other(self, user):
        return self.user_b if user.pk == self.user_a_id else self.user_a

    def includes(self, user):
        return user.pk in (self.user_a_id, self.user_b_id)


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["conversation", "id"])]