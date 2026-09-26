import logging
import re
import threading

from django.conf import settings

from .llm import AIError, complete_json
from .prompts import PERFORMANCE_FEEDBACK_SYSTEM

logger = logging.getLogger(__name__)

FILLERS = ["um", "uh", "er", "erm", "hmm", "you know", "sort of", "kind of"]
LONG_PAUSE_SECONDS = 1.5

_model = None
_lock = threading.Lock()


def _whisper():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from faster_whisper import WhisperModel

                _model = WhisperModel(settings.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(path):
    segments_iter, info = _whisper().transcribe(path, vad_filter=True)
    segments = [(s.start, s.end, s.text.strip()) for s in segments_iter]
    return {
        "text": " ".join(text for _, _, text in segments).strip(),
        "segments": segments,
        "duration": float(info.duration or 0),
        "language": info.language,
    }


def compute_metrics(transcript):
    text = transcript["text"]
    segments = transcript["segments"]
    words = re.findall(r"[\w']+", text.lower())
    speaking_time = sum(end - start for start, end, _ in segments)

    pauses = [
        segments[i + 1][0] - segments[i][1]
        for i in range(len(segments) - 1)
        if segments[i + 1][0] - segments[i][1] >= LONG_PAUSE_SECONDS
    ]
    lowered = f" {' '.join(words)} "
    filler_counts = {f: lowered.count(f" {f} ") for f in FILLERS}
    filler_counts = {k: v for k, v in filler_counts.items() if v}

    return {
        "duration_seconds": round(transcript["duration"], 1),
        "word_count": len(words),
        "words_per_minute": round(len(words) / (speaking_time / 60)) if speaking_time > 5 else None,
        "long_pauses": len(pauses),
        "longest_pause_seconds": round(max(pauses), 1) if pauses else 0,
        "filler_words": filler_counts,
        "language": transcript["language"],
    }


def analyze_media_item(media):
    from apps.portfolio.models import MediaItem

    media.ai_status = MediaItem.AIStatus.PROCESSING
    media.save(update_fields=["ai_status"])
    try:
        transcript = transcribe(media.file.path)
        if len(transcript["text"].split()) < 15:
            raise AIError("We couldn't hear enough speech in this recording to give feedback.")
        metrics = compute_metrics(transcript)
        prompt = (
            f"Statistics: {metrics}\n\n"
            f"<user_content>\n{transcript['text'][:8000]}\n</user_content>"
        )
        feedback = complete_json(
            PERFORMANCE_FEEDBACK_SYSTEM.replace("{kind}", media.get_category_display().lower()),
            prompt,
            max_tokens=900,
        )
        media.transcript = transcript["text"]
        media.ai_feedback = {
            "metrics": metrics,
            "summary": str(feedback.get("summary", ""))[:800],
            "strengths": [str(s)[:300] for s in feedback.get("strengths", [])][:4],
            "improvements": [str(s)[:300] for s in feedback.get("improvements", [])][:4],
            "exercises": [str(s)[:300] for s in feedback.get("exercises", [])][:3],
        }
        media.ai_status = MediaItem.AIStatus.DONE
        media.ai_error = ""
    except AIError as exc:
        media.ai_status = MediaItem.AIStatus.FAILED
        media.ai_error = str(exc)[:200]
    except Exception:
        logger.exception("Performance analysis failed for media %s", media.pk)
        media.ai_status = MediaItem.AIStatus.FAILED
        media.ai_error = "Something went wrong while analysing this file."
    media.save(update_fields=["transcript", "ai_feedback", "ai_status", "ai_error"])