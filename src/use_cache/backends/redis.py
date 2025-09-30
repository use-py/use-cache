"""
Redis cache backend implementation.
"""
from typing import Optional, Tuple, Union

from ..types import Backend

try:
    from redis.asyncio.client import Redis  # type: ignore
    from redis.asyncio.cluster import RedisCluster  # type: ignore
    _redis_available = True
except ImportError:
    Redis = None  # type: ignore
    RedisCluster = None  # type: ignore
    _redis_available = False


class RedisBackend(Backend):
    """
    Redis cache backend that supports both single Redis instances and Redis clusters.
    
    Note: When using the Redis backend, please make sure you pass in a redis client 
    that does not decode responses (decode_responses must be False, which is the default). 
    Cached data is stored as bytes (binary), decoding these in the Redis client would break caching.
    """
    
    def __init__(self, redis: Union["Redis[bytes]", "RedisCluster[bytes]"]):  # type: ignore
        if not _redis_available:
            raise ImportError("Redis is not available. Install with: pip install redis")
        
        self.redis = redis
        self.is_cluster: bool = RedisCluster is not None and isinstance(redis, RedisCluster)

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[bytes]]:
        """Get value with TTL. Returns (ttl_seconds, value)."""
        async with self.redis.pipeline(transaction=not self.is_cluster) as pipe:
            return await pipe.ttl(key).get(key).execute()  # type: ignore[union-attr,no-any-return]

    async def get(self, key: str) -> Optional[bytes]:
        """Get value by key."""
        return await self.redis.get(key)  # type: ignore[union-attr]

    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        """Set value with optional expiration."""
        await self.redis.set(key, value, ex=expire)  # type: ignore[union-attr]

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        """Clear cache by namespace or specific key."""
        if namespace:
            lua = f"for i, name in ipairs(redis.call('KEYS', '{namespace}:*')) do redis.call('DEL', name); end"
            return await self.redis.eval(lua, numkeys=0)  # type: ignore[union-attr,no-any-return]
        elif key:
            return await self.redis.delete(key)  # type: ignore[union-attr]
        return 0