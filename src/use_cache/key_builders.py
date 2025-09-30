"""
Cache key builders for generating cache keys.
"""
import hashlib
from typing import Any, Callable, Dict, Tuple


def default_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    *,
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    **extra: Any,
) -> str:
    """
    Default key builder that creates cache keys from function signature and arguments.
    
    Args:
        func: The function being cached
        namespace: Cache namespace
        args: Function positional arguments
        kwargs: Function keyword arguments
        **extra: Additional context (ignored in default implementation)
        
    Returns:
        Cache key string
    """
    cache_key = hashlib.md5(  # noqa: S324
        f"{func.__module__}:{func.__name__}:{args}:{kwargs}".encode()
    ).hexdigest()
    return f"{namespace}:{cache_key}"


def simple_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    *,
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    **extra: Any,
) -> str:
    """
    Simple key builder that uses function name and arguments.
    
    Args:
        func: The function being cached
        namespace: Cache namespace
        args: Function positional arguments
        kwargs: Function keyword arguments
        **extra: Additional context (ignored in simple implementation)
        
    Returns:
        Cache key string
    """
    parts = [namespace, func.__name__]
    if args:
        parts.append(str(args))
    if kwargs:
        parts.append(str(sorted(kwargs.items())))
    return ":".join(filter(None, parts))