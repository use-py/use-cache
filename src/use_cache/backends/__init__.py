"""
Cache backends for use-cache.
"""
from ..types import Backend
from .inmemory import InMemoryBackend

__all__ = ["Backend", "InMemoryBackend"]

# Import each backend in turn and add to __all__. This syntax
# is explicitly supported by type checkers, while more dynamic
# syntax would not be recognised.
try:
    from .redis import RedisBackend
except ImportError:
    pass
else:
    __all__ += ["RedisBackend"]

try:
    from .memcached import MemcachedBackend
except ImportError:
    pass
else:
    __all__ += ["MemcachedBackend"]

try:
    from .dynamodb import DynamoDBBackend
except ImportError:
    pass
else:
    __all__ += ["DynamoDBBackend"]
