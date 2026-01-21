"""
URL configuration for shorter project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from applications.links.redirect import RedirectView
from applications.analytics.admin import DashboardView, HealthCheckView, JobsView
from applications.common.health import HealthCheckView as HealthView, ReadinessCheckView

urlpatterns = [
    # Health check endpoints
    path('health/', HealthView.as_view(), name='health'),
    path('readyz/', ReadinessCheckView.as_view(), name='readiness'),

    # Custom admin views (phải đặt trước admin/)
    path('admin/dashboard/', DashboardView.as_view(), name='admin_dashboard'),
    path('admin/health/', HealthCheckView.as_view(), name='admin_health'),
    path('admin/jobs/', JobsView.as_view(), name='admin_jobs'),

    path('admin/', admin.site.urls),

    # API endpoints
    path('api/auth/', include('applications.accounts.urls')),
    path('api/links/', include('applications.links.urls')),

    # Redirect endpoint
    path('r/<str:code>', RedirectView.as_view(), name='redirect'),
]
