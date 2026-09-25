"""String enums shared by persistence and future request/response schemas."""

from enum import StrEnum


class HostedZoneType(StrEnum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class DNSRecordType(StrEnum):
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    TXT = "TXT"
    MX = "MX"
    NS = "NS"
    PTR = "PTR"
    SRV = "SRV"
    CAA = "CAA"


class RoutingPolicy(StrEnum):
    SIMPLE = "SIMPLE"
