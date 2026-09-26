import logging

from django.db.models import Q
from pgvector.django import CosineDistance

from .embeddings import embed_one
from .llm import AIError, complete_json
from .prompts import TALENT_QUERY_SYSTEM

logger = logging.getLogger(__name__)


def interpret_query(text):
    try:
        data = complete_json(TALENT_QUERY_SYSTEM, f"<user_content>{text[:500]}</user_content>", max_tokens=300)
    except AIError:
        return {}
    return _clean(data)


def _clean(data):
    from apps.profiles.models import ActorProfile, Language, Skill

    result = {}
    age = data.get("age")
    if isinstance(age, int) and 5 <= age <= 100:
        result["age"] = age
    gender = data.get("gender")
    if gender in {"female", "male", "non_binary"}:
        result["gender"] = gender
    location = data.get("location")
    if isinstance(location, str) and location.strip():
        result["location"] = location.strip()[:100]

    for key, model in (("languages", Language), ("skills", Skill)):
        wanted = [str(v).strip().lower() for v in (data.get(key) or []) if str(v).strip()]
        if wanted:
            found = [obj for obj in model.objects.all() if obj.name.lower() in wanted]
            if found:
                result[key] = found
    return result


def keyword_filter(queryset, text):
    terms = [t for t in text.split() if len(t) > 2][:8]
    query = Q()
    for term in terms:
        query |= Q(headline__icontains=term) | Q(bio__icontains=term) | Q(user__full_name__icontains=term)
    filtered = queryset.filter(query) if terms else queryset
    return filtered.order_by("-updated_at", "pk")


def rank_by_text(queryset, text):
    try:
        vector = embed_one(text)
    except Exception:
        logger.exception("Embedding model unavailable; falling back to keyword search")
        return keyword_filter(queryset, text), "keyword"
    ranked = (
        queryset.filter(embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", vector))
        .order_by("distance")
    )
    return ranked, "semantic"