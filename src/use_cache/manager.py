"""use-cache cache manager for managing cache backends and configuration."""
from typing import Optional, Type

from .coders import Coder, JsonCoder
from .key_builders import default_key_builder
from .types import Backend, KeyBuilder


class CacheManager:
    """
    Framework-agnostic cache manager that handles cache configuration and operations.
    
    This replaces the FastAPI-specific FastAPICache with a use-cache implementation.
    """
    
    _instance: Optional["CacheManager"] = None
    
    def __init__(
        self,
        backend: Backend,
        prefix: str = "use-cache:",
        expire: int = 600,
        coder: Type[Coder] = JsonCoder,
        key_builder: KeyBuilder = default_key_builder,
        enable_status: bool = True,
    ):
        self._backend = backend
        self._prefix = prefix
        self._expire = expire
        self._coder = coder()
        self._key_builder = key_builder
        self._enable_status = enable_status
    
    @classmethod
    def init(
        cls,
        backend: Backend,
        prefix: str = "use-cache:",
        expire: int = 600,
        coder: Type[Coder] = JsonCoder,
        key_builder: KeyBuilder = default_key_builder,
        enable_status: bool = True,
    ) -> "CacheManager":
        """Initialize the global cache manager instance."""
        cls._instance = cls(
            backend=backend,
            prefix=prefix,
            expire=expire,
            coder=coder,
            key_builder=key_builder,
            enable_status=enable_status,
        )
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> Optional["CacheManager"]:
        """Get the global cache manager instance."""
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the global cache manager instance."""
        cls._instance = None
    
    def get_backend(self) -> Backend:
        """Get the cache backend."""
        return self._backend
    
    def get_prefix(self) -> str:
        """Get the cache key prefix."""
        return self._prefix
    
    def get_expire(self) -> int:
        """Get the default expiration time."""
        return self._expire
    
    def get_coder(self) -> Coder:
        """Get the coder instance."""
        return self._coder
    
    def get_key_builder(self) -> KeyBuilder:
        """Get the key builder function."""
        return self._key_builder
    
    def get_enable_status(self) -> bool:
        """Get the enable status."""
        return self._enable_status
    
    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        """Clear cache entries."""
        return await self._backend.clear(namespace=namespace, key=key)
    
    async def get(self, key: str) -> Optional[bytes]:
        """Get a value from cache."""
        return await self._backend.get(key)
    
    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        """Set a value in cache."""
        await self._backend.set(key, value, expire or self._expire)
