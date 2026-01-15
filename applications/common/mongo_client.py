from pymongo import MongoClient
from applications.common.config import get_config
from applications.common.logger import get_logger

logger = get_logger("mongo")


class MongoDBClient:
    _client = None
    _db = None

    @classmethod
    def get_client(cls):
        """Lấy MongoDB client instance"""
        if cls._client is None:
            cfg = get_config("mongo")
            uri = cfg.get("uri", "mongodb://localhost:27017")
            cls._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            logger.info(
                "MongoDB client initialized",
                extra={"extra": {"uri": uri}}
            )
        return cls._client

    @classmethod
    def get_database(cls):
        """Lấy database instance"""
        if cls._db is None:
            cfg = get_config("mongo")
            db_name = cfg.get("db", "analytics")
            cls._db = cls.get_client()[db_name]
            logger.info(
                "MongoDB database selected",
                extra={"extra": {"db": db_name}}
            )
        return cls._db

    @classmethod
    def health_check(cls):
        """Kiểm tra kết nối MongoDB"""
        try:
            client = cls.get_client()
            client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False


def get_mongo_db():
    """Lấy database instance"""
    return MongoDBClient.get_database()


def get_collection(name: str):
    """Lấy collection theo tên"""
    return get_mongo_db()[name]