from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse

from apps.casting.models import Application
from apps.network.models import Connection

from .models import Notification


def _remember_status(sender, instance, **kwargs):
    instance._previous_status = (
        sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first() if instance.pk else None
    )


pre_save.connect(_remember_status, sender=Connection, dispatch_uid="connection_prev_status")
pre_save.connect(_remember_status, sender=Application, dispatch_uid="application_prev_status")


@receiver(post_save, sender=Connection)
def connection_notifications(sender, instance, created, **kwargs):
    if created and instance.status == Connection.Status.PENDING:
        Notification.send(
            instance.addressee,
            f"{instance.requester.full_name} wants to connect with you.",
            reverse("network:requests"),
            actor=instance.requester,
        )
    elif (
        not created
        and instance.status == Connection.Status.ACCEPTED
        and getattr(instance, "_previous_status", None) == Connection.Status.PENDING
    ):
        Notification.send(
            instance.requester,
            f"{instance.addressee.full_name} accepted your connection request.",
            instance.addressee.get_absolute_url(),
            actor=instance.addressee,
        )


@receiver(post_save, sender=Application)
def application_notifications(sender, instance, created, **kwargs):
    role = instance.role
    if created:
        Notification.send(
            role.call.poster,
            f"{instance.actor.full_name} applied for {role.name} in {role.call.title}.",
            reverse("casting:applicants", args=[role.call_id]),
            actor=instance.actor,
        )
    elif getattr(instance, "_previous_status", None) not in (None, instance.status):
        Notification.send(
            instance.actor,
            f"Your application for {role.name} in {role.call.title} is now: {instance.get_status_display().lower()}.",
            reverse("casting:my_applications"),
            actor=role.call.poster,
        )