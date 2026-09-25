"""Small, type-specific parsers; these represent data, not a DNS server."""

import ipaddress
import json
import re
from collections.abc import Callable

from app.models.enums import DNSRecordType
from app.validation.dns_names import validate_zone_name


def validate_hostname(value: str) -> str:
    hostname = validate_zone_name(value)
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return hostname
    raise ValueError("Use a hostname target, not an IP address.")


def validate_a(value: str) -> str:
    return str(ipaddress.IPv4Address(value.strip()))


def validate_aaaa(value: str) -> str:
    if "%" in value:
        raise ValueError("IPv6 scope identifiers are not DNS record values.")
    return str(ipaddress.IPv6Address(value.strip()))


def validate_txt(value: str) -> str:
    if not value:
        raise ValueError("TXT values cannot be empty.")
    # Raw text: no DNS quoting, unescaping, trimming, or case conversion.
    return value


def _number(value: str, maximum: int) -> str:
    if re.fullmatch(r"[0-9]{1,5}", value) is None or int(value) > maximum:
        raise ValueError("Numeric field is outside its allowed range.")
    return str(int(value))


def validate_mx(value: str) -> str:
    parts = value.split()
    if len(parts) != 2:
        raise ValueError("MX requires priority and hostname.")
    return f"{_number(parts[0], 65535)} {validate_hostname(parts[1])}"


def validate_srv(value: str) -> str:
    parts = value.split()
    if len(parts) != 4:
        raise ValueError("SRV requires priority, weight, port, and target.")
    numbers = [_number(part, 65535) for part in parts[:3]]
    target = "." if parts[3] == "." else validate_hostname(parts[3])
    return " ".join([*numbers, target])


def validate_caa(value: str) -> str:
    parts = value.split(maxsplit=2)
    if len(parts) != 3:
        raise ValueError("CAA requires flags, tag, and a quoted value.")
    flags = _number(parts[0], 255)
    tag = parts[1].lower()
    if tag not in {"issue", "issuewild", "iodef"}:
        raise ValueError("Unsupported CAA tag.")
    try:
        content = json.loads(parts[2])
    except (ValueError, RecursionError):
        raise ValueError("CAA content must be a JSON-style quoted string.") from None
    if not isinstance(content, str) or not content.strip():
        raise ValueError("CAA content cannot be empty.")
    return f"{flags} {tag} {json.dumps(content, ensure_ascii=False)}"


_VALIDATORS: dict[DNSRecordType, Callable[[str], str]] = {
    DNSRecordType.A: validate_a,
    DNSRecordType.AAAA: validate_aaaa,
    DNSRecordType.CNAME: validate_hostname,
    DNSRecordType.TXT: validate_txt,
    DNSRecordType.MX: validate_mx,
    DNSRecordType.NS: validate_hostname,
    DNSRecordType.PTR: validate_hostname,
    DNSRecordType.SRV: validate_srv,
    DNSRecordType.CAA: validate_caa,
}


def canonicalize_values(record_type: DNSRecordType, values: list[str]) -> list[str]:
    if not values:
        raise ValueError("Supply at least one value.")
    if record_type == DNSRecordType.CNAME and len(values) != 1:
        raise ValueError("CNAME requires exactly one value.")
    canonical = [_VALIDATORS[record_type](value) for value in values]
    if len(set(canonical)) != len(canonical):
        raise ValueError("Duplicate canonical values are not allowed.")
    return canonical
