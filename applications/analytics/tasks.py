"""
Celery tasks cho analytics
"""
from celery import shared_task
from datetime import datetime, timedelta
from applications.common.logger import get_logger

logger = get_logger("celery.analytics")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def record_click_event(self, link_id: int, short_code: str, ip_address: str,
                       user_agent: str = "", referer: str = ""):
    """
    Task ghi nhận click event vào MongoDB
    Chạy async để không block request chính
    """
    try:
        from applications.analytics.services import ClickEventService, LinkStatsService

        # Ghi click event thô
        event_id = ClickEventService.record_click(
            link_id=link_id,
            short_code=short_code,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
        )

        # Cập nhật realtime stats (hourly)
        now = datetime.utcnow()
        LinkStatsService.update_stats(
            link_id=link_id,
            short_code=short_code,
            date=now,
            hour=now.hour,
            click_count=1
        )

        logger.info(
            "Click event processed",
            extra={
                "extra": {
                    "task_id": self.request.id,
                    "link_id": link_id,
                    "event_id": event_id,
                }
            }
        )

        return {"status": "success", "event_id": event_id}

    except Exception as exc:
        logger.error(
            f"Failed to record click event: {exc}",
            extra={
                "extra": {
                    "task_id": self.request.id,
                    "link_id": link_id,
                    "error": str(exc),
                }
            }
        )
        raise self.retry(exc=exc)


@shared_task(bind=True)
def aggregate_clicks(self, link_id: int = None):
    """
    Task tổng hợp clicks từ raw events
    Chạy định kỳ hoặc theo yêu cầu
    """
    try:
        from applications.analytics.services import ClickEventService, LinkStatsService

        # Lấy các events chưa xử lý
        events = ClickEventService.get_unprocessed_events(limit=1000)

        if not events:
            return {"status": "success", "processed": 0}

        # Group theo link_id và ngày
        stats = {}
        event_ids = []

        for event in events:
            event_ids.append(event["_id"])
            lid = event["link_id"]
            clicked_at = event["clicked_at"]
            date_key = clicked_at.strftime("%Y-%m-%d")

            key = (lid, date_key)
            if key not in stats:
                stats[key] = {
                    "link_id": lid,
                    "short_code": event["short_code"],
                    "date": clicked_at,
                    "count": 0
                }
            stats[key]["count"] += 1

        # Cập nhật daily stats
        for key, data in stats.items():
            LinkStatsService.update_stats(
                link_id=data["link_id"],
                short_code=data["short_code"],
                date=data["date"],
                hour=None,  # Daily stats
                click_count=data["count"]
            )

        # Đánh dấu events đã xử lý
        ClickEventService.mark_events_processed(event_ids)

        logger.info(
            "Clicks aggregated",
            extra={
                "extra": {
                    "task_id": self.request.id,
                    "events_processed": len(event_ids),
                    "links_updated": len(stats),
                }
            }
        )

        return {"status": "success", "processed": len(event_ids)}

    except Exception as exc:
        logger.error(f"Failed to aggregate clicks: {exc}")
        raise


@shared_task(bind=True)
def rollup_daily(self, date_str: str = None):
    """
    Task rollup thống kê theo ngày
    Chạy hàng ngày vào 00:05
    """
    try:
        from applications.analytics.services import LinkStatsService
        from applications.common.mongo_client import get_collection

        if date_str is None:
            # Mặc định rollup ngày hôm qua
            yesterday = datetime.utcnow() - timedelta(days=1)
            date_str = yesterday.strftime("%Y-%m-%d")

        collection = get_collection("link_stats")

        # Aggregate hourly -> daily
        pipeline = [
            {
                "$match": {
                    "type": "hourly",
                    "date": date_str
                }
            },
            {
                "$group": {
                    "_id": "$link_id",
                    "short_code": {"$first": "$short_code"},
                    "total_clicks": {"$sum": "$click_count"}
                }
            }
        ]

        results = list(collection.aggregate(pipeline))

        for result in results:
            LinkStatsService.update_stats(
                link_id=result["_id"],
                short_code=result["short_code"],
                date=datetime.strptime(date_str, "%Y-%m-%d"),
                hour=None,
                click_count=result["total_clicks"]
            )

        logger.info(
            "Daily rollup completed",
            extra={
                "extra": {
                    "task_id": self.request.id,
                    "date": date_str,
                    "links_processed": len(results),
                }
            }
        )

        return {"status": "success", "date": date_str, "links": len(results)}

    except Exception as exc:
        logger.error(f"Failed to rollup daily: {exc}")
        raise


@shared_task(bind=True)
def detect_anomaly(self, link_id: int = None):
    """
    Task phát hiện bất thường
    Chạy định kỳ mỗi giờ
    """
    try:
        from applications.analytics.services import AnomalyService
        from applications.links.models import Link

        anomalies = []

        if link_id:
            # Kiểm tra một link cụ thể
            links = [Link.objects.get(id=link_id)]
        else:
            # Kiểm tra tất cả links active
            links = Link.objects.active()[:100]  # Limit để tránh quá tải

        for link in links:
            if AnomalyService.detect_spike(link.id):
                anomalies.append({
                    "link_id": link.id,
                    "short_code": link.short_code,
                })

        logger.info(
            "Anomaly detection completed",
            extra={
                "extra": {
                    "task_id": self.request.id,
                    "links_checked": len(links),
                    "anomalies_found": len(anomalies),
                }
            }
        )

        return {"status": "success", "anomalies": anomalies}

    except Exception as exc:
        logger.error(f"Failed to detect anomaly: {exc}")
        raise


@shared_task(bind=True)
def compact_click_events(self, days_to_keep: int = 30):
    """
    Task xóa click events cũ đã được aggregate
    Chạy hàng tuần
    """
    try:
        from applications.common.mongo_client import get_collection

        collection = get_collection("click_events")

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        result = collection.delete_many({
            "processed": True,
            "clicked_at": {"$lt": cutoff_date}
        })

        logger.info(
            "Click events compacted",
            extra={
                "extra": {
                    "task_id": self.request.id,
                    "deleted_count": result.deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                }
            }
        )

        return {"status": "success", "deleted": result.deleted_count}

    except Exception as exc:
        logger.error(f"Failed to compact click events: {exc}")
        raise