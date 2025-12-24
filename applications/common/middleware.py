import time
import uuid

from applications.common.logger import get_logger

logger = get_logger("middleware")


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        request_id = str(uuid.uuid4())
        request.request_id = request_id

        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
            }
        )

        response = self.get_response(request)

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Request finished",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )

        return response
