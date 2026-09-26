from dataclasses import dataclass, field

import numpy as np
from pgvector.django import CosineDistance

WEIGHTS = {"semantic": 0.40, "skills": 0.20, "languages": 0.15, "age": 0.20, "gender": 0.05}
CANDIDATE_POOL = 200


@dataclass
class MatchResult:
    score: int
    components: list = field(default_factory=list)

    @property
    def summary(self):
        strong = [c["label"].lower() for c in self.components if c["value"] >= 0.8]
        weak = [c["label"].lower() for c in self.components if c["value"] < 0.5]
        text = []
        if strong:
            text.append("Strong on " + ", ".join(strong) + ".")
        if weak:
            text.append("Gaps in " + ", ".join(weak) + ".")
        return " ".join(text) or "Not enough profile detail to compare."

    def as_dict(self):
        return {"score": self.score, "components": self.components}


def cosine_distance(a, b):
    if a is None or b is None:
        return None
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return None
    return float(1 - np.dot(a, b) / denominator)


def _age_fit(profile, role):
    low, high = profile.playing_age_min, profile.playing_age_max
    r_low, r_high = role.age_min, role.age_max
    if not (low or high) or not (r_low or r_high):
        return None
    low, high = low or high, high or low
    r_low, r_high = r_low or r_high, r_high or r_low
    overlap = min(high, r_high) - max(low, r_low)
    if overlap >= 0:
        span = max(1, min(high - low, r_high - r_low))
        return min(1.0, (overlap + 1) / (span + 1)), f"Plays {low} to {high}; role needs {r_low} to {r_high}"
    gap = -overlap
    return max(0.0, 1 - gap / 10), f"Plays {low} to {high}; role needs {r_low} to {r_high}"


def score_actor_for_role(profile, role, distance=None):
    components = []

    if distance is None:
        distance = cosine_distance(profile.embedding, role.embedding)
    if distance is not None:
        similarity = max(0.0, min(1.0, 1 - float(distance)))
        components.append(
            {"key": "semantic", "label": "Overall profile fit", "value": similarity,
             "detail": "How closely the actor's experience reads against the role description"}
        )

    role_skills = {s.name for s in role.skills.all()}
    if role_skills:
        actor_skills = {s.name for s in profile.skills.all()}
        matched = sorted(role_skills & actor_skills)
        missing = sorted(role_skills - actor_skills)
        detail = f"Has {len(matched)} of {len(role_skills)} required skills"
        if missing:
            detail += f" (missing: {', '.join(missing)})"
        components.append({"key": "skills", "label": "Skills", "value": len(matched) / len(role_skills), "detail": detail})

    role_languages = {l.name for l in role.languages.all()}
    if role_languages:
        actor_languages = {l.name for l in profile.languages.all()}
        matched = role_languages & actor_languages
        missing = sorted(role_languages - actor_languages)
        detail = f"Speaks {len(matched)} of {len(role_languages)} required languages"
        if missing:
            detail += f" (missing: {', '.join(missing)})"
        components.append(
            {"key": "languages", "label": "Languages", "value": len(matched) / len(role_languages), "detail": detail}
        )

    age = _age_fit(profile, role)
    if age:
        components.append({"key": "age", "label": "Playing age", "value": age[0], "detail": age[1]})

    if role.gender_preference != "any":
        if profile.gender in ("", "unspecified"):
            components.append({"key": "gender", "label": "Gender", "value": 0.5, "detail": "Actor hasn't stated a gender"})
        else:
            fits = profile.gender == role.gender_preference
            components.append(
                {"key": "gender", "label": "Gender", "value": 1.0 if fits else 0.0,
                 "detail": "Matches the role's requirement" if fits else "Doesn't match the role's requirement"}
            )

    if not components:
        return MatchResult(score=0, components=[])

    total_weight = sum(WEIGHTS[c["key"]] for c in components)
    blended = sum(WEIGHTS[c["key"]] * c["value"] for c in components) / total_weight
    return MatchResult(score=round(blended * 100), components=components)


def rank_actors_for_role(role, limit=20):
    from apps.profiles.models import ActorProfile

    from .embeddings import refresh_role_embedding

    if role.embedding is None:
        refresh_role_embedding(role)

    candidates = (
        ActorProfile.objects.filter(is_public=True, user__is_active=True, embedding__isnull=False)
        .select_related("user")
        .prefetch_related("skills", "languages")
        .annotate(distance=CosineDistance("embedding", role.embedding))
        .order_by("distance")[:CANDIDATE_POOL]
    )
    results = [(p, score_actor_for_role(p, role, distance=p.distance)) for p in candidates]
    results.sort(key=lambda pair: pair[1].score, reverse=True)
    return results[:limit]


def rank_roles_for_actor(profile, limit=20):
    from django.db.models import Q
    from django.utils import timezone

    from apps.casting.models import CastingCall, Role

    if profile.embedding is None:
        return []

    today = timezone.localdate()
    roles = (
        Role.objects.filter(
            call__status=CastingCall.Status.OPEN,
            call__poster__is_active=True,
            embedding__isnull=False,
        )
        .filter(Q(call__deadline__isnull=True) | Q(call__deadline__gte=today))
        .exclude(applications__actor=profile.user)
        .select_related("call", "call__poster")
        .prefetch_related("skills", "languages")
        .annotate(distance=CosineDistance("embedding", profile.embedding))
        .order_by("distance")[:CANDIDATE_POOL]
    )
    results = [(r, score_actor_for_role(profile, r, distance=r.distance)) for r in roles]
    results.sort(key=lambda pair: pair[1].score, reverse=True)
    return results[:limit]