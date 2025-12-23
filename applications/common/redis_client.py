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
                host=cfg["host"],
                port=cfg["port"],
                db=cfg.get("db", 0),
                decode_responses=True,
                socket_connect_timeout=2,
            )
            logger.info("Redis client initialized")
        return cls._client


redis_client = RedisClient.get_client()
