from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Role, User


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.profiles.models import ActorProfile, CastingProfile

    if instance.role == Role.ACTOR:
        ActorProfile.objects.get_or_create(user=instance)
    else:
        CastingProfile.objects.get_or_create(user=instance)