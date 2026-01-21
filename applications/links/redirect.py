"""
Redirect view cho short links
Xử lý: Redis cache -> MySQL fallback -> Record click event
"""
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponseGone
from django.views import View

from .models import Link
from applications.common.redis_client import get_redis
from applications.common.logger import get_logger

logger = get_logger("redirect")

# Cache TTL: 1 hour
CACHE_TTL = 3600


class RedirectView(View):
    """
    View xử lý redirect từ short code đến original URL

    Flow:
    1. Check Redis cache
    2. If cache miss -> Query MySQL -> Update cache
    3. Check link accessibility (active, not expired, not deleted)
    4. Record click event (async via Celery)
    5. Return 301 redirect
    """

    def get(self, request, code):
        # Lấy thông tin từ cache hoặc database
        link_data = self._get_link_data(code)

        if link_data is None:
            logger.info(
                "Link not found",
                extra={"extra": {"short_code": code}}
            )
            return HttpResponseNotFound("Link not found")

        # Check if link is accessible
        if not link_data['is_accessible']:
            reason = link_data.get('reason', 'Link is not available')
            logger.info(
                "Link not accessible",
                extra={"extra": {"short_code": code, "reason": reason}}
            )
            return HttpResponseGone(reason)

        # Record click event (async)
        self._record_click(
            link_id=link_data['id'],
            short_code=code,
            request=request
        )

        # Redirect 301
        return HttpResponseRedirect(link_data['original_url'], status=301)

    def _get_link_data(self, code: str) -> dict | None:
        """
        Lấy link data từ cache hoặc database
        """
        redis = get_redis()
        cache_key = f"link:{code}"

        # Try cache first
        cached = redis.hgetall(cache_key)

        if cached:
            logger.debug(
                "Cache hit",
                extra={"extra": {"short_code": code}}
            )
            # Refresh TTL on hit
            redis.expire(cache_key, CACHE_TTL)

            return {
                'id': int(cached['id']),
                'original_url': cached['original_url'],
                'is_accessible': cached['is_accessible'] == 'True',
                'reason': cached.get('reason', ''),
            }

        # Cache miss -> Query database
        logger.debug(
            "Cache miss",
            extra={"extra": {"short_code": code}}
        )

        try:
            link = Link.objects.select_related('owner').get(short_code=code)
        except Link.DoesNotExist:
            return None

        # Determine accessibility
        is_accessible = link.is_accessible
        reason = ''

        if not is_accessible:
            if link.is_deleted:
                reason = 'Link has been deleted'
            elif not link.is_active:
                reason = 'Link is disabled'
            elif link.is_expired:
                reason = 'Link has expired'

        link_data = {
            'id': link.id,
            'original_url': link.original_url,
            'is_accessible': is_accessible,
            'reason': reason,
        }

        # Update cache
        self._update_cache(cache_key, link_data)

        return link_data

    def _update_cache(self, cache_key: str, link_data: dict):
        """Cập nhật cache"""
        redis = get_redis()

        redis.hset(cache_key, mapping={
            'id': str(link_data['id']),
            'original_url': link_data['original_url'],
            'is_accessible': str(link_data['is_accessible']),
            'reason': link_data.get('reason', ''),
        })
        redis.expire(cache_key, CACHE_TTL)

    def _record_click(self, link_id: int, short_code: str, request):
        """Ghi nhận click event (async)"""
        # Lấy thông tin request
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get('User-Agent', '')
        referer = request.headers.get('Referer', '')

        # Gửi task async
        try:
            from applications.analytics.tasks import record_click_event
            record_click_event.delay(
                link_id=link_id,
                short_code=short_code,
                ip_address=ip_address,
                user_agent=user_agent,
                referer=referer,
            )
        except Exception as e:
            # Nếu Celery không hoạt động, ghi trực tiếp
            logger.warning(
                f"Celery not available, recording click directly: {e}",
                extra={"extra": {"short_code": short_code}}
            )
            self._record_click_sync(link_id, short_code, ip_address, user_agent, referer)

    def _record_click_sync(self, link_id, short_code, ip_address, user_agent, referer):
        """Ghi click đồng bộ (fallback)"""
        try:
            from applications.analytics.services import ClickEventService
            ClickEventService.record_click(
                link_id=link_id,
                short_code=short_code,
                ip_address=ip_address,
                user_agent=user_agent,
                referer=referer,
            )

            # Tăng click count trong MySQL
            Link.objects.filter(id=link_id).update(
                click_count=models.F('click_count') + 1
            )
        except Exception as e:
            logger.error(f"Failed to record click: {e}")

    def _get_client_ip(self, request) -> str:
        """Lấy IP của client"""
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


def invalidate_link_cache(short_code: str):
    """
    Xóa cache của link (gọi khi link được cập nhật)
    """
    redis = get_redis()
    cache_key = f"link:{short_code}"
    redis.delete(cache_key)
    logger.info(
        "Link cache invalidated",
        extra={"extra": {"short_code": short_code}}
    )