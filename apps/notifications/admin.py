from django.contrib import admin
from .models import Notification, NotificationLog, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'priority', 'is_read', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read', 'site']
    search_fields = ['title', 'message', 'recipient__email']
    ordering = ['-created_at']


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['notification', 'channel', 'status', 'sent_at', 'delivered_at']
    list_filter = ['channel', 'status']
    search_fields = ['notification__title']
    ordering = ['-created_at']


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled', 'sms_enabled', 'push_enabled', 'quiet_hours_enabled']
    list_filter = ['email_enabled', 'sms_enabled', 'push_enabled']
    search_fields = ['user__email']
