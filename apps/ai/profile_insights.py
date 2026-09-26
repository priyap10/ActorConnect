from django.utils import timezone

from .llm import complete_json
from .prompts import PROFILE_SUGGESTIONS_SYSTEM

CHECKLIST = [
    ("avatar", 10, "Profile photo", "Add a clear, well-lit headshot."),
    ("headline", 10, "Headline", "Write a one-line summary of who you are as an actor."),
    ("bio", 15, "About section", "Write at least 150 characters about your training and experience."),
    ("location", 5, "Location", "Tell casting directors where you're based."),
    ("age", 10, "Playing age", "Add the age range you can play."),
    ("skills", 15, "Skills", "Pick at least five skills."),
    ("languages", 5, "Languages", "List the languages you perform in."),
    ("credits", 10, "Credits", "Add at least one credit."),
    ("achievements", 5, "Achievements", "Add an award, training programme or recognition."),
    ("media", 15, "Performance media", "Upload a showreel, monologue or scene."),
]


def compute_strength(profile):
    user = profile.user
    done = {
        "avatar": bool(profile.avatar),
        "headline": len(profile.headline.strip()) >= 15,
        "bio": len(profile.bio.strip()) >= 150,
        "location": bool(profile.location.strip()),
        "age": bool(profile.playing_age_min and profile.playing_age_max),
        "skills": profile.skills.count() >= 5,
        "languages": profile.languages.exists(),
        "credits": user.credits.exists(),
        "achievements": user.achievements.exists(),
        "media": user.media_items.exclude(category="photo").exists(),
    }
    items = [
        {"key": key, "weight": weight, "label": label, "hint": hint, "done": done[key]}
        for key, weight, label, hint in CHECKLIST
    ]
    return sum(i["weight"] for i in items if i["done"]), items


def _profile_brief(profile):
    user = profile.user
    lines = [
        f"Name: {user.full_name}",
        f"Headline: {profile.headline or '(none)'}",
        f"Bio: {profile.bio or '(none)'}",
        f"Location: {profile.location or '(none)'}",
        f"Experience level: {profile.get_experience_level_display() or '(none)'}",
        "Skills: " + (", ".join(s.name for s in profile.skills.all()) or "(none)"),
        "Languages: " + (", ".join(l.name for l in profile.languages.all()) or "(none)"),
        "Credits: " + ("; ".join(f"{c.role_name} in {c.project} ({c.year})" for c in user.credits.all()[:10]) or "(none)"),
        "Achievements: " + ("; ".join(f"{a.title} ({a.year})" for a in user.achievements.all()[:10]) or "(none)"),
    ]
    return "\n".join(lines)


def generate_suggestions(profile):
    data = complete_json(
        PROFILE_SUGGESTIONS_SYSTEM,
        f"<user_content>\n{_profile_brief(profile)}\n</user_content>",
        max_tokens=1200,
    )
    suggestions = {
        "headline_options": [str(h)[:120] for h in (data.get("headline_options") or [])][:3],
        "bio_rewrite": str(data.get("bio_rewrite") or "")[:1200],
        "priorities": [str(p)[:200] for p in (data.get("priorities") or [])][:5],
    }
    profile.ai_suggestions = suggestions
    profile.ai_suggestions_at = timezone.now()
    profile.save(update_fields=["ai_suggestions", "ai_suggestions_at"])
    return suggestions