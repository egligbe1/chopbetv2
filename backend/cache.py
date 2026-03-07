import os
import json
import logging
import redis
from functools import wraps
from typing import Optional, Any
from dotenv import load_dotenv

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

def cache_response(expire: int = 3600):
    """
    Decorator to cache FastAPI route responses in Redis.
    Default expiry is 1 hour (3600 seconds).
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import inspect
            if not redis_client:
                if inspect.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

            # Create a unique cache key based on function name and arguments
            # Filter out 'db' session and 'request' from key calculation
            filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ("db", "request")}
            key_parts = [func.__name__]
            if args:
                key_parts.extend([str(a) for a in args])
            if filtered_kwargs:
                key_parts.append(json.dumps(filtered_kwargs, sort_keys=True))
            
            cache_key = f"chopbet:{':'.join(key_parts)}"

            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    logger.info(f"Cache hit for key: {cache_key}")
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

            # Call the original function
            # Check if it's a coroutine or regular function
            import inspect
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            try:
                redis_client.setex(cache_key, expire, json.dumps(result))
                logger.info(f"Cache miss. Stored result in: {cache_key}")
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

            return result
        return wrapper
    return decorator


def invalidate_cache(pattern: str = "chopbet:*"):
    """
    Invalidates all keys matching the pattern.
    Useful after new predictions are generated.
    """
    if not redis_client:
        return
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys matching {pattern}")
    except Exception as e:
        logger.warning(f"Redis invalidation error: {e}")
