"""CacheRegistry — named store for cache adapter instances.

Mirrors ConnectionRegistry but for non-SQL services (Redis, Memcached, etc.).
Adapters are registered by name at startup and retrieved later by views,
services, and HTTP routes.
"""
from lib.core.interfaces import SimpleService


class CacheRegistry:
    """Registry of named cache adapter instances."""

    _adapters: dict[str, SimpleService] = {}

    @classmethod
    def register(cls, name: str, adapter: SimpleService) -> None:
        """Register *adapter* under *name*. Overwrites any existing entry."""
        cls._adapters[name] = adapter

    @classmethod
    def get(cls, name: str) -> SimpleService:
        """Return the adapter for *name* or raise RuntimeError."""
        if name not in cls._adapters:
            raise RuntimeError(f"Cache adapter {name!r} not registered")
        return cls._adapters[name]

    @classmethod
    def list(cls) -> list[str]:
        """Return all registered adapter names."""
        return list(cls._adapters.keys())
