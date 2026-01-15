"""
Analytics Services - Xử lý dữ liệu click events với MongoDB
"""
from datetime import datetime, timedelta
from typing import Optional
from applications.common.mongo_client import get_collection
from applications.common.logger import get_logger

logger = get_logger("analytics")

# Collection names
CLICK_EVENTS_COLLECTION = "click_events"
LINK_STATS_COLLECTION = "link_stats"


class ClickEventService:
    """Service xử lý click events"""

    @staticmethod
    def record_click(
            link_id: int,
            short_code: str,
            ip_address: str,
            user_agent: str = "",
            referer: str = "",
            country: str = "",
            city: str = "",
    ) -> str:
        """
        Ghi nhận một click event vào MongoDB

        Returns:
            inserted_id
        """
        collection = get_collection(CLICK_EVENTS_COLLECTION)

        event = {
            "link_id": link_id,
            "short_code": short_code,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "referer": referer,
            "country": country,
            "city": city,
            "clicked_at": datetime.utcnow(),
            "processed": False,  # Đánh dấu chưa được aggregate
        }

        result = collection.insert_one(event)

        logger.info(
            "Click event recorded",
            extra={
                "extra": {
                    "link_id": link_id,
                    "short_code": short_code,
                    "event_id": str(result.inserted_id),
                }
            }
        )

        return str(result.inserted_id)

    @staticmethod
    def get_clicks_by_link(link_id: int, limit: int = 100) -> list:
        """Lấy danh sách click events của một link"""
        collection = get_collection(CLICK_EVENTS_COLLECTION)

        cursor = collection.find(
            {"link_id": link_id}
        ).sort("clicked_at", -1).limit(limit)

        return list(cursor)

    @staticmethod
    def get_unprocessed_events(limit: int = 1000) -> list:
        """Lấy các events chưa được xử lý"""
        collection = get_collection(CLICK_EVENTS_COLLECTION)

        cursor = collection.find(
            {"processed": False}
        ).sort("clicked_at", 1).limit(limit)

        return list(cursor)

    @staticmethod
    def mark_events_processed(event_ids: list) -> int:
        """Đánh dấu các events đã xử lý"""
        collection = get_collection(CLICK_EVENTS_COLLECTION)

        result = collection.update_many(
            {"_id": {"$in": event_ids}},
            {"$set": {"processed": True}}
        )

        return result.modified_count

    @staticmethod
    def count_clicks_in_range(
            link_id: int,
            start_time: datetime,
            end_time: datetime
    ) -> int:
        """Đếm số clicks trong khoảng thời gian"""
        collection = get_collection(CLICK_EVENTS_COLLECTION)

        return collection.count_documents({
            "link_id": link_id,
            "clicked_at": {
                "$gte": start_time,
                "$lt": end_time
            }
        })


class LinkStatsService:
    """Service xử lý thống kê link"""

    @staticmethod
    def update_stats(
            link_id: int,
            short_code: str,
            date: datetime,
            hour: Optional[int] = None,
            click_count: int = 1
    ):
        """
        Cập nhật thống kê cho link

        Args:
            link_id: ID của link
            short_code: Mã rút gọn
            date: Ngày thống kê
            hour: Giờ (0-23), None nếu là daily stats
            click_count: Số click cần cộng thêm
        """
        collection = get_collection(LINK_STATS_COLLECTION)

        # Tạo filter key
        filter_key = {
            "link_id": link_id,
            "date": date.strftime("%Y-%m-%d"),
            "type": "hourly" if hour is not None else "daily",
        }

        if hour is not None:
            filter_key["hour"] = hour

        # Upsert stats
        result = collection.update_one(
            filter_key,
            {
                "$inc": {"click_count": click_count},
                "$set": {
                    "short_code": short_code,
                    "updated_at": datetime.utcnow(),
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow(),
                }
            },
            upsert=True
        )

        return result

    @staticmethod
    def get_daily_stats(link_id: int, days: int = 30) -> list:
        """Lấy thống kê daily của link trong N ngày gần nhất"""
        collection = get_collection(LINK_STATS_COLLECTION)

        start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        cursor = collection.find({
            "link_id": link_id,
            "type": "daily",
            "date": {"$gte": start_date}
        }).sort("date", -1)

        return list(cursor)

    @staticmethod
    def get_hourly_stats(link_id: int, date: str) -> list:
        """Lấy thống kê hourly của link trong một ngày"""
        collection = get_collection(LINK_STATS_COLLECTION)

        cursor = collection.find({
            "link_id": link_id,
            "type": "hourly",
            "date": date
        }).sort("hour", 1)

        return list(cursor)

    @staticmethod
    def get_top_links(limit: int = 10, days: int = 1) -> list:
        """Lấy top links có nhiều click nhất"""
        collection = get_collection(LINK_STATS_COLLECTION)

        start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        pipeline = [
            {
                "$match": {
                    "type": "daily",
                    "date": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": "$link_id",
                    "short_code": {"$first": "$short_code"},
                    "total_clicks": {"$sum": "$click_count"}
                }
            },
            {"$sort": {"total_clicks": -1}},
            {"$limit": limit}
        ]

        return list(collection.aggregate(pipeline))

    @staticmethod
    def get_total_clicks_today() -> int:
        """Lấy tổng số clicks hôm nay"""
        collection = get_collection(LINK_STATS_COLLECTION)

        today = datetime.utcnow().strftime("%Y-%m-%d")

        pipeline = [
            {
                "$match": {
                    "type": "daily",
                    "date": today
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": "$click_count"}
                }
            }
        ]

        result = list(collection.aggregate(pipeline))
        return result[0]["total"] if result else 0

    @staticmethod
    def get_hourly_heatmap(days: int = 7) -> list:
        """Lấy dữ liệu heatmap theo giờ"""
        collection = get_collection(LINK_STATS_COLLECTION)

        start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        pipeline = [
            {
                "$match": {
                    "type": "hourly",
                    "date": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": "$hour",
                    "total_clicks": {"$sum": "$click_count"}
                }
            },
            {"$sort": {"_id": 1}}
        ]

        return list(collection.aggregate(pipeline))


class AnomalyService:
    """Service phát hiện bất thường"""

    @staticmethod
    def detect_spike(link_id: int, threshold_multiplier: float = 3.0) -> bool:
        """
        Phát hiện spike bất thường cho một link
        So sánh clicks giờ hiện tại với trung bình 7 ngày trước
        """
        collection = get_collection(LINK_STATS_COLLECTION)

        now = datetime.utcnow()
        current_hour = now.hour
        current_date = now.strftime("%Y-%m-%d")

        # Lấy clicks giờ hiện tại
        current_stats = collection.find_one({
            "link_id": link_id,
            "type": "hourly",
            "date": current_date,
            "hour": current_hour
        })

        current_clicks = current_stats["click_count"] if current_stats else 0

        # Tính trung bình 7 ngày trước cùng giờ
        start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")

        pipeline = [
            {
                "$match": {
                    "link_id": link_id,
                    "type": "hourly",
                    "hour": current_hour,
                    "date": {
                        "$gte": start_date,
                        "$lt": current_date
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_clicks": {"$avg": "$click_count"}
                }
            }
        ]

        result = list(collection.aggregate(pipeline))
        avg_clicks = result[0]["avg_clicks"] if result else 0

        # Phát hiện spike
        if avg_clicks > 0 and current_clicks > avg_clicks * threshold_multiplier:
            logger.warning(
                "Anomaly detected: click spike",
                extra={
                    "extra": {
                        "link_id": link_id,
                        "current_clicks": current_clicks,
                        "avg_clicks": avg_clicks,
                        "threshold": avg_clicks * threshold_multiplier,
                    }
                }
            )
            return True

        return False

    @staticmethod
    def get_anomalies(hours: int = 24) -> list:
        """Lấy danh sách các link có anomaly trong N giờ gần nhất"""
        # TODO: Implement lưu anomaly vào collection riêng
        # Tạm thời return empty
        return []