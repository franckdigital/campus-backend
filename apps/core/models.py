from django.db import models
from django.conf import settings
import uuid


class BaseModel(models.Model):
    """Base model with common fields for all models."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Site(BaseModel):
    """Campus/Site model for multi-site support."""
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Côte d\'Ivoire')
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to='sites/logos/', blank=True, null=True)
    is_main = models.BooleanField(default=False)

    class Meta:
        db_table = 'sites'
        verbose_name = 'Site/Campus'
        verbose_name_plural = 'Sites/Campus'
        ordering = ['-is_main', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if self.is_main:
            Site.objects.filter(is_main=True).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)


class WorkspaceSettings(BaseModel):
    """Shared app-wide branding/interface settings (Workspace Studio) — a
    singleton: one row for the whole platform, edited via get_solo()."""
    app_name = models.CharField(max_length=100, default='CampusLMS')
    app_subtitle = models.CharField(max_length=255, blank=True, default='Plateforme de gestion académique')
    logo = models.ImageField(upload_to='workspace/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#6366f1')
    font_size = models.PositiveSmallIntegerField(default=14)
    compact_mode = models.BooleanField(default=False)
    language = models.CharField(max_length=5, default='fr')
    date_format = models.CharField(max_length=20, default='DD/MM/YYYY')
    items_per_page = models.PositiveSmallIntegerField(default=10)

    class Meta:
        db_table = 'workspace_settings'
        verbose_name = 'Paramètres du workspace'
        verbose_name_plural = 'Paramètres du workspace'

    def __str__(self):
        return self.app_name

    @classmethod
    def get_solo(cls):
        obj = cls.objects.first()
        if not obj:
            obj = cls.objects.create()
        return obj


class AcademicYear(BaseModel):
    """Academic year configuration."""
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    registration_open = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'academic_years'
        verbose_name = 'Année académique'
        verbose_name_plural = 'Années académiques'
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicYear.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_current(cls):
        return cls.objects.filter(is_current=True, is_active=True).first()


class AuditLog(models.Model):
    """Audit log for tracking all important actions."""
    ACTION_CHOICES = [
        ('CREATE', 'Création'),
        ('UPDATE', 'Modification'),
        ('DELETE', 'Suppression'),
        ('LOGIN', 'Connexion'),
        ('LOGOUT', 'Déconnexion'),
        ('PAYMENT', 'Paiement'),
        ('ATTENDANCE', 'Présence'),
        ('EXPORT', 'Export'),
        ('OTHER', 'Autre'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Journal d\'audit'
        verbose_name_plural = 'Journaux d\'audit'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
        ]

    def __str__(self):
        return f"{self.action} by {self.user} at {self.timestamp}"

    @classmethod
    def log(cls, user, action, model_name='', object_id='', object_repr='', 
            changes=None, ip_address=None, user_agent='', site=None, extra_data=None):
        return cls.objects.create(
            user=user,
            site=site,
            action=action,
            model_name=model_name,
            object_id=str(object_id) if object_id else '',
            object_repr=object_repr[:255] if object_repr else '',
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else '',
            extra_data=extra_data or {}
        )


class SystemConfig(BaseModel):
    """System-wide configuration settings."""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    site = models.ForeignKey(
        Site, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='configs'
    )

    class Meta:
        db_table = 'system_configs'
        verbose_name = 'Configuration système'
        verbose_name_plural = 'Configurations système'
        unique_together = ['key', 'site']

    def __str__(self):
        return self.key

    @classmethod
    def get_value(cls, key, default=None, site=None):
        try:
            config = cls.objects.get(key=key, site=site, is_active=True)
            return config.value
        except cls.DoesNotExist:
            return default
