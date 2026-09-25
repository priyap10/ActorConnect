import os

from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {
    "video": {".mp4", ".mov", ".m4v", ".webm"},
    "audio": {".mp3", ".wav", ".m4a", ".ogg"},
    "image": {".jpg", ".jpeg", ".png", ".webp"},
}

CATEGORY_KIND = {
    "monologue": "video",
    "scene": "video",
    "showreel": "video",
    "voice_reel": "audio",
    "photo": "image",
}

KIND_LABEL = {"video": "video", "audio": "audio", "image": "image"}


def sniff_kind(uploaded):
    position = uploaded.tell()
    uploaded.seek(0)
    head = uploaded.read(32)
    uploaded.seek(position)

    if head[:3] == b"\xff\xd8\xff" or head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image"
    if head[4:8] == b"ftyp":
        return "audio" if head[8:12] in (b"M4A ", b"M4B ") else "video"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "video"
    if head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return "audio"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio"
    if head[:4] == b"OggS":
        return "audio"
    return None


def _check_size(uploaded, kind):
    limit_mb = settings.UPLOAD_LIMITS_MB[kind]
    if uploaded.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"This {KIND_LABEL[kind]} file is larger than the {limit_mb} MB limit.")


def _check_image_decodes(uploaded):
    from PIL import Image, UnidentifiedImageError

    try:
        uploaded.seek(0)
        with Image.open(uploaded) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError("This image could not be read. Try saving it again as a JPEG or PNG.")
    finally:
        uploaded.seek(0)


def validate_media_upload(uploaded, category):
    expected = CATEGORY_KIND[category]
    detected = sniff_kind(uploaded)
    extension = os.path.splitext(uploaded.name)[1].lower()

    if detected is None:
        raise ValidationError("This file type isn't supported. Upload MP4, MOV, WebM, MP3, WAV, M4A, OGG, JPEG, PNG or WebP.")
    if detected != expected:
        raise ValidationError(f"{category.replace('_', ' ').capitalize()} items must be {KIND_LABEL[expected]} files.")
    if extension not in ALLOWED_EXTENSIONS[detected]:
        raise ValidationError("The file extension doesn't match the file's contents.")
    _check_size(uploaded, detected)
    if detected == "image":
        _check_image_decodes(uploaded)
    return detected


def validate_image_upload(uploaded):
    if sniff_kind(uploaded) != "image":
        raise ValidationError("Upload a JPEG, PNG or WebP image.")
    extension = os.path.splitext(uploaded.name)[1].lower()
    if extension not in ALLOWED_EXTENSIONS["image"]:
        raise ValidationError("Upload a JPEG, PNG or WebP image.")
    if uploaded.size > settings.AVATAR_MAX_MB * 1024 * 1024:
        raise ValidationError(f"Profile photos must be smaller than {settings.AVATAR_MAX_MB} MB.")
    _check_image_decodes(uploaded)