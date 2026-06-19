from django.db import models
from django.conf import settings
from apps.core.models import BaseModel
from apps.academic.models import Class, Subject, Session, TeacherProfile
from apps.students.models import Student


class ZoomMeeting(BaseModel):
    """Zoom meeting linked to a session."""
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='zoom_meetings'
    )
    meeting_id = models.CharField(max_length=100)
    topic = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    duration = models.PositiveIntegerField(default=60)
    join_url = models.URLField()
    start_url = models.URLField(blank=True)
    password = models.CharField(max_length=50, blank=True)
    
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='hosted_meetings'
    )
    
    is_recorded = models.BooleanField(default=False)
    recording_url = models.URLField(blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_zoom_meetings'
    )

    class Meta:
        db_table = 'zoom_meetings'
        verbose_name = 'Réunion Zoom'
        verbose_name_plural = 'Réunions Zoom'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.topic} - {self.start_time}"


class Lesson(BaseModel):
    """Lesson/Course content."""
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content = models.TextField(blank=True)
    
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lessons'
    )
    
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    
    zoom_meeting = models.ForeignKey(
        ZoomMeeting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lessons'
    )

    class Meta:
        db_table = 'lessons'
        verbose_name = 'Leçon'
        verbose_name_plural = 'Leçons'
        ordering = ['class_obj', 'subject', 'order']

    def __str__(self):
        return f"{self.class_obj.code} - {self.subject.code} - {self.title}"

    def publish(self):
        from django.utils import timezone
        self.is_published = True
        self.published_at = timezone.now()
        self.save()


class LessonAttachment(BaseModel):
    """Attachment for a lesson."""
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='lessons/attachments/')
    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'lesson_attachments'
        verbose_name = 'Pièce jointe de leçon'
        verbose_name_plural = 'Pièces jointes de leçons'

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            self.file_type = self.file.name.split('.')[-1].lower()
        super().save(*args, **kwargs)


class Assignment(BaseModel):
    """Assignment/Homework."""
    STATUS_CHOICES = [
        ('DRAFT', 'Brouillon'),
        ('PUBLISHED', 'Publié'),
        ('CLOSED', 'Fermé'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    instructions = models.TextField(blank=True)
    
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assignments'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments'
    )
    
    due_date = models.DateTimeField()
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    published_at = models.DateTimeField(null=True, blank=True)
    
    allow_late_submission = models.BooleanField(default=False)
    late_penalty_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    attachment = models.FileField(upload_to='assignments/', blank=True, null=True)

    class Meta:
        db_table = 'assignments'
        verbose_name = 'Devoir'
        verbose_name_plural = 'Devoirs'
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.class_obj.code} - {self.title}"

    def publish(self):
        from django.utils import timezone
        self.status = 'PUBLISHED'
        self.published_at = timezone.now()
        self.save()

    @property
    def submission_count(self):
        return self.submissions.count()


class AssignmentSubmission(BaseModel):
    """Student submission for an assignment."""
    STATUS_CHOICES = [
        ('SUBMITTED', 'Soumis'),
        ('LATE', 'En retard'),
        ('GRADED', 'Noté'),
        ('RETURNED', 'Rendu'),
    ]

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='submissions/', blank=True, null=True)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    is_late = models.BooleanField(default=False)

    class Meta:
        db_table = 'assignment_submissions'
        verbose_name = 'Soumission de devoir'
        verbose_name_plural = 'Soumissions de devoirs'
        unique_together = ['assignment', 'student']
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.assignment.title} - {self.student.matricule}"

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if not self.pk:
            if timezone.now() > self.assignment.due_date:
                self.is_late = True
                self.status = 'LATE'
        super().save(*args, **kwargs)


class AssignmentCorrection(BaseModel):
    """Correction for a submission."""
    submission = models.OneToOneField(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name='correction'
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    feedback = models.TextField(blank=True)
    corrected_file = models.FileField(upload_to='corrections/', blank=True, null=True)
    
    corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='corrections'
    )
    corrected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'assignment_corrections'
        verbose_name = 'Correction de devoir'
        verbose_name_plural = 'Corrections de devoirs'

    def __str__(self):
        return f"{self.submission} - {self.score}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.submission.status = 'GRADED'
        self.submission.save()
