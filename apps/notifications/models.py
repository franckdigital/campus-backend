from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import BaseModel, Site
import uuid


class NotificationTemplate(BaseModel):
    """Reusable templates for automated notifications."""
    EVENT_TYPES = [
        ('PAYMENT_VALIDATED',  'Paiement validé'),
        ('ABSENCE_RECORDED',   'Absence constatée'),
        ('ABSENCE_PLANNED',    'Absence prévue'),
        ('CASH_DEPOSIT',       'Versement caisse'),
        ('MOBILE_MONEY',       'Mobile money'),
        ('GRADE_PUBLISHED',    'Note publiée'),
        ('BULLETIN_PUBLISHED', 'Bulletin publié'),
        ('CUSTOM',             'Personnalisé'),
    ]
    CHANNEL_CHOICES = [
        ('EMAIL',     'Email'),
        ('SMS',       'SMS'),
        ('WHATSAPP',  'WhatsApp'),
        ('PUSH',      'Push'),
        ('IN_APP',    'In-App'),
    ]

    name       = models.CharField(max_length=200)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    channel    = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    subject    = models.CharField(max_length=255, blank=True, help_text='Sujet email ou titre push')
    body       = models.TextField(help_text='Variables: {{student_name}}, {{amount}}, {{date}}, {{subject_name}}')
    site       = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='notif_templates', null=True, blank=True)

    class Meta:
        db_table = 'notification_templates'
        ordering = ['event_type', 'channel']
        unique_together = ['event_type', 'channel', 'site']

    def __str__(self):
        return f"{self.name} [{self.channel}]"

    def render(self, context: dict) -> tuple[str, str]:
        """Returns (subject, body) with context vars replaced."""
        subject = self.subject
        body    = self.body
        for k, v in context.items():
            subject = subject.replace(f'{{{{{k}}}}}', str(v))
            body    = body.replace(f'{{{{{k}}}}}', str(v))
        return subject, body


class Notification(BaseModel):
    """In-app notification record."""
    TYPE_CHOICES = [
        ('PAYMENT',       'Paiement'),
        ('ATTENDANCE',    'Présence'),
        ('ABSENCE',       'Absence'),
        ('ASSIGNMENT',    'Devoir'),
        ('GRADE',         'Note'),
        ('MESSAGE',       'Message'),
        ('SYSTEM',        'Système'),
        ('REMINDER',      'Rappel'),
        ('ALERT',         'Alerte'),
        ('FINANCE',       'Finance'),
        ('COURSE',        'Cours'),
        ('QUIZ',          'Quiz'),
        ('EVALUATION',    'Évaluation'),
        ('EXAM',          'Examen sécurisé'),
        ('VIRTUAL_CLASS', 'Classe virtuelle'),
    ]
    PRIORITY_CHOICES = [
        ('LOW',    'Basse'),
        ('NORMAL', 'Normale'),
        ('HIGH',   'Haute'),
        ('URGENT', 'Urgente'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sent_notifications'
    )
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    priority          = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='NORMAL')
    title             = models.CharField(max_length=255)
    message           = models.TextField()
    data              = models.JSONField(default=dict, blank=True)
    action_url        = models.CharField(max_length=500, blank=True)
    is_read           = models.BooleanField(default=False)
    read_at           = models.DateTimeField(null=True, blank=True)
    site              = models.ForeignKey(
        Site, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications'
    )

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.notification_type} – {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def send(cls, recipient, notification_type, title, message,
             sender=None, priority='NORMAL', data=None, action_url='', site=None):
        notification = cls.objects.create(
            recipient=recipient, sender=sender,
            notification_type=notification_type, priority=priority,
            title=title, message=message,
            data=data or {}, action_url=action_url, site=site
        )
        NotificationLog.objects.create(notification=notification, channel='IN_APP', status='SENT')
        return notification

    @classmethod
    def send_bulk(cls, recipients, notification_type, title, message,
                  sender=None, priority='NORMAL', data=None, action_url='', site=None):
        return [
            cls.send(
                recipient=r, notification_type=notification_type,
                title=title, message=message,
                sender=sender, priority=priority,
                data=data, action_url=action_url, site=site
            )
            for r in recipients
        ]


class NotificationLog(BaseModel):
    """Delivery attempt log — one row per channel per notification."""
    CHANNEL_CHOICES = [
        ('IN_APP',    'In-App'),
        ('EMAIL',     'Email'),
        ('SMS',       'SMS'),
        ('PUSH',      'Push'),
        ('WHATSAPP',  'WhatsApp'),
        ('WEBSOCKET', 'WebSocket'),
    ]
    STATUS_CHOICES = [
        ('PENDING',   'En attente'),
        ('SENT',      'Envoyé'),
        ('DELIVERED', 'Délivré'),
        ('FAILED',    'Échoué'),
        ('RETRYING',  'Relance'),
    ]

    notification   = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='logs')
    channel        = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    recipient_address = models.CharField(max_length=255, blank=True,
                                         help_text='email / phone / device token')
    sent_at        = models.DateTimeField(null=True, blank=True)
    delivered_at   = models.DateTimeField(null=True, blank=True)
    error_message  = models.TextField(blank=True)
    metadata       = models.JSONField(default=dict, blank=True)
    retry_count    = models.PositiveSmallIntegerField(default=0)
    max_retries    = models.PositiveSmallIntegerField(default=3)
    next_retry_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notification_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'next_retry_at']),
            models.Index(fields=['channel', 'status']),
        ]

    def __str__(self):
        return f"{self.notification.title} [{self.channel}] → {self.status}"

    def mark_sent(self, address=''):
        self.status = 'SENT'
        self.sent_at = timezone.now()
        if address:
            self.recipient_address = address
        # 'metadata' included so callers that stash data on the instance just
        # before calling mark_sent() (e.g. Expo push ticket ids, see
        # apps.notifications.services.dispatch_notification) don't lose it —
        # this save() is otherwise the only one that follows a status change.
        self.save(update_fields=['status', 'sent_at', 'recipient_address', 'metadata'])

    def mark_failed(self, error=''):
        self.status = 'FAILED'
        self.error_message = error
        if self.retry_count < self.max_retries:
            self.status = 'RETRYING'
            import datetime
            delay_minutes = 5 * (2 ** self.retry_count)   # 5, 10, 20 min
            self.next_retry_at = timezone.now() + datetime.timedelta(minutes=delay_minutes)
            self.retry_count += 1
        self.save(update_fields=['status', 'error_message', 'retry_count', 'next_retry_at'])


class DeviceToken(BaseModel):
    """Push notification device tokens (Expo / FCM / APNS)."""
    PLATFORM_CHOICES = [
        ('EXPO', 'Expo'),
        ('FCM',  'Firebase Android'),
        ('APNS', 'Apple iOS'),
    ]

    user     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens'
    )
    token    = models.CharField(max_length=512)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='EXPO')
    is_active = models.BooleanField(default=True)
    # False once the user explicitly logs out on this device — the token
    # stays active (still reachable) so a push still arrives, but push.py
    # sends a generic, content-free message instead of the real one until
    # the next login flips this back to True (see RegisterDeviceView.post).
    is_logged_in = models.BooleanField(default=True)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        db_table       = 'device_tokens'
        unique_together = ['user', 'token']
        verbose_name   = 'Token appareil'
        verbose_name_plural = 'Tokens appareils'

    def __str__(self):
        return f"{self.user} [{self.platform}] {self.token[:30]}…"


class NotificationPreference(BaseModel):
    """Per-user channel preferences."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences'
    )
    email_enabled    = models.BooleanField(default=True)
    sms_enabled      = models.BooleanField(default=False)
    push_enabled     = models.BooleanField(default=True)
    whatsapp_enabled = models.BooleanField(default=False)

    phone_number     = models.CharField(max_length=20, blank=True)
    whatsapp_number  = models.CharField(max_length=20, blank=True)

    payment_notifications    = models.BooleanField(default=True)
    attendance_notifications = models.BooleanField(default=True)
    assignment_notifications = models.BooleanField(default=True)
    grade_notifications      = models.BooleanField(default=True)
    message_notifications    = models.BooleanField(default=True)
    system_notifications     = models.BooleanField(default=True)

    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start   = models.TimeField(null=True, blank=True)
    quiet_hours_end     = models.TimeField(null=True, blank=True)

    class Meta:
        db_table = 'notification_preferences'

    def __str__(self):
        return f"Préférences – {self.user.full_name}"

    def active_channels(self):
        channels = ['IN_APP']
        if self.email_enabled and hasattr(self.user, 'email') and self.user.email:
            channels.append('EMAIL')
        if self.sms_enabled and self.phone_number:
            channels.append('SMS')
        if self.push_enabled:
            channels.append('PUSH')
        if self.whatsapp_enabled and self.whatsapp_number:
            channels.append('WHATSAPP')
        return channels


class ReminderConfig(BaseModel):
    """Admin-configurable reminder settings — échéancier de scolarité and
    exam reminders. Replaces the constants that used to be hard-coded in
    apps.finance.tasks (REMINDER_START_DAY/REMINDER_INTERVAL_DAYS)."""
    TYPE_CHOICES = [
        ('ECHEANCIER', 'Échéancier'),
        ('EXAMEN',     'Examen'),
    ]

    reminder_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    label         = models.CharField(max_length=200, blank=True)
    is_automatic  = models.BooleanField(default=True)
    created_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reminder_configs'
    )

    # Scope — null on any of these means "all" for that dimension (mirrors
    # apps.finance.models.FeeConfiguration's site/program/level fields).
    # A student matches this config when every set field equals theirs
    # (see matches_scope) — see apps.students.models.get_student_org_scope
    # for how a student's own site/program/level is resolved.
    site    = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True, related_name='reminder_configs')
    program = models.ForeignKey('academic.Program', on_delete=models.SET_NULL, null=True, blank=True, related_name='reminder_configs')
    level   = models.ForeignKey('academic.Level', on_delete=models.SET_NULL, null=True, blank=True, related_name='reminder_configs')

    # ECHEANCIER — jour du mois de démarrage, fréquence en jours, et une
    # date limite au-delà de laquelle les rappels automatiques s'arrêtent.
    echeancier_start_day      = models.PositiveSmallIntegerField(null=True, blank=True)
    echeancier_frequency_days = models.PositiveSmallIntegerField(null=True, blank=True)
    echeancier_deadline_date  = models.DateField(null=True, blank=True)

    # EXAMEN — entrée manuelle indépendante du module notes (pas de lien
    # avec apps.grades.models.Evaluation).
    exam_type = models.CharField(max_length=100, blank=True)
    exam_date = models.DateField(null=True, blank=True)
    exam_reminder_frequency_days = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'reminder_configs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_reminder_type_display()} – {self.label or self.id}"

    def matches_scope(self, site_id, program_id, level_id):
        """A None field on this config matches anything (= "tous")."""
        if self.site_id and self.site_id != site_id:
            return False
        if self.program_id and self.program_id != program_id:
            return False
        if self.level_id and self.level_id != level_id:
            return False
        return True

    @property
    def scope_specificity(self):
        """Number of scope dimensions this config restricts — used to pick
        the most specific match when several configs could apply to the
        same student (mirrors FeeConfiguration's site>program>level tiers)."""
        return sum(1 for f in (self.site_id, self.program_id, self.level_id) if f)
