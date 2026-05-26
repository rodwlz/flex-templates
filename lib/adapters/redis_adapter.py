from lib.core.interfaces import SimpleService


class RedisAdapter(SimpleService):
    """
    IMPORTANT: uses a dict-based API, NOT standard redis-py conventions.
    Always pass a dict argument, not a plain string key:

        adapter.get({"key": "my_key"})          # correct
        adapter.set({"key": "k", "value": "v"}) # correct
        adapter.get("my_key")                    # WRONG — will raise KeyError

    Actions: get, set, delete, exists, keys, expire, ttl

    get(data: {key}) -> {key, value, found}
    set(data: {key, value, ttl?}) -> {key, stored}
    delete(data: {key}) -> {deleted}
    exists(data: {key}) -> {exists}
    keys(data: {pattern?}) -> {keys}
    expire(data: {key, seconds}) -> {set}
    ttl(data: {key}) -> {ttl}
    """

    @classmethod
    def from_url(cls, url: str) -> "RedisAdapter":
        """Construct from a Redis URL: redis://:password@host:port/db"""
        from urllib.parse import urlparse
        p = urlparse(url)
        return cls(
            host=p.hostname or "localhost",
            port=p.port or 6379,
            password=p.password or "",
            db=int((p.path or "/0").lstrip("/") or 0),
        )

    def __init__(self, host: str, port: int = 6379, password: str = "", db: int = 0):
        import redis
        self._r = redis.Redis(
            host=host, port=port, password=password, db=db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    def get(self, data: dict) -> dict:
        value = self._r.get(data["key"])
        return {"key": data["key"], "value": value, "found": value is not None}

    def set(self, data: dict) -> dict:
        ttl = data.get("ttl")
        self._r.set(data["key"], data["value"], ex=ttl)
        return {"key": data["key"], "stored": True}

    def delete(self, data: dict) -> dict:
        deleted = self._r.delete(data["key"])
        return {"deleted": bool(deleted)}

    def exists(self, data: dict) -> dict:
        return {"exists": bool(self._r.exists(data["key"]))}

    def keys(self, data: dict) -> dict:
        pattern = data.get("pattern", "*")
        return {"keys": self._r.keys(pattern)}

    def expire(self, data: dict) -> dict:
        seconds = data.get("seconds", 0)
        self._r.expire(data["key"], seconds)
        return {"set": True}

    def ttl(self, data: dict) -> dict:
        ttl = self._r.ttl(data["key"])
        return {"ttl": ttl}
