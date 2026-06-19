from rest_framework import serializers
from .models import Notification, NotificationLog, NotificationPreference, NotificationTemplate


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    notification_title = serializers.CharField(source='notification.title', read_only=True)
    notification_type  = serializers.CharField(source='notification.notification_type', read_only=True)
    recipient_name     = serializers.CharField(source='notification.recipient.full_name', read_only=True)

    class Meta:
        model = NotificationLog
        fields = [
            'id', 'notification', 'notification_title', 'notification_type',
            'recipient_name', 'channel', 'status', 'recipient_address',
            'sent_at', 'delivered_at', 'error_message',
            'retry_count', 'max_retries', 'next_retry_at',
            'metadata', 'created_at',
        ]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    site_name   = serializers.CharField(source='site.name', read_only=True)
    logs        = NotificationLogSerializer(many=True, read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'sender', 'sender_name',
            'notification_type', 'priority', 'title', 'message',
            'data', 'action_url', 'is_read', 'read_at',
            'site', 'site_name', 'is_active', 'created_at',
            'logs',
        ]
        read_only_fields = ['id', 'read_at', 'created_at']


class NotificationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'priority', 'title', 'message',
            'is_read', 'created_at', 'action_url',
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user',
            'email_enabled', 'sms_enabled', 'push_enabled', 'whatsapp_enabled',
            'phone_number', 'whatsapp_number',
            'payment_notifications', 'attendance_notifications',
            'assignment_notifications', 'grade_notifications',
            'message_notifications', 'system_notifications',
            'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class SendNotificationSerializer(serializers.Serializer):
    recipient_id   = serializers.UUIDField(required=False)
    recipient_ids  = serializers.ListField(child=serializers.UUIDField(), required=False)
    role           = serializers.CharField(required=False, allow_blank=True,
                                           help_text='Send to all users with this role')
    notification_type = serializers.ChoiceField(choices=Notification.TYPE_CHOICES)
    priority       = serializers.ChoiceField(choices=Notification.PRIORITY_CHOICES, default='NORMAL')
    title          = serializers.CharField(max_length=255)
    message        = serializers.CharField()
    channels       = serializers.ListField(
        child=serializers.ChoiceField(choices=NotificationLog.CHANNEL_CHOICES),
        required=False, default=list,
    )
    data           = serializers.JSONField(required=False, default=dict)
    action_url     = serializers.CharField(max_length=500, required=False, allow_blank=True)
    site_id        = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, data):
        if not data.get('recipient_id') and not data.get('recipient_ids') and not data.get('role'):
            raise serializers.ValidationError('recipient_id, recipient_ids ou role est requis')
        return data
