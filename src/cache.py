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
