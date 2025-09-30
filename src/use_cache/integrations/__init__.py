"""
Framework integrations for use-cache.
"""

__all__ = []

# Import FastAPI integration if available
try:
    from .fastapi import FastAPICache, cache
except ImportError:
    pass
else:
    __all__ += ["FastAPICache", "cache"]
