"""Explicit canonicalization helpers; callers apply these before persistence.

Table models never silently mutate names. Database checks reject noncanonical
storage. Domain syntax is checked in validation/dns_names.py; FQDN-to-relative
conversion remains deferred to the DNS Record API phase.
"""


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_zone_name(value: str) -> str:
    return value.strip().lower().removesuffix(".")
