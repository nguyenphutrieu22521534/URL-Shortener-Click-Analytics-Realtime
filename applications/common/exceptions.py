from rest_framework.exceptions import APIException
from rest_framework import status


class BadRequestException(APIException):
    """400 Bad Request"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Bad request'
    default_code = 'bad_request'


class UnauthorizedException(APIException):
    """401 Unauthorized"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Authentication required'
    default_code = 'unauthorized'


class ForbiddenException(APIException):
    """403 Forbidden"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Permission denied'
    default_code = 'forbidden'


class NotFoundException(APIException):
    """404 Not Found"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Resource not found'
    default_code = 'not_found'


class ConflictException(APIException):
    """409 Conflict"""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Resource already exists'
    default_code = 'conflict'


class RateLimitException(APIException):
    """429 Too Many Requests"""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = 'Too many requests'
    default_code = 'rate_limit_exceeded'

    def __init__(self, detail=None, retry_after=None):
        super().__init__(detail)
        self.retry_after = retry_after


class ServiceUnavailableException(APIException):
    """503 Service Unavailable"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service temporarily unavailable'
    default_code = 'service_unavailable'