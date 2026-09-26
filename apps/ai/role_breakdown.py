from .llm import AIServiceError, complete_json
from .prompts import ROLE_BREAKDOWN_SYSTEM

PRODUCTION_TYPES = {"film", "television", "theatre", "web_series", "commercial", "voiceover", "music_video", "other"}
AUDITION_MODES = {"in_person", "self_tape", "hybrid"}
COMPENSATION = {"paid", "stipend", "unpaid"}
GENDERS = {"any", "female", "male", "non_binary"}
MAX_ROLES = 15


def _age(value):
    return value if isinstance(value, int) and 1 <= value <= 100 else None


def sanitize(data):
    roles = []
    for raw in (data.get("roles") or [])[:MAX_ROLES]:
        if not isinstance(raw, dict) or not str(raw.get("name", "")).strip():
            continue
        age_min, age_max = _age(raw.get("age_min")), _age(raw.get("age_max"))
        if age_min and age_max and age_min > age_max:
            age_min, age_max = age_max, age_min
        slots = raw.get("slots")
        gender = raw.get("gender_preference")
        roles.append(
            {
                "name": str(raw["name"]).strip()[:100],
                "description": str(raw.get("description") or "")[:600],
                "gender_preference": gender if gender in GENDERS else "any",
                "age_min": age_min,
                "age_max": age_max,
                "skills": [str(s).strip() for s in (raw.get("skills") or []) if str(s).strip()][:15],
                "languages": [str(s).strip() for s in (raw.get("languages") or []) if str(s).strip()][:8],
                "requirements": str(raw.get("requirements") or "")[:800],
                "slots": slots if isinstance(slots, int) and 1 <= slots <= 50 else 1,
            }
        )
    if not roles:
        raise AIServiceError("We couldn't find any roles in that brief. Add a little more detail about who you're casting.")

    production_type = data.get("production_type")
    audition_mode = data.get("audition_mode")
    compensation = data.get("compensation")
    return {
        "title": str(data.get("title") or "Untitled casting call").strip()[:150],
        "production_type": production_type if production_type in PRODUCTION_TYPES else "other",
        "description": str(data.get("description") or "")[:1500],
        "location": str(data.get("location") or "")[:100],
        "audition_mode": audition_mode if audition_mode in AUDITION_MODES else "self_tape",
        "compensation": compensation if compensation in COMPENSATION else "unpaid",
        "roles": roles,
    }


def parse_brief(brief_text):
    data = complete_json(
        ROLE_BREAKDOWN_SYSTEM,
        f"<user_content>\n{brief_text[:8000]}\n</user_content>",
        max_tokens=2500,
    )
    return sanitize(data)