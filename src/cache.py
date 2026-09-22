import logging
import os

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DEFAULT_TTL = int(os.getenv("CACHE_TTL", "10"))

try:
    _client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=1)
    _client.ping()
except Exception:
    logger.warning("Redis not available at %s – caching disabled", REDIS_URL)
    _client = None


def get_cached(key: str) -> str | None:
    if _client is None:
        return None
    try:
        return _client.get(key)
    except Exception:
        return None


def set_cached(key: str, value: str, ttl: int = DEFAULT_TTL) -> None:
    if _client is None:
        return
    try:
        _client.set(key, value, ex=ttl)
    except Exception:
        pass


def try_lock(key: str, ttl: int) -> bool:
    if _client is None:
        return True
    try:
        return bool(_client.set(key, "1", nx=True, ex=ttl))
    except Exception:
        return True


def kv_set(key: str, value: str, ttl: int = 86400) -> None:
    if _client is None:
        return
    try:
        _client.set(key, value, ex=ttl)
    except Exception:
        pass


def kv_get(key: str) -> str | None:
    if _client is None:
        return None
    try:
        return _client.get(key)
    except Exception:
        return None


def kv_delete(key: str) -> None:
    if _client is None:
        return
    try:
        _client.delete(key)
    except Exception:
        pass


def set_add(key: str, member: str) -> None:
    if _client is None:
        return
    try:
        _client.sadd(key, member)
    except Exception:
        pass


def set_remove(key: str, member: str) -> None:
    if _client is None:
        return
    try:
        _client.srem(key, member)
    except Exception:
        pass


def set_members(key: str) -> list[str]:
    if _client is None:
        return []
    try:
        return list(_client.smembers(key) or [])
    except Exception:
        return []


def set_count(key: str) -> int:
    if _client is None:
        return 0
    try:
        return int(_client.scard(key) or 0)
    except Exception:
        return 0
