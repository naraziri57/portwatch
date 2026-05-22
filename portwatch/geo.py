"""Optional GeoIP enrichment for port scan entries."""
from __future__ import annotations

import socket
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GeoInfo:
    ip: str
    country: Optional[str] = None
    city: Optional[str] = None
    asn: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "country": self.country,
            "city": self.city,
            "asn": self.asn,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GeoInfo":
        return cls(
            ip=data["ip"],
            country=data.get("country"),
            city=data.get("city"),
            asn=data.get("asn"),
        )

    def __str__(self) -> str:
        parts = [self.ip]
        if self.city:
            parts.append(self.city)
        if self.country:
            parts.append(self.country)
        if self.asn:
            parts.append(f"AS:{self.asn}")
        return " / ".join(parts)


def resolve_hostname(ip: str) -> Optional[str]:
    """Reverse-resolve an IP to a hostname, returns None on failure."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, OSError):
        return None


def enrich_with_geoip(ip: str, db_path: Optional[str] = None) -> GeoInfo:
    """Return a GeoInfo for *ip*.

    If ``geoip2`` is available and *db_path* points to a MaxMind City DB,
    real data is returned.  Otherwise a stub with only the IP is returned so
    the rest of the pipeline can proceed without the optional dependency.
    """
    try:
        import geoip2.database  # type: ignore

        if db_path is None:
            return GeoInfo(ip=ip)
        with geoip2.database.Reader(db_path) as reader:
            response = reader.city(ip)
            return GeoInfo(
                ip=ip,
                country=response.country.iso_code,
                city=response.city.name,
                asn=None,
            )
    except Exception:
        return GeoInfo(ip=ip)
