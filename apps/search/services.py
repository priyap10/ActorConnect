from django.core.paginator import Paginator

from apps.ai.semantic_search import interpret_query, rank_by_text
from apps.profiles.models import ActorProfile

PAGE_SIZE = 12


def run_talent_search(cleaned, page_number, use_ai=True):
    profiles = (
        ActorProfile.objects.filter(is_public=True, user__is_active=True)
        .select_related("user")
        .prefetch_related("skills", "languages")
    )
    query = cleaned.get("q", "").strip()
    interpretation = {}
    if query and use_ai:
        interpretation = interpret_query(query)

    def pick(key):
        return cleaned.get(key) or interpretation.get(key)

    age = cleaned.get("age") or interpretation.get("age")
    if age:
        profiles = profiles.filter(playing_age_min__lte=age, playing_age_max__gte=age)
    if pick("gender"):
        profiles = profiles.filter(gender=pick("gender"))
    if cleaned.get("location") or interpretation.get("location"):
        profiles = profiles.filter(location__icontains=cleaned.get("location") or interpretation["location"])
    if cleaned.get("experience_level"):
        profiles = profiles.filter(experience_level=cleaned["experience_level"])

    languages = [cleaned["language"]] if cleaned.get("language") else interpretation.get("languages", [])
    for language in languages:
        profiles = profiles.filter(languages=language)
    skills = [cleaned["skill"]] if cleaned.get("skill") else interpretation.get("skills", [])
    for skill in skills:
        profiles = profiles.filter(skills=skill)

    mode = "recent"
    if query:
        profiles, mode = rank_by_text(profiles, query)
    else:
        profiles = profiles.order_by("-updated_at", "pk")

    page = Paginator(profiles.distinct() if mode == "keyword" else profiles, PAGE_SIZE).get_page(page_number)
    return {"page": page, "interpretation": interpretation, "mode": mode}