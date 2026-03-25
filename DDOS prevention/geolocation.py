"""
IP Geolocation Service with caching and spoofing detection.

Provides:
- MOCKED IP-based city/country lookup for heavy load testing
- LRU cache with TTL for IP -> location mappings
- Spoofing detection (header city vs IP-based city)
"""

import asyncio
import time
import aiohttp
import random
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from enum import Enum

from config import (
    GEOIP_CACHE_MAX_ENTRIES,
    GEOIP_CACHE_TTL_SECONDS,
    GEOIP_API_URL,
    GEOIP_API_TIMEOUT,
    ENABLE_SPOOFING_DETECTION,
    DEMOTE_SPOOFING_TO_SUSPICIOUS,
    LOG_SPOOFING_ATTEMPTS,
    LOCAL_IP_PREFIXES,
    METRO_CITIES,
    TIER2_CITIES,
)

class GeolocationSource(Enum):
    """Source of geolocation information."""
    IP_VERIFIED = "ip_verified"          
    HEADER_VERIFIED = "header_verified"  
    HEADER_ONLY = "header_only"          
    IP_ONLY = "ip_only"                  
    SPOOFING_DETECTED = "spoofing_detected"  
    LOCAL_IP = "local_ip"                
    UNKNOWN = "unknown"                  

@dataclass
class GeolocationResult:
    """Result of geolocation lookup."""
    city: Optional[str]
    country: Optional[str]
    region: Optional[str]
    source: GeolocationSource
    is_spoofing: bool = False
    claimed_city: Optional[str] = None  

    def __str__(self):
        return f"GeolocationResult(city={self.city}, country={self.country}, source={self.source.value}, spoofing={self.is_spoofing})"

@dataclass
class CachedLocation:
    """Cached IP location entry."""
    city: Optional[str]
    country: Optional[str]
    region: Optional[str]
    created_at: float

class IPGeolocationCache:
    """Thread-safe LRU cache for IP -> location mappings."""

    def __init__(
        self,
        max_entries: int = GEOIP_CACHE_MAX_ENTRIES,
        ttl_seconds: int = GEOIP_CACHE_TTL_SECONDS
    ):
        self._cache: Dict[str, CachedLocation] = {}
        self._lock = asyncio.Lock()
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0

    async def get(self, ip: str) -> Optional[CachedLocation]:
        """Get cached location for IP."""
        async with self._lock:
            if ip not in self._cache:
                self.misses += 1
                return None

            entry = self._cache[ip]
            current_time = time.time()

            if current_time - entry.created_at > self.ttl_seconds:
                del self._cache[ip]
                self.misses += 1
                return None

            self.hits += 1
            return entry

    async def set(self, ip: str, city: Optional[str], country: Optional[str], region: Optional[str]):
        """Store location in cache."""
        async with self._lock:
            if len(self._cache) >= self.max_entries and ip not in self._cache:
                oldest_ip = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
                del self._cache[oldest_ip]

            self._cache[ip] = CachedLocation(
                city=city,
                country=country,
                region=region,
                created_at=time.time()
            )

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        async with self._lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                "entries": len(self._cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_percent": round(hit_rate, 2),
            }

class GeolocationService:
    """Main geolocation service with multi-tier lookup and spoofing detection."""

    def __init__(self):
        self.cache = IPGeolocationCache()
        self._http_session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=GEOIP_API_TIMEOUT)
            )
        return self._http_session

    async def close(self):
        """Close HTTP session."""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

    def _is_local_ip(self, ip: str) -> bool:
        """Check if IP is local/private."""
        if not ip:
            return True
        return any(ip.startswith(prefix) for prefix in LOCAL_IP_PREFIXES)

    async def _lookup_ip_api(self, ip: str) -> Optional[Tuple[str, str, str]]:
        """
        MOCKED FOR LOAD TESTING.
        Replaces the real API call to prevent rate-limit bans during DoS simulations.
        """
        # Simulate a fast local DB lookup (e.g., MaxMind) instead of a slow network call
        await asyncio.sleep(0.001) 
        
        # Mix of metro, tier 2, and standard cities to trigger different priority queues
        mock_cities = ["mumbai", "delhi", "bangalore", "ahmedabad", "jaipur", "unknown_city", "small_town"]
        return (random.choice(mock_cities), "India", "State")

    async def get_location(
        self,
        client_ip: str,
        claimed_city: Optional[str] = None
    ) -> GeolocationResult:
        """Get location for client IP with spoofing detection."""
        claimed_city_normalized = claimed_city.lower().strip() if claimed_city else None

        if self._is_local_ip(client_ip):
            if claimed_city_normalized:
                return GeolocationResult(
                    city=claimed_city_normalized,
                    country=None,
                    region=None,
                    source=GeolocationSource.HEADER_ONLY,
                    is_spoofing=False,
                    claimed_city=claimed_city
                )
            return GeolocationResult(
                city=None,
                country=None,
                region=None,
                source=GeolocationSource.LOCAL_IP,
                is_spoofing=False,
                claimed_city=claimed_city
            )

        cached = await self.cache.get(client_ip)
        if cached:
            ip_city = cached.city.lower() if cached.city else None
            return self._build_result(
                ip_city=ip_city,
                ip_country=cached.country,
                ip_region=cached.region,
                claimed_city=claimed_city,
                claimed_city_normalized=claimed_city_normalized
            )

        lookup_result = await self._lookup_ip_api(client_ip)

        if lookup_result:
            ip_city, ip_country, ip_region = lookup_result
            await self.cache.set(client_ip, ip_city, ip_country, ip_region)

            ip_city_normalized = ip_city.lower() if ip_city else None
            return self._build_result(
                ip_city=ip_city_normalized,
                ip_country=ip_country,
                ip_region=ip_region,
                claimed_city=claimed_city,
                claimed_city_normalized=claimed_city_normalized
            )

        if claimed_city_normalized:
            return GeolocationResult(
                city=claimed_city_normalized,
                country=None,
                region=None,
                source=GeolocationSource.HEADER_ONLY,
                is_spoofing=False,
                claimed_city=claimed_city
            )

        return GeolocationResult(
            city=None,
            country=None,
            region=None,
            source=GeolocationSource.UNKNOWN,
            is_spoofing=False,
            claimed_city=claimed_city
        )

    def _build_result(
        self,
        ip_city: Optional[str],
        ip_country: Optional[str],
        ip_region: Optional[str],
        claimed_city: Optional[str],
        claimed_city_normalized: Optional[str]
    ) -> GeolocationResult:
        """Build GeolocationResult with spoofing detection."""
        if not claimed_city_normalized:
            return GeolocationResult(
                city=ip_city,
                country=ip_country,
                region=ip_region,
                source=GeolocationSource.IP_ONLY,
                is_spoofing=False,
                claimed_city=claimed_city
            )

        if not ip_city:
            return GeolocationResult(
                city=claimed_city_normalized,
                country=ip_country,
                region=ip_region,
                source=GeolocationSource.HEADER_ONLY,
                is_spoofing=False,
                claimed_city=claimed_city
            )

        if not ENABLE_SPOOFING_DETECTION:
            return GeolocationResult(
                city=claimed_city_normalized,
                country=ip_country,
                region=ip_region,
                source=GeolocationSource.HEADER_VERIFIED,
                is_spoofing=False,
                claimed_city=claimed_city
            )

        is_match = self._cities_match(claimed_city_normalized, ip_city)

        if is_match:
            return GeolocationResult(
                city=claimed_city_normalized,
                country=ip_country,
                region=ip_region,
                source=GeolocationSource.HEADER_VERIFIED,
                is_spoofing=False,
                claimed_city=claimed_city
            )

        if DEMOTE_SPOOFING_TO_SUSPICIOUS:
            return GeolocationResult(
                city=ip_city,  
                country=ip_country,
                region=ip_region,
                source=GeolocationSource.SPOOFING_DETECTED,
                is_spoofing=True,
                claimed_city=claimed_city
            )
        else:
            return GeolocationResult(
                city=ip_city,
                country=ip_country,
                region=ip_region,
                source=GeolocationSource.IP_VERIFIED,
                is_spoofing=False,
                claimed_city=claimed_city
            )

    def _cities_match(self, claimed: str, ip_city: str) -> bool:
        """Check if claimed city matches IP city."""
        if claimed == ip_city:
            return True

        aliases = {
            "bangalore": {"bengaluru", "bangalore"},
            "bengaluru": {"bengaluru", "bangalore"},
            "delhi": {"delhi", "new delhi"},
            "new delhi": {"delhi", "new delhi"},
            "mumbai": {"mumbai", "bombay"},
            "bombay": {"mumbai", "bombay"},
            "chennai": {"chennai", "madras"},
            "madras": {"chennai", "madras"},
            "kolkata": {"kolkata", "calcutta"},
            "calcutta": {"kolkata", "calcutta"},
            "gurgaon": {"gurgaon", "gurugram"},
            "gurugram": {"gurgaon", "gurugram"},
        }

        claimed_aliases = aliases.get(claimed, {claimed})
        ip_aliases = aliases.get(ip_city, {ip_city})

        if claimed_aliases & ip_aliases:
            return True

        if claimed in ip_city or ip_city in claimed:
            return True

        return False

    async def get_stats(self) -> dict:
        """Get geolocation service statistics."""
        cache_stats = await self.cache.get_stats()
        return {
            "cache": cache_stats,
            "spoofing_detection_enabled": ENABLE_SPOOFING_DETECTION,
        }

geolocation_service = GeolocationService()