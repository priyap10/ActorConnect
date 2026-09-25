import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def analyze_media_task(media_id):
    from apps.ai.performance_review import analyze_media_item

    from .models import MediaItem

    try:
        media = MediaItem.objects.get(pk=media_id)
    except MediaItem.DoesNotExist:
        return
    analyze_media_item(media)