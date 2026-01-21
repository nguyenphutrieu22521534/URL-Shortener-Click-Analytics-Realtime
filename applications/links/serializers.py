from rest_framework import serializers
from .models import Link


class LinkSerializer(serializers.ModelSerializer):
    """Serializer cho Link model"""
    is_expired = serializers.ReadOnlyField()
    is_accessible = serializers.ReadOnlyField()
    short_url = serializers.SerializerMethodField()

    class Meta:
        model = Link
        fields = [
            'id', 'original_url', 'short_code', 'short_url', 'title',
            'is_active', 'expires_at', 'click_count',
            'is_expired', 'is_accessible',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'short_code', 'click_count', 'created_at', 'updated_at']

    def get_short_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/r/{obj.short_code}')
        return f'/r/{obj.short_code}'


class LinkCreateSerializer(serializers.ModelSerializer):
    """Serializer cho tạo link mới"""
    short_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Link
        fields = ['original_url', 'short_code', 'title', 'expires_at', 'is_active']
        extra_kwargs = {
            'title': {'required': False},
            'expires_at': {'required': False},
            'is_active': {'required': False},
        }

    def validate_short_code(self, value):
        if value:
            if len(value) < 4:
                raise serializers.ValidationError("Short code must be at least 4 characters.")
            if Link.objects.filter(short_code=value).exists():
                raise serializers.ValidationError("This short code is already taken.")
        return value

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class LinkUpdateSerializer(serializers.ModelSerializer):
    """Serializer cho cập nhật link"""

    class Meta:
        model = Link
        fields = ['original_url', 'title', 'is_active', 'expires_at']
        extra_kwargs = {
            'original_url': {'required': False},
            'title': {'required': False},
            'is_active': {'required': False},
            'expires_at': {'required': False},
        }