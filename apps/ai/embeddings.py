import logging
import threading

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model %s", settings.EMBEDDING_MODEL)
                _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def embed_texts(texts):
    vectors = _get_model().encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
    return [vector.tolist() for vector in vectors]


def embed_one(text):
    return embed_texts([text])[0]


def actor_profile_text(profile):
    user = profile.user
    parts = []
    if profile.headline:
        parts.append(profile.headline)
    if profile.experience_level:
        parts.append(f"Experience: {profile.get_experience_level_display()}")
    skills = [s.name for s in profile.skills.all()]
    if skills:
        parts.append("Skills: " + ", ".join(skills))
    languages = [l.name for l in profile.languages.all()]
    if languages:
        parts.append("Languages: " + ", ".join(languages))
    if profile.playing_age_min or profile.playing_age_max:
        parts.append(f"Playing age: {profile.playing_age_display}")
    if profile.gender and profile.gender != "unspecified":
        parts.append(f"Gender: {profile.get_gender_display()}")
    if profile.location:
        parts.append(f"Based in {profile.location}")
    credits = [f"{c.role_name} in {c.project} ({c.get_credit_type_display()})" for c in user.credits.all()[:8]]
    if credits:
        parts.append("Credits: " + "; ".join(credits))
    awards = [a.title for a in user.achievements.all()[:5]]
    if awards:
        parts.append("Achievements: " + "; ".join(awards))
    if profile.bio:
        parts.append(profile.bio)
    return "\n".join(parts)


def role_text(role):
    call = role.call
    parts = [f"{role.name} in a {call.get_production_type_display().lower()}: {call.title}"]
    if role.description:
        parts.append(role.description)
    skills = [s.name for s in role.skills.all()]
    if skills:
        parts.append("Skills: " + ", ".join(skills))
    languages = [l.name for l in role.languages.all()]
    if languages:
        parts.append("Languages: " + ", ".join(languages))
    if role.age_min or role.age_max:
        parts.append(f"Playing age: {role.age_min or ''} to {role.age_max or ''}".strip())
    if role.gender_preference != "any":
        parts.append(f"Gender: {role.get_gender_preference_display()}")
    if role.requirements:
        parts.append(role.requirements)
    if call.location:
        parts.append(f"Location: {call.location}")
    return "\n".join(parts)


def refresh_actor_embedding(profile):
    text = actor_profile_text(profile)
    if not text.strip():
        profile.embedding = None
    else:
        profile.embedding = embed_one(text)
    profile.embedding_updated_at = timezone.now()
    profile.save(update_fields=["embedding", "embedding_updated_at"])


def refresh_role_embedding(role):
    role.embedding = embed_one(role_text(role))
    role.save(update_fields=["embedding"])