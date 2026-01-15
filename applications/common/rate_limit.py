from applications.common.redis_client import get_redis
from applications.common.logger import get_logger

logger = get_logger("rate_limit")


class RateLimitExceeded(Exception):
    """Exception khi vượt quá rate limit"""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


def check_rate_limit(key: str, limit: int, window_seconds: int) -> int:
    """
    Kiểm tra rate limit cho một key.

    Args:
        key: Unique identifier (e.g., user_id, ip_address)
        limit: Số request tối đa cho phép
        window_seconds: Khoảng thời gian tính bằng giây

    Returns:
        Số request hiện tại

    Raises:
        RateLimitExceeded: Khi vượt quá limit
    """
    redis = get_redis()
    redis_key = f"rate_limit:{key}"

    current = redis.incr(redis_key)

    if current == 1:
        redis.expire(redis_key, window_seconds)

    if current > limit:
        ttl = redis.ttl(redis_key)
        logger.warning(
            "Rate limit exceeded",
            extra={
                "extra": {
                    "key": key,
                    "limit": limit,
                    "window": window_seconds,
                    "current": current,
                    "retry_after": ttl,
                }
            }
        )
        raise RateLimitExceeded(
            f"Rate limit exceeded. Retry after {ttl} seconds",
            retry_after=ttl
        )

    return current


# Alias cho backward compatibility
def rate_limit(key: str, limit: int, window_seconds: int) -> int:
    """Alias cho check_rate_limit"""
    return check_rate_limit(key, limit, window_seconds)