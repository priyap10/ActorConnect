import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def refresh_actor_embedding_task(profile_id):
    from apps.profiles.models import ActorProfile

    from .embeddings import refresh_actor_embedding

    try:
        profile = ActorProfile.objects.select_related("user").get(pk=profile_id)
    except ActorProfile.DoesNotExist:
        return
    try:
        refresh_actor_embedding(profile)
    except Exception:
        logger.exception("Could not refresh embedding for actor profile %s", profile_id)