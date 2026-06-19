from django.db import models
from django.utils import timezone


class GradeCategory(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    weight = models.FloatField(default=1.0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Evaluation(models.Model):
    EVAL_TYPES = [
        ('DEVOIR', 'Devoir'),
        ('TP', 'Travaux Pratiques'),
        ('EXAMEN', 'Examen'),
        ('RATTRAPAGE', 'Rattrapage'),
    ]
    title = models.CharField(max_length=200)
    eval_type = models.CharField(max_length=20, choices=EVAL_TYPES, default='DEVOIR')
    subject = models.ForeignKey('academic.Subject', on_delete=models.CASCADE, related_name='evaluations')
    class_group = models.ForeignKey('academic.Class', on_delete=models.CASCADE, related_name='evaluations')
    semester = models.ForeignKey('academic.Semester', on_delete=models.CASCADE, related_name='evaluations', null=True, blank=True)
    date = models.DateField()
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    description = models.TextField(blank=True)
    is_locked = models.BooleanField(default=False)
    locked_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='locked_evaluations'
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_evaluations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.title} – {self.class_group.code} ({self.eval_type})"

    def lock(self, user):
        self.is_locked = True
        self.locked_by = user
        self.locked_at = timezone.now()
        self.save(update_fields=['is_locked', 'locked_by', 'locked_at'])

    def unlock(self):
        self.is_locked = False
        self.locked_by = None
        self.locked_at = None
        self.save(update_fields=['is_locked', 'locked_by', 'locked_at'])


class Grade(models.Model):
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey('academic.Subject', on_delete=models.CASCADE, related_name='grades')
    class_group = models.ForeignKey('academic.Class', on_delete=models.CASCADE, related_name='grades', null=True, blank=True)
    semester = models.ForeignKey('academic.Semester', on_delete=models.CASCADE, related_name='grades', null=True, blank=True)
    evaluation = models.ForeignKey(Evaluation, on_delete=models.SET_NULL, null=True, blank=True, related_name='grades')
    category = models.ForeignKey(GradeCategory, on_delete=models.SET_NULL, null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    date = models.DateField()
    comment = models.TextField(blank=True)
    entered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='entered_grades')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.student} – {self.subject} : {self.score}/{self.max_score}"

    @property
    def percentage(self):
        return float(self.score) / float(self.max_score) * 100 if self.max_score else 0


class ReportCard(models.Model):
    STATUS_CHOICES = [
        ('PASS', 'Admis'),
        ('FAIL', 'Ajourné'),
        ('CONDITIONAL', 'Conditionnel'),
        ('HONORS', 'Mention TB'),
        ('PENDING', 'En cours'),
    ]
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='report_cards')
    class_group = models.ForeignKey('academic.Class', on_delete=models.CASCADE, related_name='report_cards')
    semester = models.ForeignKey('academic.Semester', on_delete=models.CASCADE, related_name='report_cards', null=True, blank=True)
    average = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rank = models.PositiveIntegerField(null=True, blank=True)
    total_students = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    subject_averages = models.JSONField(default=dict, blank=True)
    teacher_comment = models.TextField(blank=True)
    principal_comment = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ['-generated_at']
        unique_together = ['student', 'class_group', 'semester']

    def __str__(self):
        return f"Bulletin {self.student} – {self.semester}"
