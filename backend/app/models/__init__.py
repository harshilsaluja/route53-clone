"""Import all models to register their tables and relationship targets."""

from app.models.dns_record import DNSRecordSet, DNSRecordValue
from app.models.enums import DNSRecordType, HostedZoneType, RoutingPolicy
from app.models.hosted_zone import HostedZone
from app.models.session import Session
from app.models.user import User

__all__ = [
    "User", "Session", "HostedZone", "DNSRecordSet", "DNSRecordValue",
    "HostedZoneType", "DNSRecordType", "RoutingPolicy",
]
