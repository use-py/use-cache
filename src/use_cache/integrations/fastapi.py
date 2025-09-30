"""
FastAPI integration for use-cache with backward compatibility.
"""
import logging
import sys
from functools import wraps
from inspect import Parameter, Signature, isawaitable, iscoroutinefunction
from typing import (
    Awaitable,
    Callable,
    List,
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

from ..coders import Coder
from ..manager import CacheManager
from ..types import KeyBuilder

try:
    from fastapi.concurrency import run_in_threadpool  # type: ignore
    from fastapi.dependencies.utils import (  # type: ignore
        get_typed_return_annotation,
        get_typed_signature,
    )
    from starlette.requests import Request  # type: ignore
    from starlette.responses import Response  # type: ignore
    from starlette.status import HTTP_304_NOT_MODIFIED  # type: ignore
    _fastapi_available = True
except ImportError:
    run_in_threadpool = None  # type: ignore
    get_typed_return_annotation = None  # type: ignore
    get_typed_signature = None  # type: ignore
    Request = None  # type: ignore
    Response = None  # type: ignore
    HTTP_304_NOT_MODIFIED = 304
    _fastapi_available = False

logger: logging.Logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
P = ParamSpec("P")
R = TypeVar("R")


def _augment_signature(signature: Signature, *extra: Parameter) -> Signature:
    """Augment function signature with extra parameters."""
    if not extra:
        return signature

    parameters = list(signature.parameters.values())
    variadic_keyword_params: List[Parameter] = []
    while parameters and parameters[-1].kind is Parameter.VAR_KEYWORD:
        variadic_keyword_params.append(parameters.pop())

    return signature.replace(parameters=[*parameters, *extra, *variadic_keyword_params])


def _locate_param(
    sig: Signature, dep: Parameter, to_inject: List[Parameter]
) -> Parameter:
    """Locate an existing parameter in the decorated endpoint."""
    param = next(
        (p for p in sig.parameters.values() if p.annotation is dep.annotation), None
    )
    if param is None:
        to_inject.append(dep)
        param = dep
    return param


def _uncacheable(request: Optional["Request"]) -> bool:  # type: ignore
    """Determine if this request should not be cached."""
    if not _fastapi_available:
        return False
    
    # Get cache manager instance
    manager = CacheManager.get_instance()
    if manager is None or not manager.get_enable_status():
        return True
    
    if request is None:
        return False
    if request.method != "GET":
        return True
    return request.headers.get("Cache-Control") == "no-store"


def cache(
    expire: Optional[int] = None,
    coder: Optional[Type[Coder]] = None,
    key_builder: Optional[KeyBuilder] = None,
    namespace: str = "",
    injected_dependency_namespace: str = "__fastapi_cache",
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[Union[R, "Response"]]]]:  # type: ignore
    """
    FastAPI-compatible cache decorator with backward compatibility.
    
    Args:
        expire: Cache expiration time in seconds
        coder: Custom coder for serialization/deserialization
        key_builder: Custom key builder function
        namespace: Cache namespace prefix
        injected_dependency_namespace: Namespace for injected dependencies
        
    Returns:
        Decorated function that caches results with FastAPI integration
    """
    if not _fastapi_available:
        raise ImportError("FastAPI is not available. Install with: pip install fastapi")
    
    injected_request = Parameter(
        name=f"{injected_dependency_namespace}_request",
        annotation=Request,
        kind=Parameter.KEYWORD_ONLY,
    )
    injected_response = Parameter(
        name=f"{injected_dependency_namespace}_response",
        annotation=Response,
        kind=Parameter.KEYWORD_ONLY,
    )

    def wrapper(
        func: Callable[P, Awaitable[R]]
    ) -> Callable[P, Awaitable[Union[R, "Response"]]]:  # type: ignore
        # get_typed_signature ensures that any forward references are resolved first
        wrapped_signature = get_typed_signature(func)  # type: ignore
        to_inject: List[Parameter] = []
        request_param = _locate_param(wrapped_signature, injected_request, to_inject)
        response_param = _locate_param(wrapped_signature, injected_response, to_inject)
        return_type = get_typed_return_annotation(func)  # type: ignore

        @wraps(func)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> Union[R, "Response"]:  # type: ignore
            nonlocal coder, expire, key_builder

            async def ensure_async_func(*args: P.args, **kwargs: P.kwargs) -> R:
                """Run cached sync functions in thread pool just like FastAPI."""
                # Remove injected parameters from kwargs
                kwargs.pop(injected_request.name, None)
                kwargs.pop(injected_response.name, None)

                if iscoroutinefunction(func):
                    return await func(*args, **kwargs)  # type: ignore
                else:
                    return await run_in_threadpool(func, *args, **kwargs)  # type: ignore

            copy_kwargs = kwargs.copy()
            request: Optional["Request"] = copy_kwargs.pop(request_param.name, None)  # type: ignore
            response: Optional["Response"] = copy_kwargs.pop(response_param.name, None)  # type: ignore

            if _uncacheable(request):
                return await ensure_async_func(*args, **kwargs)

            # Get cache manager
            manager = CacheManager.get_instance()
            if manager is None:
                raise RuntimeError("Cache manager not initialized. Call CacheManager.init() first.")

            # Get configuration
            prefix = manager.get_prefix()
            actual_coder = coder() if coder else manager.get_coder()
            expire = expire or manager.get_expire()
            key_builder = key_builder or manager.get_key_builder()
            backend = manager.get_backend()

            cache_key = key_builder(
                func,
                f"{prefix}:{namespace}" if namespace else prefix,
                request=request,
                response=response,
                args=args,
                kwargs=copy_kwargs,
            )
            if isawaitable(cache_key):
                cache_key = await cache_key  # type: ignore
            assert isinstance(cache_key, str), "Key builder must return a string"

            try:
                ttl, cached = await backend.get_with_ttl(cache_key)
            except Exception:
                logger.warning(
                    f"Error retrieving cache key '{cache_key}' from backend:",
                    exc_info=True,
                )
                ttl, cached = 0, None

            if cached is None or (request is not None and request.headers.get("Cache-Control") == "no-cache"):
                # Cache miss
                result = await ensure_async_func(*args, **kwargs)
                to_cache = actual_coder.encode(result)

                try:
                    await backend.set(cache_key, to_cache, expire)
                except Exception:
                    logger.warning(
                        f"Error setting cache key '{cache_key}' in backend:",
                        exc_info=True,
                    )

                if response:
                    response.headers.update(
                        {
                            "Cache-Control": f"max-age={expire}",
                            "ETag": f"W/{hash(to_cache)}",
                            "X-Cache-Status": "MISS",
                        }
                    )

            else:
                # Cache hit
                if response:
                    etag = f"W/{hash(cached)}"
                    response.headers.update(
                        {
                            "Cache-Control": f"max-age={ttl}",
                            "ETag": etag,
                            "X-Cache-Status": "HIT",
                        }
                    )

                    if_none_match = request and request.headers.get("if-none-match")
                    if if_none_match == etag:
                        response.status_code = HTTP_304_NOT_MODIFIED
                        return response  # type: ignore

                result = cast(R, actual_coder.decode(cached))

            return result

        inner.__signature__ = _augment_signature(wrapped_signature, *to_inject)  # type: ignore[attr-defined]
        return inner

    return wrapper


class FastAPICache:
    """
    Backward compatibility wrapper for the original FastAPICache class.
    
    This class provides the same interface as the original FastAPICache
    but delegates to the new CacheManager internally.
    """
    
    @classmethod
    def init(
        cls,
        backend,
        prefix: str = "fastapi-cache",
        expire: int = 600,
        coder: Type[Coder] = None,  # type: ignore
        key_builder: KeyBuilder = None,  # type: ignore
        enable: bool = True,
    ) -> None:
        """Initialize FastAPICache with backward compatibility."""
        from ..coders import JsonCoder
        from ..key_builders import default_key_builder
        
        CacheManager.init(
            backend=backend,
            prefix=prefix,
            expire=expire,
            coder=coder or JsonCoder,
            key_builder=key_builder or default_key_builder,
            enable_status=enable,
        )
    
    @classmethod
    def reset(cls) -> None:
        """Reset the cache manager."""
        CacheManager.reset()
    
    @classmethod
    def get_backend(cls):
        """Get the cache backend."""
        manager = CacheManager.get_instance()
        if manager is None:
            raise RuntimeError("FastAPICache not initialized")
        return manager.get_backend()
    
    @classmethod
    def get_prefix(cls) -> str:
        """Get the cache prefix."""
        manager = CacheManager.get_instance()
        if manager is None:
            raise RuntimeError("FastAPICache not initialized")
        return manager.get_prefix()
    
    @classmethod
    def get_expire(cls) -> int:
        """Get the default expiration time."""
        manager = CacheManager.get_instance()
        if manager is None:
            raise RuntimeError("FastAPICache not initialized")
        return manager.get_expire()
    
    @classmethod
    def get_coder(cls):
        """Get the coder."""
        manager = CacheManager.get_instance()
        if manager is None:
            raise RuntimeError("FastAPICache not initialized")
        return manager.get_coder()
    
    @classmethod
    def get_key_builder(cls):
        """Get the key builder."""
        manager = CacheManager.get_instance()
        if manager is None:
            raise RuntimeError("FastAPICache not initialized")
        return manager.get_key_builder()
    
    @classmethod
    def get_enable(cls) -> bool:
        """Check if caching is enabled."""
        manager = CacheManager.get_instance()
        if manager is None:
            return False
        return manager.get_enable_status()
    
    @classmethod
    def get_cache_status_header(cls) -> str:
        """Get cache status header name."""
        return "X-Cache-Status"
    
    @classmethod
    async def clear(cls, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        """Clear cache entries."""
        manager = CacheManager.get_instance()
        if manager is None:
            raise RuntimeError("FastAPICache not initialized")
        return await manager.clear(namespace=namespace, key=key)
