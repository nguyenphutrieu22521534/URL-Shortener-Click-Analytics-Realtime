import redis
from applications.common.config import get_config
from applications.common.logger import get_logger

logger = get_logger("redis")


class RedisClient:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cfg = get_config("redis")
            cls._client = redis.Redis(
                host=cfg.get("host", "localhost"),
                port=cfg.get("port", 6379),
                db=cfg.get("db", 0),
                decode_responses=True,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            logger.info(
                "Redis client initialized",
                extra={
                    "extra": {
                        "host": cfg.get("host"),
                        "port": cfg.get("port")
                    }
                }
            )
        return cls._client

    @classmethod
    def health_check(cls):
        """Kiểm tra kết nối Redis"""
        try:
            client = cls.get_client()
            client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


def get_redis():
    """Lấy Redis client instance"""
    return RedisClient.get_client()


# Backward compatibility
redis_client = None


def get_redis_client():
    global redis_client
    if redis_client is None:
        redis_client = get_redis()
    return redis_client