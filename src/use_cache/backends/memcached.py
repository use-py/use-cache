"""
Memcached cache backend implementation.
"""
from typing import Optional, Tuple

from ..types import Backend

try:
    from aiomcache import Client  # type: ignore
    _memcached_available = True
except ImportError:
    Client = None  # type: ignore
    _memcached_available = False


class MemcachedBackend(Backend):
    """
    Memcached cache backend using aiomcache client.
    
    Note: Memcached doesn't support TTL retrieval, so get_with_ttl returns a default TTL.
    The clear method with namespace is not supported by Memcached protocol.
    """
    
    def __init__(self, mcache: "Client"):  # type: ignore
        if not _memcached_available:
            raise ImportError("aiomcache is not available. Install with: pip install aiomcache")
        
        self.mcache = mcache

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[bytes]]:
        """Get value with TTL. Returns default TTL since Memcached doesn't support TTL retrieval."""
        return 3600, await self.get(key)

    async def get(self, key: str) -> Optional[bytes]:
        """Get value by key."""
        return await self.mcache.get(key.encode())

    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        """Set value with optional expiration."""
        await self.mcache.set(key.encode(), value, exptime=expire or 0)

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        """Clear cache by specific key. Namespace clearing is not supported."""
        if namespace:
            raise NotImplementedError("Memcached doesn't support namespace-based clearing")
        elif key:
            # Memcached doesn't return success status for delete operations
            await self.mcache.delete(key.encode())
            return 1
        return 0