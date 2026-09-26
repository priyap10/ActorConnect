import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def refresh_role_embedding_task(role_id):
    from apps.ai.embeddings import refresh_role_embedding

    from .models import Role

    try:
        role = Role.objects.select_related("call").prefetch_related("skills", "languages").get(pk=role_id)
    except Role.DoesNotExist:
        return
    try:
        refresh_role_embedding(role)
    except Exception:
        logger.exception("Could not refresh embedding for role %s", role_id)


@shared_task
def score_application_task(application_id):
    from apps.ai.embeddings import refresh_actor_embedding, refresh_role_embedding
    from apps.ai.matching import score_actor_for_role

    from .models import Application

    try:
        application = Application.objects.select_related("actor__actor_profile", "role__call").get(pk=application_id)
    except Application.DoesNotExist:
        return
    role = application.role
    profile = application.actor.actor_profile
    try:
        if role.embedding is None:
            refresh_role_embedding(role)
        if profile.embedding is None:
            refresh_actor_embedding(profile)
    except Exception:
        logger.exception("Embedding unavailable while scoring application %s", application_id)
    result = score_actor_for_role(profile, role)
    application.match_score = result.score
    application.match_detail = result.as_dict()
    application.save(update_fields=["match_score", "match_detail"])