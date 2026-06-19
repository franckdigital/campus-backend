import uuid
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel, Site, AcademicYear


DEPARTMENT_CHOICES = [
    ('DIRECTION', 'Direction'),
    ('SCOLARITE', 'Scolarité'),
    ('COMPTABILITE', 'Comptabilité'),
    ('INFORMATIQUE', 'Informatique'),
    ('SECRETARIAT', 'Secrétariat'),
    ('BIBLIOTHEQUE', 'Bibliothèque'),
    ('MAINTENANCE', 'Maintenance'),
    ('AUTRE', 'Autre'),
]

CONTRACT_CHOICES = [
    ('PERMANENT', 'Permanent'),
    ('CONTRACT', 'Contractuel'),
    ('INTERN', 'Stagiaire'),
]


class StaffProfile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile'
    )
    employee_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES, default='AUTRE')
    position = models.CharField(max_length=255)          # Poste occupé
    hire_date = models.DateField(null=True, blank=True)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_CHOICES, default='PERMANENT')
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_members')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_profiles')
    contract_hours_per_week = models.PositiveIntegerField(null=True, blank=True)
    bio = models.TextField(blank=True)

    class Meta:
        db_table = 'staff_profiles'
        verbose_name = 'Personnel administratif'
        verbose_name_plural = 'Personnels administratifs'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.employee_id} - {self.user.full_name}"


class StaffExperience(BaseModel):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='experiences')
    position = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'staff_experiences'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.staff.user.full_name} – {self.position} @ {self.company}"


class StaffDocument(BaseModel):
    DOCUMENT_TYPES = [
        ('IDENTITY', "Pièce d'identité"),
        ('CONTRACT', 'Contrat'),
        ('DIPLOMA', 'Diplôme'),
        ('CERTIFICATE', 'Certificat'),
        ('OTHER', 'Autre'),
    ]
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='OTHER')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='staff_documents/%Y/')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='uploaded_staff_documents'
    )

    class Meta:
        db_table = 'staff_documents'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.staff.user.full_name} – {self.title}"
