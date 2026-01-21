from django.db.models import Sum, Count, Q
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Link
from .serializers import LinkSerializer, LinkCreateSerializer, LinkUpdateSerializer
from .filters import LinkFilter
from applications.common.rate_limit import check_rate_limit, RateLimitExceeded
from applications.common.exceptions import RateLimitException


class LinkViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho CRUD links

    list: Lấy danh sách links của user
    create: Tạo link mới
    retrieve: Xem chi tiết link
    update: Cập nhật link
    destroy: Soft delete link
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = LinkFilter
    search_fields = ['title', 'original_url', 'short_code']
    ordering_fields = ['created_at', 'click_count', 'expires_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Chỉ lấy links của user hiện tại (không bao gồm deleted)"""
        return Link.objects.by_owner(self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return LinkCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return LinkUpdateSerializer
        return LinkSerializer

    def create(self, request, *args, **kwargs):
        """Tạo link mới với rate limiting"""
        # Rate limit: 10 links per minute per user
        try:
            check_rate_limit(
                key=f"create_link:{request.user.id}",
                limit=10,
                window_seconds=60
            )
        except RateLimitExceeded as e:
            raise RateLimitException(
                detail=str(e),
                retry_after=e.retry_after
            )

        return super().create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        """Soft delete thay vì hard delete"""
        instance.soft_delete()

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Khôi phục link đã soft delete"""
        # Lấy cả links đã deleted
        link = Link.objects.filter(owner=request.user, pk=pk).first()

        if not link:
            return Response(
                {"detail": "Link not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not link.is_deleted:
            return Response(
                {"detail": "Link is not deleted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        link.restore()
        return Response(LinkSerializer(link, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Bật/tắt trạng thái active của link"""
        link = self.get_object()
        link.is_active = not link.is_active
        link.save(update_fields=['is_active', 'updated_at'])
        return Response(LinkSerializer(link, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def deleted(self, request):
        """Lấy danh sách links đã soft delete"""
        queryset = Link.objects.filter(owner=request.user).deleted()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = LinkSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = LinkSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Thống kê tổng quan links của user"""
        user_links = Link.objects.filter(owner=request.user, deleted_at__isnull=True)

        data = user_links.aggregate(
            total_links=Count('id'),
            active_links=Count('id', filter=Q(is_active=True)),
            inactive_links=Count('id', filter=Q(is_active=False)),
            total_clicks=Sum('click_count', default=0)
        )

        return Response(data)
