from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import LinkViewSet

router = DefaultRouter()
router.register(r'', LinkViewSet, basename='link')

urlpatterns = [
    path('', include(router.urls)),
]