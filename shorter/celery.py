"""
Celery configuration for shorter project.
"""
import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shorter.settings')

# Create Celery app
app = Celery('shorter')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Define queues for different task types
app.conf.task_queues = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'analytics': {
        'exchange': 'analytics',
        'routing_key': 'analytics',
    },
    'aggregation': {
        'exchange': 'aggregation',
        'routing_key': 'aggregation',
    },
}

# Default queue
app.conf.task_default_queue = 'default'

# Task routing
app.conf.task_routes = {
    'applications.analytics.tasks.record_click_event': {'queue': 'analytics'},
    'applications.analytics.tasks.aggregate_clicks': {'queue': 'aggregation'},
    'applications.analytics.tasks.rollup_daily': {'queue': 'aggregation'},
    'applications.analytics.tasks.detect_anomaly': {'queue': 'analytics'},
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task để test Celery"""
    print(f'Request: {self.request!r}')