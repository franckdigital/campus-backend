from django.db import models
from django.conf import settings
from apps.core.models import BaseModel, Site, AcademicYear
import uuid


class Parent(BaseModel):
    """Parent model linked to user account."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='parent_profile'
    )
    profession = models.CharField(max_length=255, blank=True)
    employer = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    relationship = models.CharField(
        max_length=50,
        choices=[
            ('FATHER', 'Père'),
            ('MOTHER', 'Mère'),
            ('GUARDIAN', 'Tuteur'),
            ('OTHER', 'Autre'),
        ],
        default='GUARDIAN'
    )

    class Meta:
        db_table = 'parents'
        verbose_name = 'Parent'
        verbose_name_plural = 'Parents'

    def __str__(self):
        return f"{self.user.full_name} ({self.relationship})"


class Student(BaseModel):
    """Student model with complete profile."""
    GENDER_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Actif'),
        ('GRADUATED', 'Diplômé'),
        ('SUSPENDED', 'Suspendu'),
        ('WITHDRAWN', 'Retiré'),
        ('TRANSFERRED', 'Transféré'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    matricule = models.CharField(max_length=50, unique=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    birth_date = models.DateField()
    birth_place = models.CharField(max_length=255, blank=True)
    nationality = models.CharField(max_length=100, default='Ivoirienne')
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name='students'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    admission_date = models.DateField()
    graduation_date = models.DateField(null=True, blank=True)
    
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relation = models.CharField(max_length=100, blank=True)
    
    medical_info = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    photo = models.TextField(blank=True, null=True)
    
    # Financial fields
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    registration_fee_paid = models.BooleanField(default=False)
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'students'
        verbose_name = 'Étudiant'
        verbose_name_plural = 'Étudiants'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.matricule} - {self.user.full_name}"

    def save(self, *args, **kwargs):
        if not self.matricule:
            self.matricule = self.generate_matricule()
        super().save(*args, **kwargs)

    def generate_matricule(self):
        import datetime
        year = datetime.date.today().year
        site_code = self.site.code if self.site else 'XX'
        count = Student.objects.filter(
            matricule__startswith=f"{site_code}{year}"
        ).count() + 1
        return f"{site_code}{year}{count:04d}"


class StudentParent(models.Model):
    """Link between students and parents."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='student_parents'
    )
    parent = models.ForeignKey(
        Parent,
        on_delete=models.CASCADE,
        related_name='parent_students'
    )
    is_primary = models.BooleanField(default=False)
    can_pickup = models.BooleanField(default=True)
    receives_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'student_parents'
        unique_together = ['student', 'parent']
        verbose_name = 'Lien étudiant-parent'
        verbose_name_plural = 'Liens étudiants-parents'

    def __str__(self):
        return f"{self.student.user.full_name} - {self.parent.user.full_name}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            StudentParent.objects.filter(
                student=self.student, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class StudentFile(BaseModel):
    """Student file/dossier containing all records."""
    FILE_TYPE_CHOICES = [
        ('INSCRIPTION', 'Inscription'),
        ('REINSCRIPTION', 'Réinscription'),
        ('PAYMENT', 'Paiement'),
        ('ABSENCE', 'Absence'),
        ('DISCIPLINE', 'Discipline'),
        ('ACADEMIC', 'Académique'),
        ('MEDICAL', 'Médical'),
        ('DOCUMENT', 'Document'),
        ('OTHER', 'Autre'),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='files'
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name='student_files'
    )
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    attachment = models.FileField(upload_to='students/files/', blank=True, null=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_student_files'
    )

    class Meta:
        db_table = 'student_files'
        verbose_name = 'Dossier étudiant'
        verbose_name_plural = 'Dossiers étudiants'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.matricule} - {self.title}"


class StudentCard(BaseModel):
    """Digital student card."""
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='cards'
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name='student_cards'
    )
    card_number = models.CharField(max_length=50, unique=True)
    qr_code = models.ImageField(upload_to='students/cards/qr/', blank=True, null=True)
    issue_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    is_valid = models.BooleanField(default=True)

    class Meta:
        db_table = 'student_cards'
        verbose_name = 'Carte étudiant'
        verbose_name_plural = 'Cartes étudiants'
        unique_together = ['student', 'academic_year']

    def __str__(self):
        return f"{self.card_number} - {self.student.user.full_name}"

    def save(self, *args, **kwargs):
        if not self.card_number:
            self.card_number = self.generate_card_number()
        super().save(*args, **kwargs)

    def generate_card_number(self):
        import datetime
        year = self.academic_year.code if self.academic_year else datetime.date.today().year
        return f"CARD-{self.student.matricule}-{year}"
