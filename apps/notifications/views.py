from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from django.utils import timezone
from django.db.models import Count, Q

from .models import (
    Notification, NotificationLog, NotificationPreference, NotificationTemplate,
    ReminderConfig,
)
from .serializers import (
    NotificationSerializer, NotificationListSerializer,
    NotificationPreferenceSerializer, SendNotificationSerializer,
    NotificationLogSerializer, NotificationTemplateSerializer,
    ReminderConfigSerializer,
)
from .services import dispatch_notification


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    filter_backends  = [DjangoFilterBackend, OrderingFilter]
    ordering_fields  = ['created_at', 'priority']
    filterset_fields = ['notification_type', 'priority', 'is_read', 'is_active']

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('sender', 'site').prefetch_related('logs')

    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_read()
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False, is_active=True
        ).update(is_read=True, read_at=timezone.now())
        return Response({'detail': f'{count} notifications marquées comme lues'})

    @action(detail=False, methods=['get'])
    def unread(self, request):
        qs = self.get_queryset().filter(is_read=False)
        return Response(NotificationListSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """H3: Full delivery history, accessible to admins."""
    queryset = NotificationLog.objects.select_related(
        'notification__recipient', 'notification__sender'
    ).all()
    serializer_class = NotificationLogSerializer
    filter_backends  = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['channel', 'status', 'notification__notification_type']
    search_fields    = [
        'notification__title', 'notification__recipient__first_name',
        'notification__recipient__last_name', 'recipient_address',
    ]
    ordering_fields  = ['created_at', 'sent_at', 'status']

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Manually retry a FAILED or RETRYING log."""
        log = self.get_object()
        if log.status not in ('FAILED', 'RETRYING'):
            return Response(
                {'detail': 'Seuls les logs FAILED ou RETRYING peuvent être relancés'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notification = log.notification
        log.status       = 'PENDING'
        log.error_message = ''
        log.save(update_fields=['status', 'error_message'])

        from .services import _send_email, _send_sms, _send_whatsapp
        if log.channel == 'EMAIL':
            _send_email(notification, log)
        elif log.channel == 'SMS':
            try:
                phone = notification.recipient.notification_preferences.phone_number
            except Exception:
                phone = log.recipient_address
            if phone:
                _send_sms(notification, log, phone)
            else:
                log.mark_failed('Numéro introuvable')
        elif log.channel == 'WHATSAPP':
            try:
                wa = notification.recipient.notification_preferences.whatsapp_number
            except Exception:
                wa = log.recipient_address
            if wa:
                _send_whatsapp(notification, log, wa)
            else:
                log.mark_failed('Numéro WA introuvable')

        return Response(NotificationLogSerializer(log).data)


class NotificationStatsView(APIView):
    """H3: Delivery stats by channel and event type."""
    def get(self, request):
        site_id = request.query_params.get('site_id')
        days    = int(request.query_params.get('days', 30))
        since   = timezone.now() - timezone.timedelta(days=days)

        logs_qs = NotificationLog.objects.filter(created_at__gte=since)
        notif_qs = Notification.objects.filter(created_at__gte=since, is_active=True)

        if site_id:
            notif_qs = notif_qs.filter(site_id=site_id)
            logs_qs  = logs_qs.filter(notification__site_id=site_id)

        # By channel
        by_channel = list(
            logs_qs.values('channel', 'status').annotate(count=Count('id'))
        )
        # By notification type
        by_type = list(
            notif_qs.values('notification_type').annotate(
                total=Count('id'),
                unread=Count('id', filter=Q(is_read=False)),
            )
        )
        # Overall delivery rates per channel
        channel_summary = {}
        for row in by_channel:
            ch = row['channel']
            if ch not in channel_summary:
                channel_summary[ch] = {'sent': 0, 'failed': 0, 'pending': 0, 'total': 0}
            channel_summary[ch]['total'] += row['count']
            st = row['status'].lower()
            if st in ('sent', 'delivered'):
                channel_summary[ch]['sent'] += row['count']
            elif st == 'failed':
                channel_summary[ch]['failed'] += row['count']
            else:
                channel_summary[ch]['pending'] += row['count']

        for ch in channel_summary:
            total = channel_summary[ch]['total']
            channel_summary[ch]['rate'] = round(
                channel_summary[ch]['sent'] / total * 100, 1
            ) if total else 0

        # Recent failed
        recent_failed = NotificationLogSerializer(
            logs_qs.filter(status='FAILED').order_by('-created_at')[:20],
            many=True
        ).data

        return Response({
            'by_channel': channel_summary,
            'by_type': by_type,
            'recent_failed': recent_failed,
            'total_sent': logs_qs.filter(status__in=['SENT', 'DELIVERED']).count(),
            'total_failed': logs_qs.filter(status='FAILED').count(),
            'total_retrying': logs_qs.filter(status='RETRYING').count(),
        })


class SendNotificationView(APIView):
    """Manual broadcast: single user, list of users, or by role."""
    def post(self, request):
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.accounts.models import User
        from apps.core.models import Site

        site = None
        if data.get('site_id'):
            try:
                site = Site.objects.get(id=data['site_id'])
            except Site.DoesNotExist:
                pass

        channels = data.get('channels') or []

        # Resolve recipients
        recipients = []
        if data.get('recipient_id'):
            try:
                recipients.append(User.objects.get(id=data['recipient_id']))
            except User.DoesNotExist:
                return Response({'detail': 'Destinataire non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        if data.get('recipient_ids'):
            recipients += list(User.objects.filter(id__in=data['recipient_ids']))

        if data.get('role'):
            role_users = User.objects.filter(
                is_active=True,
                roles__name=data['role'],
            ).distinct()
            recipients += list(role_users)

        # De-duplicate
        seen = set()
        unique_recipients = []
        for r in recipients:
            if r.id not in seen:
                seen.add(r.id)
                unique_recipients.append(r)

        notifications = []
        for recipient in unique_recipients:
            n = Notification.send(
                recipient=recipient,
                notification_type=data['notification_type'],
                title=data['title'],
                message=data['message'],
                sender=request.user,
                priority=data['priority'],
                data=data.get('data', {}),
                action_url=data.get('action_url', ''),
                site=site,
            )
            dispatch_notification(
                n,
                channels=channels if channels else None,
            )
            notifications.append(n)

        return Response({
            'detail': f'{len(notifications)} notification(s) envoyée(s)',
            'notifications': NotificationListSerializer(notifications, many=True).data,
        }, status=status.HTTP_201_CREATED)


class RegisterDeviceView(APIView):
    """Register or refresh a mobile push token for the current user.

    POST (on login / app start) marks the token fully active AND "logged
    in" — the user gets real push content again. DELETE (on logout) does
    NOT deactivate the token: the device stays reachable so push still
    arrives, but marked "logged out" (is_logged_in=False) so push.py sends
    a generic, content-free message instead of the real one until the next
    login on that same device flips it back.
    """
    # An unpaid student is exactly who échéancier reminders target — the fee
    # gate must not block them from registering the device that receives
    # those reminders in the first place.
    fee_gate_exempt = True

    def post(self, request):
        token    = (request.data.get('token') or '').strip()
        platform = request.data.get('platform', 'EXPO').upper()
        if not token:
            return Response({'detail': 'Token requis.'}, status=status.HTTP_400_BAD_REQUEST)
        if platform not in ('EXPO', 'FCM', 'APNS'):
            platform = 'EXPO'
        from .models import DeviceToken
        obj, created = DeviceToken.objects.update_or_create(
            user=request.user, token=token,
            defaults={'platform': platform, 'is_active': True, 'is_logged_in': True},
        )
        return Response({'detail': 'Token enregistré.', 'created': created})

    def delete(self, request):
        token = (request.data.get('token') or '').strip()
        if token:
            from .models import DeviceToken
            DeviceToken.objects.filter(user=request.user, token=token).update(is_logged_in=False)
        return Response({'detail': 'Session marquée déconnectée sur cet appareil.'})


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationPreferenceSerializer

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)

    def get_object(self):
        obj, _ = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj

    def list(self, request):
        return Response(self.get_serializer(self.get_object()).data)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ['event_type', 'channel', 'site', 'is_active']


class ReminderConfigViewSet(viewsets.ModelViewSet):
    """Admin-facing CRUD for échéancier/exam reminder settings, plus a
    'send-now' action that triggers an immediate send regardless of
    is_automatic or the configured frequency/timing."""
    queryset = ReminderConfig.objects.select_related('created_by', 'site', 'program', 'level').all()
    serializer_class = ReminderConfigSerializer
    filter_backends  = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['reminder_type', 'is_active', 'is_automatic', 'site', 'program', 'level']
    ordering_fields  = ['created_at', 'exam_date']

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        self._enforce_single_active_echeancier(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._enforce_single_active_echeancier(instance)

    def _enforce_single_active_echeancier(self, instance):
        # Only one échéancier schedule per exact scope (site+program+level) —
        # activating one deactivates any other config with that SAME scope,
        # so apps.finance.tasks._get_echeancier_config always has a single
        # unambiguous match for a given student. Configs with a different
        # scope (e.g. one for Site A, another for Site B, or a global
        # all-sites fallback) coexist without conflict.
        if instance.reminder_type == 'ECHEANCIER' and instance.is_active:
            ReminderConfig.objects.filter(
                reminder_type='ECHEANCIER', is_active=True,
                site_id=instance.site_id, program_id=instance.program_id, level_id=instance.level_id,
            ).exclude(pk=instance.pk).update(is_active=False)

    @action(detail=True, methods=['post'], url_path='send-now')
    def send_now(self, request, pk=None):
        config = self.get_object()
        today = timezone.now().date()

        if config.reminder_type == 'ECHEANCIER':
            from apps.finance.tasks import send_echeancier_reminders
            count = send_echeancier_reminders(force=True, config=config)
        else:
            from .services import send_exam_reminder_config
            count = send_exam_reminder_config(config, today, force=True)

        return Response({'detail': f'{count} rappel(s) envoyé(s) immédiatement.', 'sent_count': count})
