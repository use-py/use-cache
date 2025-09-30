"""
Pytest-based tests for use-cache.
"""

import asyncio
import os
import sys
import time
import pytest
import pytest_asyncio
from typing import cast
from datetime import datetime, date
from decimal import Decimal

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from use_cache.manager import CacheManager
from use_cache.backends.inmemory import InMemoryBackend
try:
    from use_cache.backends.redis import RedisBackend
except Exception:
    RedisBackend = None  # type: ignore
from use_cache.coders import JsonCoder, StringCoder
from use_cache.decorators import cache


@pytest.fixture(autouse=True)
def _reset_manager():
    """Ensure global CacheManager is reset before each test."""
    CacheManager.reset()
    yield
    CacheManager.reset()


@pytest.fixture
def cache_manager():
    """Provide initialized CacheManager for tests."""
    manager = CacheManager.init(
        backend=InMemoryBackend(),
        coder=JsonCoder,
        prefix="test:",
        expire=60,
    )
    return manager


class TestCacheManager:
    """Test CacheManager functionality."""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_manager: CacheManager):
        """Test basic set and get operations."""
        await cache_manager.set("key1", b'{"data": "value1"}')
        result = await cache_manager.get("key1")
        assert result == b'{"data": "value1"}'

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache_manager: CacheManager):
        """Test getting a non-existent key returns None."""
        result = await cache_manager.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_cache(self, cache_manager: CacheManager):
        """Test clearing the cache."""
        await cache_manager.set("key1", b"value1")
        await cache_manager.set("key2", b"value2")
        
        # Clear all cache entries by clearing the backend directly
        await cache_manager._backend.clear()
        
        assert await cache_manager.get("key1") is None
        assert await cache_manager.get("key2") is None

    @pytest.mark.asyncio
    async def test_clear_namespace(self, cache_manager: CacheManager):
        """Clear by namespace via manager backend."""
        await cache_manager.set("ns1:key1", b"value1")
        await cache_manager.set("ns1:key2", b"value2")
        await cache_manager.set("ns2:key1", b"value3")

        await cache_manager._backend.clear("ns1")

        assert await cache_manager.get("ns1:key1") is None
        assert await cache_manager.get("ns1:key2") is None
        assert await cache_manager.get("ns2:key1") == b"value3"


class TestInMemoryBackend:
    """Test InMemoryBackend functionality."""

    def get_backend(self):
        return InMemoryBackend()

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test basic set and get operations."""
        backend = self.get_backend()
        await backend.set("key1", b"value1", 60)
        result = await backend.get("key1")
        assert result == b"value1"

    @pytest.mark.asyncio
    async def test_get_with_ttl(self):
        """Test get_with_ttl operation."""
        backend = self.get_backend()
        await backend.set("key1", b"value1", 60)
        ttl, result = await backend.get_with_ttl("key1")
        assert result == b"value1"
        assert ttl > 0

    @pytest.mark.asyncio
    async def test_clear_namespace(self):
        """Test clearing by namespace."""
        backend = self.get_backend()
        await backend.set("ns1:key1", b"value1", 60)
        await backend.set("ns1:key2", b"value2", 60)
        await backend.set("ns2:key1", b"value3", 60)
        
        await backend.clear("ns1")
        
        assert await backend.get("ns1:key1") is None
        assert await backend.get("ns1:key2") is None
        assert await backend.get("ns2:key1") == b"value3"

    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        """Verify that expired keys are removed on access."""
        backend = self.get_backend()
        await backend.set("expiring", b"value", expire=1)
        # Wait until expiry accounting for integer-second TTL
        ttl, _ = await backend.get_with_ttl("expiring")
        await asyncio.sleep(ttl + 1.0)
        val = await backend.get("expiring")
        assert val is None


class TestCoders:
    """Test coder functionality."""

    def test_json_coder(self):
        """Test JsonCoder encode/decode."""
        coder = JsonCoder()
        data = {"key": "value", "number": 42}
        
        encoded = coder.encode(data)
        decoded = coder.decode(encoded)
        
        assert decoded == data

    def test_string_coder(self):
        """Test StringCoder encode/decode."""
        coder = StringCoder()
        data = "test string"
        
        encoded = coder.encode(data)
        decoded = coder.decode(encoded)
        
        assert decoded == data

    def test_json_coder_special_types(self):
        """Test JsonCoder with datetime, date, Decimal."""
        coder = JsonCoder()
        payload = {
            "ts": datetime(2024, 1, 2, 3, 4, 5),
            "d": date(2024, 1, 2),
            "amount": Decimal("123.45"),
        }
        encoded = coder.encode(payload)
        decoded = coder.decode(encoded)
        assert isinstance(decoded["ts"], datetime)
        assert isinstance(decoded["d"], date)
        assert isinstance(decoded["amount"], Decimal)
        assert decoded["amount"] == Decimal("123.45")


class TestCacheDecorator:
    """Test cache decorator functionality."""

    @pytest.mark.asyncio
    async def test_cache_decorator_async(self):
        """Test that cache decorator works."""
        # Setup cache
        CacheManager.init(
            backend=InMemoryBackend(),
            coder=JsonCoder,
            prefix="decorator:",
            expire=60
        )
        
        call_count = 0
        
        @cache(expire=60)
        async def test_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call should execute function
        result1 = await test_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call should use cache
        result2 = await test_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment
        
        # Different parameter should execute function again
        result3 = await test_function(10)
        assert result3 == 20
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cache_decorator_sync(self):
        """Test decorator with sync functions (await async wrapper)."""
        CacheManager.init(
            backend=InMemoryBackend(),
            coder=JsonCoder,
            prefix="decorator:",
            expire=60,
        )

        call_count = 0

        @cache(expire=60)
        def sync_func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 3

        result1 = await sync_func(4)
        assert result1 == 12
        assert call_count == 1

        result2 = await sync_func(4)
        assert result2 == 12
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_decorator_without_manager_raises(self):
        """Calling decorated function without CacheManager should raise RuntimeError."""
        CacheManager.reset()

        @cache(expire=10)
        async def foo(x: int) -> int:
            return x

        with pytest.raises(RuntimeError):
            await foo(1)


@pytest.mark.skipif(RedisBackend is None, reason="redis backend not available")
class TestRedisBackend:
    """Test RedisBackend functionality when redis server is available."""

    @pytest_asyncio.fixture(scope="class")
    async def redis_client(self):
        try:
            from redis.asyncio import Redis
        except Exception:
            pytest.skip("redis asyncio client not installed")
        import os
        host = os.getenv("REDIS_HOST", "127.0.0.1")
        port = int(os.getenv("REDIS_PORT", "6379"))
        client = Redis(host=host, port=port, db=0, decode_responses=False)
        # Try ping; skip if cannot connect
        try:
            await client.ping()
        except Exception:
            try:
                await client.aclose()
            except Exception:
                pass
            pytest.skip(f"redis server not available at {host}:{port}")
        yield client
        try:
            await client.aclose()
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_set_get_ttl(self, redis_client):
        assert RedisBackend is not None
        backend = RedisBackend(redis_client)
        await backend.set("uc:test:key", b"value", expire=2)
        ttl, v = await backend.get_with_ttl("uc:test:key")
        assert v == b"value"
        assert ttl > 0
        await asyncio.sleep(ttl + 1)
        v2 = await backend.get("uc:test:key")
        assert v2 is None

    @pytest.mark.asyncio
    async def test_clear_namespace(self, redis_client):
        assert RedisBackend is not None
        backend = RedisBackend(redis_client)
        await backend.set("nsA:k1", b"v1", expire=30)
        await backend.set("nsA:k2", b"v2", expire=30)
        await backend.set("nsB:k1", b"v3", expire=30)
        removed = await backend.clear("nsA")
        assert removed >= 2
        assert await backend.get("nsA:k1") is None
        assert await backend.get("nsA:k2") is None
        assert await backend.get("nsB:k1") == b"v3"


"""Pytest entry is automatic; no manual runner needed."""
