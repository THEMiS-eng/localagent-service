"""
Cache System - Centralized TTL cache for LocalAgent
"""
from typing import Dict, Any, Optional
from time import time


class TTLCache:
    """Simple TTL cache for reducing redundant file reads."""
    
    def __init__(self, ttl_seconds: int = 30):
        self._cache: Dict[str, tuple] = {}
        self._ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, ts = self._cache[key]
            if time() - ts < self._ttl:
                return value
            del self._cache[key]
        return None
    
    def set(self, key: str, value: Any):
        self._cache[key] = (value, time())
    
    def invalidate(self, key: str = None):
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()


# Global cache instance
_cache = TTLCache(ttl_seconds=30)


def get_cache() -> TTLCache:
    return _cache


def cached_get(category: str, project: str, loader_fn):
    """Generic cached getter."""
    key = f"{category}:{project}"
    cached = _cache.get(key)
    if cached is not None:
        return cached
    result = loader_fn(project)
    _cache.set(key, result)
    return result


def invalidate(category: str = None, project: str = None):
    """Invalidate cache entries."""
    if category and project:
        _cache.invalidate(f"{category}:{project}")
    elif category:
        # Invalidate all entries for this category
        keys_to_remove = [k for k in _cache._cache.keys() if k.startswith(f"{category}:")]
        for k in keys_to_remove:
            _cache.invalidate(k)
    else:
        _cache.invalidate()
