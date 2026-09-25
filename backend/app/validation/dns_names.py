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


_OWNER_LABEL = re.compile(r"[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?")


def record_fqdn(name: str, zone_name: str) -> str:
    return f"{name}.{zone_name}" if name else zone_name


def validate_record_name(value: str, zone_name: str, *, supplied_name: bool = True) -> str:
    name = value.strip().lower()
    if name == "@":
        name = ""
    if supplied_name and (name == zone_name or name.endswith("." + zone_name)):
        raise ValueError("Supply a relative owner name, without the zone suffix.")
    if name:
        labels = name.split(".")
        for index, label in enumerate(labels):
            if label == "*" and index == 0:
                continue
            if _OWNER_LABEL.fullmatch(label) is None:
                raise ValueError("Invalid relative owner label.")
    if len(record_fqdn(name, zone_name)) > 253:
        raise ValueError("The resulting FQDN is too long.")
    return name
