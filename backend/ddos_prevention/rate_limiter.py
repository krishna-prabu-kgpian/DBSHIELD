"""
Rate limiting and request validation for DDoS protection.
"""

import asyncio
import time
import sqlparse
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from .config import (
    IP_REQUESTS_PER_SECOND,
    IP_REQUESTS_PER_MINUTE,
    VIOLATIONS_FOR_TEMP_BAN,
    VIOLATIONS_FOR_BLACKLIST,
    BASE_BAN_SECONDS,
    BAN_MULTIPLIER,
    MAX_BAN_SECONDS,
    QUERY_HISTORY_MAX_ENTRIES,
    QUERY_HISTORY_TTL_SECONDS,
    QUERY_HISTORY_CLEANUP_INTERVAL,
    MAX_QUERY_LENGTH,
    MAX_BODY_SIZE,
    BLOCKED_SQL_KEYWORDS,
)


@dataclass
class IPTrackingInfo:
    """Tracks rate limiting and penalty info per IP."""
    request_timestamps: List[float] = field(default_factory=list)
    violation_count: int = 0
    last_violation_time: float = 0
    penalty_until: float = 0
    is_blacklisted: bool = False


class IPRateLimiter:
    """
    Multi-tier IP-based rate limiting with progressive penalties.
    """

    def __init__(self):
        self._ip_data: Dict[str, IPTrackingInfo] = {}
        self._ip_locks: Dict[str, asyncio.Lock] = {}
        self._state_lock = asyncio.Lock()
        self._blacklist: Set[str] = set()
        self._last_cleanup = time.time()

    async def check_ip(self, ip_address: str) -> Tuple[bool, str]:
        """Check if IP is allowed to make request."""
        async with self._state_lock:
            if ip_address in self._blacklist:
                return False, "IP permanently blacklisted"

            if ip_address not in self._ip_data:
                self._ip_data[ip_address] = IPTrackingInfo()
                self._ip_locks[ip_address] = asyncio.Lock()

            info = self._ip_data[ip_address]
            ip_lock = self._ip_locks[ip_address]

        async with ip_lock:
            current_time = time.time()

            if info.penalty_until > current_time:
                remaining = int(info.penalty_until - current_time)
                return False, f"IP temporarily banned for {remaining}s"

            info.request_timestamps = [
                t for t in info.request_timestamps
                if current_time - t < 60
            ]

            recent_second = sum(1 for t in info.request_timestamps if current_time - t < 1)
            if recent_second >= IP_REQUESTS_PER_SECOND:
                await self._record_violation(ip_address, info, current_time)
                return False, f"Rate limit exceeded: {IP_REQUESTS_PER_SECOND}/second"

            if len(info.request_timestamps) >= IP_REQUESTS_PER_MINUTE:
                await self._record_violation(ip_address, info, current_time)
                return False, f"Rate limit exceeded: {IP_REQUESTS_PER_MINUTE}/minute"

            info.request_timestamps.append(current_time)

            if current_time - self._last_cleanup > 300: 
                await self._cleanup_old_ips(current_time)
                self._last_cleanup = current_time

            return True, ""

    async def _record_violation(self, ip: str, info: IPTrackingInfo, current_time: float):
        """Record violation and apply progressive penalties."""
        info.violation_count += 1
        info.last_violation_time = current_time

        if info.violation_count >= VIOLATIONS_FOR_BLACKLIST:
            async with self._state_lock:
                self._blacklist.add(ip)
            info.is_blacklisted = True
            print(f"[BLACKLIST] IP {ip} permanently blacklisted after {info.violation_count} violations")
        elif info.violation_count >= VIOLATIONS_FOR_TEMP_BAN:
            multiplier = info.violation_count - VIOLATIONS_FOR_TEMP_BAN
            ban_duration = BASE_BAN_SECONDS * (BAN_MULTIPLIER ** multiplier)
            ban_duration = min(ban_duration, MAX_BAN_SECONDS)
            info.penalty_until = current_time + ban_duration
            print(f"[TEMP BAN] IP {ip} banned for {ban_duration}s (violation #{info.violation_count})")

    async def _cleanup_old_ips(self, current_time: float):
        """Remove IPs with no recent activity."""
        async with self._state_lock:
            stale_ips = [
                ip for ip, info in self._ip_data.items()
                if (not info.request_timestamps or
                    current_time - max(info.request_timestamps) > 300)
                and not info.is_blacklisted
                and info.penalty_until < current_time
            ]
            for ip in stale_ips:
                del self._ip_data[ip]
                self._ip_locks.pop(ip, None)

    async def add_to_blacklist(self, ip: str):
        """Manually blacklist an IP."""
        async with self._state_lock:
            self._blacklist.add(ip)
            if ip in self._ip_data:
                self._ip_data[ip].is_blacklisted = True
            print(f"[BLACKLIST] IP {ip} manually added to blacklist")

    async def remove_from_blacklist(self, ip: str):
        """Remove IP from blacklist."""
        async with self._state_lock:
            self._blacklist.discard(ip)
            if ip in self._ip_data:
                self._ip_data[ip].is_blacklisted = False
                self._ip_data[ip].violation_count = 0
                self._ip_data[ip].penalty_until = 0
            print(f"[BLACKLIST] IP {ip} removed from blacklist")

    async def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        async with self._state_lock:
            return {
                "tracked_ips": len(self._ip_data),
                "blacklisted_ips": len(self._blacklist),
                "blacklist": list(self._blacklist),
            }


class BoundedQueryHistory:
    """
    Thread-safe, memory-bounded query history for AST-based rate limiting.
    Upgraded to use O(1) eviction via OrderedDict to survive DoS floods.
    """

    def __init__(
        self,
        max_entries: int = QUERY_HISTORY_MAX_ENTRIES,
        ttl_seconds: int = QUERY_HISTORY_TTL_SECONDS,
        cleanup_interval: int = QUERY_HISTORY_CLEANUP_INTERVAL
    ):
        # Using OrderedDict for O(1) LRU caching
        self._history: OrderedDict[str, List[float]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.cleanup_interval = cleanup_interval

    async def record_and_check(self, query_hash: str, threshold: int, window: int) -> bool:
        """
        Atomically records timestamp and checks if rate limited.
        """
        async with self._lock:
            current_time = time.time()

            if current_time - self._last_cleanup > self.cleanup_interval:
                await self._cleanup_stale_entries(current_time)
                self._last_cleanup = current_time

            # O(1) Eviction Logic
            if query_hash not in self._history:
                if len(self._history) >= self.max_entries:
                    # Instantly pop the oldest item from the front
                    self._history.popitem(last=False)
                self._history[query_hash] = []
            else:
                # Move accessed item to the back (most recently used)
                self._history.move_to_end(query_hash)

            timestamps = self._history[query_hash]
            self._history[query_hash] = [t for t in timestamps if current_time - t < window]

            if len(self._history[query_hash]) >= threshold:
                return True

            self._history[query_hash].append(current_time)
            return False

    async def _cleanup_stale_entries(self, current_time: float):
        """Remove entries with no recent activity."""
        stale_keys = [
            k for k, v in self._history.items()
            if not v or current_time - max(v) > self.ttl_seconds
        ]
        for key in stale_keys:
            del self._history[key]

    async def get_stats(self) -> dict:
        """Get query history statistics."""
        async with self._lock:
            total_timestamps = sum(len(v) for v in self._history.values())
            return {
                "unique_hashes": len(self._history),
                "total_timestamps": total_timestamps,
                "max_entries": self.max_entries,
            }


class RequestValidator:
    """Validates incoming requests for DDoS mitigation."""

    def __init__(
        self,
        max_query_length: int = MAX_QUERY_LENGTH,
        max_body_size: int = MAX_BODY_SIZE,
        blocked_keywords: set = None
    ):
        self.max_query_length = max_query_length
        self.max_body_size = max_body_size
        self.blocked_keywords = blocked_keywords or BLOCKED_SQL_KEYWORDS

    def validate(self, query: str, body_size: int) -> Tuple[bool, str]:
        """Validate request."""
        if body_size > self.max_body_size:
            return False, f"Request body exceeds {self.max_body_size} bytes"

        if len(query) > self.max_query_length:
            return False, f"Query exceeds {self.max_query_length} characters"

        if not query or not query.strip():
            return False, "Empty query"

        query_upper = query.upper()
        for keyword in self.blocked_keywords:
            if f" {keyword} " in f" {query_upper} ":
                return False, f"Blocked SQL keyword detected: {keyword}"

        try:
            parsed = sqlparse.parse(query)
            if not parsed or not parsed[0].tokens:
                return False, "Unable to parse query"
        except Exception:
            return False, "Invalid SQL syntax"

        return True, ""
