from django.contrib import admin
from .models import Site, AcademicYear, AuditLog, SystemConfig


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'city', 'is_main', 'is_active', 'created_at']
    list_filter = ['is_main', 'is_active', 'city']
    search_fields = ['name', 'code', 'city']
    ordering = ['-is_main', 'name']


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'start_date', 'end_date', 'is_current', 'registration_open', 'is_active']
    list_filter = ['is_current', 'registration_open', 'is_active']
    search_fields = ['name', 'code']
    ordering = ['-start_date']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'model_name', 'object_repr', 'timestamp']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['object_repr', 'model_name', 'user__email']
    readonly_fields = [
        'id', 'user', 'site', 'action', 'model_name', 'object_id',
        'object_repr', 'changes', 'ip_address', 'user_agent', 'timestamp', 'extra_data'
    ]
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ['key', 'site', 'is_public', 'is_active', 'updated_at']
    list_filter = ['is_public', 'is_active', 'site']
    search_fields = ['key', 'description']
    ordering = ['key']
