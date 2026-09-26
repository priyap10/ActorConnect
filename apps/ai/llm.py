import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class AIError(Exception):
    pass


class AIUnavailable(AIError):
    pass


class AIServiceError(AIError):
    pass


def _client():
    if not settings.ANTHROPIC_API_KEY:
        raise AIUnavailable("AI features are not switched on for this installation yet.")
    import anthropic

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=60.0, max_retries=2)


def complete(system, user, max_tokens=1500):
    client = _client()
    try:
        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except Exception as exc:
        logger.exception("Anthropic request failed")
        raise AIServiceError("The AI service didn't respond. Please try again in a moment.") from exc
    return "".join(block.text for block in response.content if getattr(block, "type", "") == "text").strip()


def complete_json(system, user, max_tokens=1500):
    text = complete(system, user, max_tokens=max_tokens)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        logger.warning("Model returned no JSON object: %.200s", text)
        raise AIServiceError("The AI service returned an unexpected answer. Please try again.")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        logger.warning("Model returned invalid JSON: %.200s", text)
        raise AIServiceError("The AI service returned an unexpected answer. Please try again.") from exc