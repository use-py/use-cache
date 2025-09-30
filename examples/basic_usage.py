"""
Basic usage examples for use-cache.
"""

import asyncio
from use_cache import CacheManager, InMemoryBackend, JsonCoder, cache, RedisBackend


async def basic_example():
    """Basic cache usage example."""
    print("=== Basic Cache Usage ===")
    # from redis.asyncio import Redis
    
    # redis_client = Redis(host="127.0.0.1", port=6379, db=0, decode_responses=False)
    
    cache_manager = CacheManager.init(
        backend=InMemoryBackend(),
        coder=JsonCoder,
        prefix="example:",
        expire=60  # 60 seconds
    )
    
    # Manual cache operations
    await cache_manager.set("key1", b'{"message": "Hello, World!"}')
    value = await cache_manager.get("key1")
    print(f"Cached value: {value}")
    
    # Clear cache
    await cache_manager.clear()
    print("Cache cleared")


@cache(expire=30)
async def expensive_operation(x: int, y: int) -> int:
    """Simulate an expensive operation that benefits from caching."""
    print(f"Computing {x} + {y} (expensive operation)")
    await asyncio.sleep(1)  # Simulate work
    return x + y


async def decorator_example():
    """Cache decorator usage example."""
    print("\n=== Cache Decorator Usage ===")
    
    # Initialize cache manager using class method
    cache_manager = CacheManager.init(
        backend=InMemoryBackend(),
        coder=JsonCoder,
        prefix="decorator:",
        expire=60
    )
    
    # First call - will compute and cache
    result1 = await expensive_operation(5, 3)
    print(f"First call result: {result1}")
    
    # Second call - will use cached result
    result2 = await expensive_operation(5, 3)
    print(f"Second call result: {result2}")
    
    # Different parameters - will compute again
    result3 = await expensive_operation(10, 20)
    print(f"Different params result: {result3}")


async def main():
    """Run all examples."""
    await basic_example()
    await decorator_example()


if __name__ == "__main__":
    asyncio.run(main())
