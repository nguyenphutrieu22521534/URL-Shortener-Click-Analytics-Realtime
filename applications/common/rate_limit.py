from applications.common.redis_client import redis_client
from applications.common.logger import get_logger

logger = get_logger("rate_limit")


class RateLimitExceeded(Exception):
    pass


def rate_limit(key: str, limit: int, window_seconds: int):
    redis_key = f"rate_limit:{key}"

    current = redis_client.incr(redis_key)

    if current == 1:
        redis_client.expire(redis_key, window_seconds)

    if current > limit:
        logger.warning(
            "Rate limit exceeded",
            extra={
                "key": key,
                "limit": limit,
                "window": window_seconds,
                "current": current,
            }
        )
        raise RateLimitExceeded(f"Rate limit exceeded for {key}")

    return current
