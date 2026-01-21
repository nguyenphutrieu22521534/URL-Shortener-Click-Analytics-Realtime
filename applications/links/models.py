import string
import random
from django.db import models
from django.utils import timezone
from applications.accounts.models import User


def generate_short_code(length=7):
    """Tạo short code ngẫu nhiên"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))




class LinkQuerySet(models.QuerySet):
    """Custom QuerySet với các query thường dùng"""

    def active(self):
        """Lấy các link đang hoạt động"""
        return self.filter(
            is_active=True,
            deleted_at__isnull=True
        ).exclude(
            expires_at__lt=timezone.now()
        )

    def by_owner(self, user):
        """Lấy links của một user (không bao gồm deleted)"""
        return self.filter(
            owner=user,
            deleted_at__isnull=True
        )

    def expired(self):
        """Lấy các link đã hết hạn"""
        return self.filter(
            expires_at__lt=timezone.now(),
            deleted_at__isnull=True
        )

    def deleted(self):
        """Lấy các link đã soft delete"""
        return self.filter(deleted_at__isnull=False)


class Link(models.Model):
    """Model lưu trữ short links"""

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='links',
        verbose_name='Owner'
    )
    original_url = models.URLField(
        max_length=2048,
        verbose_name='Original URL'
    )
    short_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name='Short Code'
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Title'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='Active'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Expires At'
    )
    click_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Click Count'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Deleted At'
    )

    objects = LinkQuerySet.as_manager()

    class Meta:
        db_table = 'links'
        verbose_name = 'Link'
        verbose_name_plural = 'Links'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['owner', 'deleted_at']),
        ]

    def __str__(self):
        return f"{self.short_code} -> {self.original_url[:50]}"

    def save(self, *args, **kwargs):
        """Tự động tạo short_code nếu chưa có"""
        if not self.short_code:
            self.short_code = self._generate_unique_code()
        super().save(*args, **kwargs)

    def _generate_unique_code(self):
        """Tạo short code unique"""
        for _ in range(10):  # Thử tối đa 10 lần
            code = generate_short_code()
            if not Link.objects.filter(short_code=code).exists():
                return code
        raise ValueError("Could not generate unique short code")

    @property
    def is_expired(self):
        """Kiểm tra link đã hết hạn chưa"""
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_deleted(self):
        """Kiểm tra link đã bị soft delete chưa"""
        return self.deleted_at is not None

    @property
    def is_accessible(self):
        """Kiểm tra link có thể truy cập được không"""
        return self.is_active and not self.is_expired and not self.is_deleted

    def soft_delete(self):
        """Soft delete link"""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at', 'updated_at'])

    def restore(self):
        """Khôi phục link đã soft delete"""
        self.deleted_at = None
        self.save(update_fields=['deleted_at', 'updated_at'])

    def increment_click(self):
        """Tăng click count (dùng cho fallback, chính sẽ dùng Redis)"""
        self.click_count = models.F('click_count') + 1
        self.save(update_fields=['click_count'])
