"""
use-cache - A framework-agnostic caching library.

This library provides a caching solution that can work with multiple
backends (Redis, Memcached, DynamoDB, InMemory) and can be integrated with
various frameworks including FastAPI.
"""

__version__ = "0.1.0"

# Core components
from .manager import CacheManager
from .decorators import cache, cache_one_minute, cache_one_hour, cache_one_day
from .types import Backend, Coder, KeyBuilder

# Backends
from .backends import InMemoryBackend

# Coders
from .coders import JsonCoder, PickleCoder, StringCoder

# Key builders
from .key_builders import default_key_builder, simple_key_builder

__all__ = [
    # Core
    "CacheManager",
    "cache",
    "cache_one_minute", 
    "cache_one_hour",
    "cache_one_day",
    
    # Types
    "Backend",
    "Coder", 
    "KeyBuilder",
    
    # Backends
    "InMemoryBackend",
    
    # Coders
    "JsonCoder",
    "PickleCoder", 
    "StringCoder",
    
    # Key builders
    "default_key_builder",
    "simple_key_builder",
]

# Optional backends (only export if dependencies are available)
try:
    from .backends.redis import RedisBackend
    __all__.append("RedisBackend")
except ImportError:
    pass

try:
    from .backends.memcached import MemcachedBackend
    __all__.append("MemcachedBackend")
except ImportError:
    pass

try:
    from .backends.dynamodb import DynamoDBBackend
    __all__.append("DynamoDBBackend")
except ImportError:
    pass
