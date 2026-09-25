"""Explicit canonicalization helpers; callers apply these before persistence.

Table models never silently mutate names. Database checks reject noncanonical
storage. Hostname syntax and FQDN-to-relative conversion arrive with services.
"""


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_zone_name(value: str) -> str:
    return value.strip().lower().removesuffix(".")
