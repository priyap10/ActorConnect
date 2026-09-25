from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .managers import UserManager
from .validators import validate_full_name


class Role(models.TextChoices):
    ACTOR = "actor", "Actor"
    CASTING = "casting", "Casting professional"


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("email address", unique=True)
    full_name = models.CharField(max_length=120, validators=[validate_full_name])
    role = models.CharField(max_length=10, choices=Role.choices)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.email

    @property
    def is_actor(self):
        return self.role == Role.ACTOR

    @property
    def is_casting(self):
        return self.role == Role.CASTING

    @property
    def profile(self):
        try:
            return self.actor_profile if self.is_actor else self.casting_profile
        except ObjectDoesNotExist:
            return None

    @property
    def tagline(self):
        profile = self.profile
        if profile is None:
            return ""
        if self.is_actor:
            return profile.headline
        parts = [p for p in (profile.position, profile.organisation) if p]
        return ", ".join(parts)

    @property
    def avatar(self):
        profile = self.profile
        return profile.avatar if profile and profile.avatar else None

    def get_absolute_url(self):
        if self.is_actor:
            return reverse("profiles:actor_detail", args=[self.profile.pk])
        return reverse("profiles:casting_detail", args=[self.profile.pk])

    def conversations(self):
        from apps.messaging.models import Conversation

        return Conversation.objects.filter(Q(user_a=self) | Q(user_b=self))