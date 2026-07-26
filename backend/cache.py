import os
import json
import inspect
import logging
from functools import wraps
from datetime import datetime, UTC
from dotenv import load_dotenv
import redis

load_dotenv()

logger = logging.getLogger(__name__)

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL")

redis_client = None

if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        # Test connection
        redis_client.ping()
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.warning(f"Could not connect to Redis: {e}. Caching will be disabled.")
        redis_client = None
else:
    logger.info("REDIS_URL not set. Caching is disabled by default.")


def _build_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Build a stable cache key. Includes the current UTC date so cached
    'today' payloads roll over automatically at UTC midnight instead of
    serving the previous day until the TTL lapses."""
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ("db", "request")}
    key_parts = [func_name, datetime.now(UTC).strftime("%Y-%m-%d")]
    if args:
        key_parts.extend([str(a) for a in args])
    if filtered_kwargs:
        key_parts.append(json.dumps(filtered_kwargs, sort_keys=True))
    return f"chopbet:{':'.join(key_parts)}"


def _cache_get(cache_key: str):
    try:
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Cache hit for key: {cache_key}")
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis get error: {e}")
    return None


def _cache_set(cache_key: str, value, expire: int):
    try:
        redis_client.setex(cache_key, expire, json.dumps(value))
        logger.info(f"Cache miss. Stored result in: {cache_key}")
    except Exception as e:
        logger.warning(f"Redis set error: {e}")


def cache_response(expire: int = 3600):
    """
    Decorator to cache FastAPI route responses in Redis (default 1 hour).

    Preserves the wrapped function's sync/async nature: a sync route keeps a
    sync wrapper so FastAPI runs it in its threadpool (never blocking the event
    loop with DB/Redis I/O), and an async route keeps an async wrapper.
    """
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not redis_client:
                    return await func(*args, **kwargs)
                cache_key = _build_cache_key(func.__name__, args, kwargs)
                cached = _cache_get(cache_key)
                if cached is not None:
                    return cached
                result = await func(*args, **kwargs)
                _cache_set(cache_key, result, expire)
                return result
            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not redis_client:
                return func(*args, **kwargs)
            cache_key = _build_cache_key(func.__name__, args, kwargs)
            cached = _cache_get(cache_key)
            if cached is not None:
                return cached
            result = func(*args, **kwargs)
            _cache_set(cache_key, result, expire)
            return result
        return sync_wrapper
    return decorator


def invalidate_cache(pattern: str = "chopbet:*"):
    """
    Invalidate all keys matching the pattern. Uses SCAN (non-blocking) rather
    than KEYS so it never stalls a shared/managed Redis server.
    """
    if not redis_client:
        return

    try:
        deleted = 0
        batch = []
        for key in redis_client.scan_iter(match=pattern, count=500):
            batch.append(key)
            if len(batch) >= 500:
                deleted += redis_client.delete(*batch)
                batch = []
        if batch:
            deleted += redis_client.delete(*batch)
        if deleted:
            logger.info(f"Invalidated {deleted} cache keys matching {pattern}")
    except Exception as e:
        logger.warning(f"Redis invalidation error: {e}")
