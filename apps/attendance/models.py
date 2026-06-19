from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import BaseModel
from apps.academic.models import Session, Class
from apps.students.models import Student
import uuid
import secrets


class AttendanceSession(BaseModel):
    """Attendance session for a class session."""
    STATUS_CHOICES = [
        ('OPEN', 'Ouverte'),
        ('CLOSED', 'Fermée'),
        ('CANCELLED', 'Annulée'),
    ]

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='attendance_sessions'
    )
    date = models.DateField()
    qr_code = models.CharField(max_length=100, unique=True, blank=True)
    qr_expiry = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='opened_attendance_sessions'
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    is_postponed        = models.BooleanField(default=False, help_text='Cours ajourné — personne ne sera marqué absent')
    postponement_reason = models.TextField(blank=True, help_text='Raison de l\'ajournement')
    postponed_by        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='postponed_attendance_sessions',
    )
    postponed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'attendance_sessions'
        verbose_name = 'Session de présence'
        verbose_name_plural = 'Sessions de présence'
        unique_together = ['session', 'date']
        ordering = ['-date', '-opened_at']

    def __str__(self):
        return f"{self.session} - {self.date}"

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.qr_code = self.generate_qr_code()
        super().save(*args, **kwargs)

    def generate_qr_code(self):
        return f"ATT-{secrets.token_urlsafe(16)}"

    def refresh_qr(self, expiry_minutes=15):
        self.qr_code = self.generate_qr_code()
        self.qr_expiry = timezone.now() + timezone.timedelta(minutes=expiry_minutes)
        self.save()
        return self.qr_code

    def is_qr_valid(self):
        if self.status != 'OPEN':
            return False
        if self.qr_expiry and timezone.now() > self.qr_expiry:
            return False
        return True

    @property
    def present_count(self):
        return self.records.filter(status='PRESENT').count()

    @property
    def absent_count(self):
        return self.records.filter(status='ABSENT').count()


class AttendanceRecord(BaseModel):
    """Individual attendance record for a student."""
    STATUS_CHOICES = [
        ('PRESENT', 'Présent'),
        ('ABSENT', 'Absent'),
        ('LATE', 'En retard'),
        ('EXCUSED', 'Excusé'),
    ]

    attendance_session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name='records'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABSENT')
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_in_method = models.CharField(
        max_length=20,
        choices=[
            ('QR', 'QR Code'),
            ('MANUAL', 'Manuel'),
            ('AUTO', 'Automatique'),
        ],
        default='MANUAL'
    )
    notes = models.TextField(blank=True)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendances'
    )
    student_latitude  = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    student_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    class Meta:
        db_table = 'attendance_records'
        verbose_name = 'Enregistrement de présence'
        verbose_name_plural = 'Enregistrements de présence'
        unique_together = ['attendance_session', 'student']

    def __str__(self):
        return f"{self.student.matricule} - {self.attendance_session.date} - {self.status}"


class AbsenceRequest(BaseModel):
    """Absence request with justification."""
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('APPROVED', 'Approuvée'),
        ('REJECTED', 'Rejetée'),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='absence_requests'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    attachment = models.FileField(upload_to='absences/justifications/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_absence_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'absence_requests'
        verbose_name = 'Demande d\'absence'
        verbose_name_plural = 'Demandes d\'absence'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.matricule} - {self.start_date} to {self.end_date}"

    def approve(self, user, notes=''):
        self.status = 'APPROVED'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
        
        AttendanceRecord.objects.filter(
            student=self.student,
            attendance_session__date__gte=self.start_date,
            attendance_session__date__lte=self.end_date,
            status='ABSENT'
        ).update(status='EXCUSED')

    def reject(self, user, notes=''):
        self.status = 'REJECTED'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
