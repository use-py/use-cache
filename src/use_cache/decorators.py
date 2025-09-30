"""
use-cache cache decorators that work with any framework.
"""
import logging
import sys
from functools import wraps
from inspect import iscoroutinefunction
from typing import (
    Any,
    Awaitable,
    Callable,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

from .coders import Coder
from .manager import CacheManager
from .types import KeyBuilder

logger: logging.Logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
P = ParamSpec("P")
R = TypeVar("R")


def cache(
    expire: Optional[int] = None,
    coder: Optional[Type[Coder]] = None,
    key_builder: Optional[KeyBuilder] = None,
    namespace: str = "",
    cache_manager: Optional[CacheManager] = None,
) -> Callable[[Callable[P, Union[R, Awaitable[R]]]], Callable[P, Awaitable[R]]]:
    """
    use-cache cache decorator that works with both sync and async functions.
    
    Args:
        expire: Cache expiration time in seconds
        coder: Custom coder for serialization/deserialization
        key_builder: Custom key builder function
        namespace: Cache namespace prefix
        cache_manager: Custom cache manager instance
        
    Returns:
        Decorated function that caches results
    """
    
    def wrapper(func: Callable[P, Union[R, Awaitable[R]]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            nonlocal coder, expire, key_builder, cache_manager
            
            # Use provided cache manager or global default
            manager = cache_manager or CacheManager.get_instance()
            if manager is None:
                raise RuntimeError("No cache manager configured. Call CacheManager.init() first.")
            
            # Get configuration from manager if not provided
            actual_coder = coder() if coder else manager.get_coder()
            expire = expire or manager.get_expire()
            key_builder = key_builder or manager.get_key_builder()
            backend = manager.get_backend()
            prefix = manager.get_prefix()
            
            # Build cache key
            cache_key = key_builder(
                func,
                f"{prefix}:{namespace}" if namespace else prefix,
                args=args,
                kwargs=kwargs,
            )
            
            # Handle async key builders
            if hasattr(cache_key, '__await__'):
                cache_key = await cache_key  # type: ignore
            
            assert isinstance(cache_key, str), "Key builder must return a string"
            
            # Try to get from cache
            try:
                ttl, cached = await backend.get_with_ttl(cache_key)
            except Exception:
                logger.warning(
                    f"Error retrieving cache key '{cache_key}' from backend:",
                    exc_info=True,
                )
                ttl, cached = 0, None
            
            if cached is None:  # Cache miss
                # Execute the original function
                if iscoroutinefunction(func):
                    result = await func(*args, **kwargs)  # type: ignore
                else:
                    result = func(*args, **kwargs)  # type: ignore
                
                # Cache the result
                to_cache = actual_coder.encode(result)
                try:
                    await backend.set(cache_key, to_cache, expire)
                except Exception:
                    logger.warning(
                        f"Error setting cache key '{cache_key}' in backend:",
                        exc_info=True,
                    )
                
                return cast(R, result)
            else:  # Cache hit
                return cast(R, actual_coder.decode(cached))
        
        return inner
    
    return wrapper


def cache_one_minute(
    namespace: str = "",
    cache_manager: Optional[CacheManager] = None,
) -> Callable[[Callable[P, Union[R, Awaitable[R]]]], Callable[P, Awaitable[R]]]:
    """Convenience decorator for 1-minute cache."""
    return cache(expire=60, namespace=namespace, cache_manager=cache_manager)


def cache_one_hour(
    namespace: str = "",
    cache_manager: Optional[CacheManager] = None,
) -> Callable[[Callable[P, Union[R, Awaitable[R]]]], Callable[P, Awaitable[R]]]:
    """Convenience decorator for 1-hour cache."""
    return cache(expire=3600, namespace=namespace, cache_manager=cache_manager)


def cache_one_day(
    namespace: str = "",
    cache_manager: Optional[CacheManager] = None,
) -> Callable[[Callable[P, Union[R, Awaitable[R]]]], Callable[P, Awaitable[R]]]:
    """Convenience decorator for 1-day cache."""
    return cache(expire=86400, namespace=namespace, cache_manager=cache_manager)
