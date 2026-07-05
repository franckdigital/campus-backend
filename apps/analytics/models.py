from django.db import models

from apps.core.models import BaseModel


class StudentKPIAnalysis(BaseModel):
    """Cached KPI computation + AI-generated narrative for one student/semester.

    KPIs are cheap to recompute on every request; only the AI narrative
    (ai_summary) is expensive (LLM call), so it's cached here and only
    regenerated on demand — see apps.analytics.services.get_or_generate_analysis.
    """
    RISK_CHOICES = [
        ('LOW', 'Faible'),
        ('MEDIUM', 'Moyen'),
        ('HIGH', 'Élevé'),
    ]

    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, related_name='kpi_analyses'
    )
    semester = models.ForeignKey(
        'academic.Semester', on_delete=models.CASCADE, related_name='kpi_analyses'
    )

    risk_score = models.PositiveSmallIntegerField(default=0)
    risk_level = models.CharField(max_length=10, choices=RISK_CHOICES, default='LOW')

    # Exact payload sent to Claude — audit trail so the AI text can always be
    # traced back to the numbers that produced it.
    kpi_snapshot = models.JSONField(default=dict, blank=True)

    ai_summary = models.TextField(blank=True)
    ai_tokens_used = models.PositiveIntegerField(default=0)
    # Set only when Claude actually responds successfully — null means "never
    # generated yet", distinct from an empty string.
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'student_kpi_analyses'
        verbose_name = 'Analyse KPI étudiant'
        verbose_name_plural = 'Analyses KPI étudiant'
        unique_together = ['student', 'semester']
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.student.matricule} — {self.semester} ({self.risk_level})"
