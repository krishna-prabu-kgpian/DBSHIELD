import asyncio
import time
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
)


@dataclass
class IPTrackingInfo:
    request_timestamps: List[float] = field(default_factory=list)
    violation_count: int = 0
    last_violation_time: float = 0
    penalty_until: float = 0
    is_blacklisted: bool = False


class IPRateLimiter:
    def __init__(self):
        self._ip_data: Dict[str, IPTrackingInfo] = {}
        self._ip_locks: Dict[str, asyncio.Lock] = {}
        self._state_lock = asyncio.Lock()
        self._blacklist: Set[str] = set()
        self._last_cleanup = time.time()

    async def check_ip(self, ip_address: str) -> Tuple[bool, str]:
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
