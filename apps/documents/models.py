from django.db import models
from django.conf import settings
from apps.core.models import BaseModel, Site, AcademicYear
from apps.students.models import Student
import os


def document_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"documents/{instance.site.code}/{instance.academic_year.code}/{instance.category}/{filename}"


class DocumentCategory(BaseModel):
    """Category for document classification."""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )
    allowed_extensions = models.JSONField(default=list, blank=True)
    max_file_size_mb = models.PositiveIntegerField(default=10)
    requires_validation = models.BooleanField(default=True)
    retention_years = models.PositiveIntegerField(default=5)

    class Meta:
        db_table = 'document_categories'
        verbose_name = 'Catégorie de document'
        verbose_name_plural = 'Catégories de documents'
        ordering = ['name']

    def __str__(self):
        return self.name


class Document(BaseModel):
    """Document model for GED."""
    STATUS_CHOICES = [
        ('DRAFT', 'Brouillon'),
        ('PENDING', 'En attente de validation'),
        ('VALIDATED', 'Validé'),
        ('REJECTED', 'Rejeté'),
        ('ARCHIVED', 'Archivé'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.PROTECT,
        related_name='documents'
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name='documents'
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name='documents'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='documents'
    )
    
    file = models.FileField(upload_to=document_upload_path)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    file_type = models.CharField(max_length=100, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_documents'
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    validation_notes = models.TextField(blank=True)
    
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'documents'
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.category.name})"

    def save(self, *args, **kwargs):
        if self.file:
            self.file_name = os.path.basename(self.file.name)
            self.file_size = self.file.size
            self.file_type = self.file.name.split('.')[-1].lower()
        super().save(*args, **kwargs)

    def validate(self, user, notes=''):
        from django.utils import timezone
        self.status = 'VALIDATED'
        self.validated_by = user
        self.validated_at = timezone.now()
        self.validation_notes = notes
        self.save()

    def reject(self, user, notes=''):
        from django.utils import timezone
        self.status = 'REJECTED'
        self.validated_by = user
        self.validated_at = timezone.now()
        self.validation_notes = notes
        self.save()


class Archive(BaseModel):
    """Archive for long-term document storage."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name='archives'
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name='archives'
    )
    documents = models.ManyToManyField(
        Document,
        through='ArchiveDocument',
        related_name='archives'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_archives'
    )
    archived_at = models.DateTimeField(auto_now_add=True)
    retention_until = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'archives'
        verbose_name = 'Archive'
        verbose_name_plural = 'Archives'
        ordering = ['-archived_at']

    def __str__(self):
        return f"{self.name} - {self.academic_year.code}"

    @property
    def document_count(self):
        return self.archive_documents.count()


class ArchiveDocument(models.Model):
    """Through model for Archive-Document relationship."""
    archive = models.ForeignKey(
        Archive,
        on_delete=models.CASCADE,
        related_name='archive_documents'
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='archive_entries'
    )
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        db_table = 'archive_documents'
        unique_together = ['archive', 'document']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.document.status = 'ARCHIVED'
        self.document.save()
