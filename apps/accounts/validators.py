import re

from django.core.exceptions import ValidationError

_BAD_NAME = re.compile(r"[<>@/\\{}\[\]|]|https?:|www\.", re.IGNORECASE)


def validate_full_name(value):
    value = value.strip()
    if len(value) < 2:
        raise ValidationError("Please enter your full name.")
    if _BAD_NAME.search(value):
        raise ValidationError("Names can't contain links or special characters.")