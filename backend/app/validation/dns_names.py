"""Basic ASCII domain validation, without DNS lookups or IDN conversion."""

import re

from app.normalization import normalize_zone_name

_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


def validate_zone_name(value: str) -> str:
    name = normalize_zone_name(value)
    if not name or len(name) > 253:
        raise ValueError("Domain names must contain between 1 and 253 characters.")
    if any(_LABEL.fullmatch(label) is None for label in name.split(".")):
        raise ValueError(
            "Use ASCII domain labels of 1–63 letters, digits, or hyphens; "
            "labels cannot start or end with a hyphen."
        )
    return name
