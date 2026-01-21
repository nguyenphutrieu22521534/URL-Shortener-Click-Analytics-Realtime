"""
Health Check Endpoints
- /health/ : Liveness check (app đang chạy)
- /readyz/ : Readiness check (app sẵn sàng nhận request)
"""
from django.http import JsonResponse
from django.views import View

from applications.common.redis_client import RedisClient
from applications.common.mongo_client import MongoDBClient
from applications.common.logger import get_logger

logger = get_logger("health")


class HealthCheckView(View):
    """
    Liveness check - Kiểm tra app có đang chạy không
    Dùng cho Kubernetes liveness probe
    """

    def get(self, request):
        return JsonResponse({
            "status": "ok",
            "service": "url-shorter"
        })


class ReadinessCheckView(View):
    """
    Readiness check - Kiểm tra app sẵn sàng nhận request
    Dùng cho Kubernetes readiness probe
    """

    def get(self, request):
        checks = {}
        all_ok = True

        # Check MySQL
        mysql_ok, mysql_msg = self._check_mysql()
        checks["mysql"] = {"status": "ok" if mysql_ok else "error", "message": mysql_msg}
        if not mysql_ok:
            all_ok = False

        # Check Redis
        redis_ok, redis_msg = self._check_redis()
        checks["redis"] = {"status": "ok" if redis_ok else "error", "message": redis_msg}
        if not redis_ok:
            all_ok = False

        # Check MongoDB
        mongo_ok, mongo_msg = self._check_mongo()
        checks["mongodb"] = {"status": "ok" if mongo_ok else "error", "message": mongo_msg}
        if not mongo_ok:
            all_ok = False

        # Check RabbitMQ/Celery
        celery_ok, celery_msg = self._check_celery()
        checks["celery"] = {"status": "ok" if celery_ok else "error", "message": celery_msg}
        # Celery không bắt buộc phải chạy

        status_code = 200 if all_ok else 503

        return JsonResponse({
            "status": "ready" if all_ok else "not_ready",
            "checks": checks
        }, status=status_code)

    def _check_mysql(self):
        """Kiểm tra kết nối MySQL"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True, "Connected"
        except Exception as e:
            logger.error(f"MySQL health check failed: {e}")
            return False, str(e)

    def _check_redis(self):
        """Kiểm tra kết nối Redis"""
        try:
            if RedisClient.health_check():
                return True, "Connected"
            return False, "Ping failed"
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False, str(e)

    def _check_mongo(self):
        """Kiểm tra kết nối MongoDB"""
        try:
            if MongoDBClient.health_check():
                return True, "Connected"
            return False, "Ping failed"
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False, str(e)

    def _check_celery(self):
        """Kiểm tra Celery workers"""
        try:
            from shorter.celery import app
            inspect = app.control.inspect()
            stats = inspect.ping()
            if stats:
                worker_count = len(stats)
                return True, f"{worker_count} worker(s) online"
            return False, "No workers available"
        except Exception as e:
            logger.error(f"Celery health check failed: {e}")
            return False, str(e)