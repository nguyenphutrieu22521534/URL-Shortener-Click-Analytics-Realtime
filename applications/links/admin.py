from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Link


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    """Custom admin cho Link model"""

    list_display = [
        'short_code', 'short_url_display', 'owner', 'title_display',
        'is_active', 'status_display', 'click_count', 'created_at'
    ]
    list_filter = ['is_active', 'created_at', 'expires_at']
    search_fields = ['short_code', 'original_url', 'title', 'owner__email']
    ordering = ['-created_at']
    readonly_fields = ['short_code', 'click_count', 'created_at', 'updated_at', 'deleted_at']

    fieldsets = (
        ('Link Info', {
            'fields': ('owner', 'original_url', 'short_code', 'title')
        }),
        ('Settings', {
            'fields': ('is_active', 'expires_at')
        }),
        ('Statistics', {
            'fields': ('click_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_links', 'deactivate_links', 'soft_delete_links', 'restore_links']

    def short_url_display(self, obj):
        """Hiển thị short URL có thể click"""
        url = f"/r/{obj.short_code}"
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.short_code)

    short_url_display.short_description = 'Short URL'

    def title_display(self, obj):
        """Hiển thị title rút gọn"""
        if obj.title:
            return obj.title[:30] + '...' if len(obj.title) > 30 else obj.title
        return '-'

    title_display.short_description = 'Title'

    def status_display(self, obj):
        """Hiển thị trạng thái với màu sắc"""
        if obj.is_deleted:
            return format_html('<span style="color: red;">Deleted</span>')
        elif obj.is_expired:
            return format_html('<span style="color: orange;">Expired</span>')
        elif not obj.is_active:
            return format_html('<span style="color: gray;">Inactive</span>')
        else:
            return format_html('<span style="color: green;">Active</span>')

    status_display.short_description = 'Status'

    @admin.action(description='Activate selected links')
    def activate_links(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} links activated.')

    @admin.action(description='Deactivate selected links')
    def deactivate_links(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} links deactivated.')

    @admin.action(description='Soft delete selected links')
    def soft_delete_links(self, request, queryset):
        updated = queryset.update(deleted_at=timezone.now())
        self.message_user(request, f'{updated} links soft deleted.')

    @admin.action(description='Restore selected links')
    def restore_links(self, request, queryset):
        updated = queryset.update(deleted_at=None)
        self.message_user(request, f'{updated} links restored.')