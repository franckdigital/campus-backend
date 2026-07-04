from rest_framework import serializers
from .models import Site, AcademicYear, AuditLog, SystemConfig, WorkspaceSettings


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = [
            'id', 'name', 'code', 'address', 'city', 'country',
            'phone', 'email', 'logo', 'is_main', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SiteListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ['id', 'name', 'code', 'city', 'is_main', 'is_active']


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = [
            'id', 'name', 'code', 'start_date', 'end_date',
            'is_current', 'registration_open', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_email', 'site', 'site_name',
            'action', 'model_name', 'object_id', 'object_repr',
            'changes', 'ip_address', 'timestamp', 'extra_data'
        ]
        read_only_fields = fields


class SystemConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = [
            'id', 'key', 'value', 'description', 'is_public',
            'site', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SystemConfigPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = ['key', 'value']


class WorkspaceSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceSettings
        fields = [
            'id', 'app_name', 'app_subtitle', 'logo', 'primary_color',
            'font_size', 'compact_mode', 'language', 'date_format',
            'items_per_page', 'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']
