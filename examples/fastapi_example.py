"""
FastAPI integration example for use-cache.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from use_cache import CacheManager, InMemoryBackend, JsonCoder
from use_cache.integrations.fastapi import cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize cache on startup
    CacheManager.init(
        backend=InMemoryBackend(),
        coder=JsonCoder,
        prefix="fastapi:",
        expire=300  # 5 minutes
    )
    yield
    # Cleanup on shutdown (if needed)


app = FastAPI(title="use-cache FastAPI Example", lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "use-cache FastAPI Example"}


@app.get("/users/{user_id}")
@cache(expire=60)
async def get_user(user_id: int):
    """Get user by ID - cached for 60 seconds."""
    # Simulate database query
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    }


@app.get("/expensive-calculation")
@cache(expire=300)
async def expensive_calculation(x: int = 10, y: int = 20):
    """Expensive calculation - cached for 5 minutes."""
    import asyncio
    await asyncio.sleep(2)  # Simulate expensive operation
    result = x ** y
    return {"x": x, "y": y, "result": result}


@app.post("/clear-cache")
async def clear_cache():
    """Clear all cache."""
    cache_manager = CacheManager.get_instance()
    if cache_manager:
        await cache_manager.clear()
        return {"message": "Cache cleared successfully"}
    return {"message": "Cache not initialized"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
