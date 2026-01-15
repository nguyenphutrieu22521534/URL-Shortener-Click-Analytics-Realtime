import time
import uuid

from applications.common.logger import get_logger

logger = get_logger("middleware")


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip logging cho static files và health check
        skip_paths = ['/static/', '/favicon.ico', '/health/', '/readyz/']
        if any(request.path.startswith(path) for path in skip_paths):
            return self.get_response(request)

        start_time = time.time()

        # Lấy request_id từ header hoặc tạo mới
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        request.request_id = request_id

        logger.info(
            "Request started",
            extra={
                "extra": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.path,
                    "user_agent": request.headers.get('User-Agent', ''),
                    "ip": self._get_client_ip(request),
                }
            }
        )

        response = self.get_response(request)

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Request finished",
            extra={
                "extra": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            }
        )

        # Thêm request_id vào response header
        response['X-Request-ID'] = request_id
        return response

    def _get_client_ip(self, request):
        """Lấy IP thực của client (hỗ trợ proxy)"""
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')