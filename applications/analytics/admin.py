from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View

from applications.links.models import Link
from applications.accounts.models import User
from applications.common.redis_client import RedisClient
from applications.common.mongo_client import MongoDBClient


class AnalyticsAdminSite(admin.AdminSite):
    """Custom Admin Site với dashboard"""
    site_header = 'URL Shorter Administration'
    site_title = 'URL Shorter Admin'
    index_title = 'Dashboard'


# Tạo custom admin views
@method_decorator(staff_member_required, name='dispatch')
class DashboardView(View):
    """Dashboard tổng quan"""

    def get(self, request):
        # Lấy thống kê
        context = {
            'title': 'Dashboard',
            'total_users': User.objects.count(),
            'total_links': Link.objects.filter(deleted_at__isnull=True).count(),
            'active_links': Link.objects.filter(is_active=True, deleted_at__isnull=True).count(),
            'total_clicks': self._get_total_clicks(),
            'top_links': self._get_top_links(),
            'recent_links': Link.objects.filter(deleted_at__isnull=True).order_by('-created_at')[:10],
        }
        return render(request, 'admin/dashboard.html', context)

    def _get_total_clicks(self):
        """Lấy tổng số clicks"""
        try:
            total = sum(link.click_count for link in Link.objects.all())
            return total
        except Exception:
            return 0

    def _get_top_links(self):
        """Lấy top 10 links"""
        return Link.objects.filter(
            deleted_at__isnull=True
        ).order_by('-click_count')[:10]


@method_decorator(staff_member_required, name='dispatch')
class HealthCheckView(View):
    """Health check cho các services"""

    def get(self, request):
        context = {
            'title': 'System Health',
            'services': self._check_services(),
        }
        return render(request, 'admin/health.html', context)

    def _check_services(self):
        """Kiểm tra trạng thái các services"""
        services = []

        # MySQL
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            services.append({'name': 'MySQL', 'status': 'OK', 'color': 'green'})
        except Exception as e:
            services.append({'name': 'MySQL', 'status': f'Error: {e}', 'color': 'red'})

        # Redis
        try:
            if RedisClient.health_check():
                services.append({'name': 'Redis', 'status': 'OK', 'color': 'green'})
            else:
                services.append({'name': 'Redis', 'status': 'Error', 'color': 'red'})
        except Exception as e:
            services.append({'name': 'Redis', 'status': f'Error: {e}', 'color': 'red'})

        # MongoDB
        try:
            if MongoDBClient.health_check():
                services.append({'name': 'MongoDB', 'status': 'OK', 'color': 'green'})
            else:
                services.append({'name': 'MongoDB', 'status': 'Error', 'color': 'red'})
        except Exception as e:
            services.append({'name': 'MongoDB', 'status': f'Error: {e}', 'color': 'red'})

        # RabbitMQ (via Celery)
        try:
            from shorter.celery import app
            inspect = app.control.inspect()
            if inspect.ping():
                services.append({'name': 'RabbitMQ/Celery', 'status': 'OK', 'color': 'green'})
            else:
                services.append({'name': 'RabbitMQ/Celery', 'status': 'No workers', 'color': 'orange'})
        except Exception as e:
            services.append({'name': 'RabbitMQ/Celery', 'status': f'Error: {e}', 'color': 'red'})

        return services


@method_decorator(staff_member_required, name='dispatch')
class JobsView(View):
    """Chạy manual jobs"""

    def get(self, request):
        context = {
            'title': 'Manual Jobs',
            'jobs': [
                {'name': 'aggregate_clicks', 'description': 'Tổng hợp clicks từ raw events'},
                {'name': 'rollup_daily', 'description': 'Rollup thống kê theo ngày'},
                {'name': 'detect_anomaly', 'description': 'Phát hiện bất thường'},
                {'name': 'compact_click_events', 'description': 'Xóa events cũ'},
            ],
            'message': request.GET.get('message', ''),
        }
        return render(request, 'admin/jobs.html', context)

    def post(self, request):
        job_name = request.POST.get('job')
        message = ''

        try:
            if job_name == 'aggregate_clicks':
                from applications.analytics.tasks import aggregate_clicks
                aggregate_clicks.delay()
                message = 'aggregate_clicks task queued'

            elif job_name == 'rollup_daily':
                from applications.analytics.tasks import rollup_daily
                date_str = request.POST.get('date')
                rollup_daily.delay(date_str)
                message = f'rollup_daily task queued for {date_str or "yesterday"}'

            elif job_name == 'detect_anomaly':
                from applications.analytics.tasks import detect_anomaly
                detect_anomaly.delay()
                message = 'detect_anomaly task queued'

            elif job_name == 'compact_click_events':
                from applications.analytics.tasks import compact_click_events
                days = int(request.POST.get('days', 30))
                compact_click_events.delay(days)
                message = f'compact_click_events task queued (keep {days} days)'

            else:
                message = 'Unknown job'

        except Exception as e:
            message = f'Error: {e}'

        from django.shortcuts import redirect
        return redirect(f'/admin/jobs/?message={message}')


# Đăng ký URLs cho admin
def get_admin_urls(admin_site):
    """Thêm custom URLs vào admin"""
    urls = [
        path('dashboard/', DashboardView.as_view(), name='admin_dashboard'),
        path('health/', HealthCheckView.as_view(), name='admin_health'),
        path('jobs/', JobsView.as_view(), name='admin_jobs'),
    ]
    return urls + admin_site.get_urls()