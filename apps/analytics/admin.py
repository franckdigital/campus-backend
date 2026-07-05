from django.contrib import admin

from .models import StudentKPIAnalysis


@admin.register(StudentKPIAnalysis)
class StudentKPIAnalysisAdmin(admin.ModelAdmin):
    list_display = ['student', 'semester', 'risk_level', 'risk_score', 'generated_at']
    list_filter = ['risk_level', 'semester']
    search_fields = ['student__matricule', 'student__user__first_name', 'student__user__last_name']
    readonly_fields = ['kpi_snapshot', 'ai_summary', 'ai_tokens_used', 'generated_at', 'created_at', 'updated_at']
