"""
In-memory cache backend implementation.
"""
import time
from asyncio import Lock
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ..types import Backend


@dataclass
class Value:
    """Internal value container with TTL."""
    data: bytes
    ttl_ts: int


class InMemoryBackend(Backend):
    """
    In-memory cache backend that stores data in process memory.
    
    Note: This backend stores cache data in memory and only deletes when an
    expired key is accessed. This means that if you don't access a function after
    data has been cached, the data will not be removed automatically.
    """
    
    _store: Dict[str, Value] = {}
    _lock = Lock()

    @property
    def _now(self) -> int:
        """Get current timestamp."""
        return int(time.time())

    def _get(self, key: str) -> Optional[Value]:
        """Internal get method with TTL check."""
        v = self._store.get(key)
        if v:
            if v.ttl_ts < self._now:
                del self._store[key]
            else:
                return v
        return None

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[bytes]]:
        """Get value with TTL. Returns (ttl_seconds, value)."""
        async with self._lock:
            v = self._get(key)
            if v:
                return v.ttl_ts - self._now, v.data
            return 0, None

    async def get(self, key: str) -> Optional[bytes]:
        """Get value by key."""
        async with self._lock:
            v = self._get(key)
            if v:
                return v.data
            return None

    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        """Set value with optional expiration."""
        async with self._lock:
            self._store[key] = Value(value, self._now + (expire or 0))

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        """Clear cache by namespace or specific key."""
        count = 0
        async with self._lock:
            if namespace:
                keys = list(self._store.keys())
                for k in keys:
                    if k.startswith(namespace):
                        del self._store[k]
                        count += 1
            elif key:
                if key in self._store:
                    del self._store[key]
                    count += 1
            else:
                # Clear all entries if no namespace or key specified
                count = len(self._store)
                self._store.clear()
        return count