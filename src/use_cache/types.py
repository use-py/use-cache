"""
use-cache cache types and interfaces.
"""
import abc
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, Union

from typing_extensions import Protocol

_Func = Callable[..., Any]


class KeyBuilder(Protocol):
    """Protocol for cache key builders."""
    
    def __call__(
        self,
        __function: _Func,
        __namespace: str = ...,
        *,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        **extra: Any,
    ) -> Union[Awaitable[str], str]:
        """Build a cache key for the given function and arguments."""
        ...


class Backend(abc.ABC):
    """Abstract base class for cache backends."""
    
    @abc.abstractmethod
    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[bytes]]:
        """Get value with TTL. Returns (ttl_seconds, value)."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, key: str) -> Optional[bytes]:
        """Get value by key."""
        raise NotImplementedError

    @abc.abstractmethod
    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        """Set value with optional expiration."""
        raise NotImplementedError

    @abc.abstractmethod
    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        """Clear cache by namespace or specific key."""
        raise NotImplementedError


class Coder(abc.ABC):
    """Abstract base class for value encoders/decoders."""
    
    @classmethod
    @abc.abstractmethod
    def encode(cls, value: Any) -> bytes:
        """Encode value to bytes."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def decode(cls, value: bytes) -> Any:
        """Decode bytes to value."""
        raise NotImplementedError
