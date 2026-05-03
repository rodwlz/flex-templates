"""CacheRegistry: named store for cache adapter instances (Redis, Memcached, etc.)."""
from unittest.mock import MagicMock
import pytest

from lib.services.cache_registry import CacheRegistry


@pytest.fixture(autouse=True)
def clean():
    CacheRegistry._adapters = {}
    yield
    CacheRegistry._adapters = {}


def test_register_and_get():
    adapter = MagicMock()
    CacheRegistry.register("redis", adapter)
    assert CacheRegistry.get("redis") is adapter


def test_get_missing_raises():
    with pytest.raises(RuntimeError, match="not registered"):
        CacheRegistry.get("nonexistent")


def test_list_returns_registered_names():
    CacheRegistry.register("a", MagicMock())
    CacheRegistry.register("b", MagicMock())
    assert set(CacheRegistry.list()) == {"a", "b"}


def test_register_overwrites_existing():
    a, b = MagicMock(), MagicMock()
    CacheRegistry.register("redis", a)
    CacheRegistry.register("redis", b)
    assert CacheRegistry.get("redis") is b


def test_empty_registry_lists_nothing():
    assert CacheRegistry.list() == []
