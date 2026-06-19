from django.contrib import admin
from .models import AttendanceSession, AttendanceRecord, AbsenceRequest


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ['session', 'date', 'status', 'opened_by', 'opened_at', 'present_count', 'absent_count']
    list_filter = ['status', 'date']
    search_fields = ['session__class_obj__code', 'session__subject__name']
    ordering = ['-date', '-opened_at']


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'attendance_session', 'status', 'check_in_time', 'check_in_method']
    list_filter = ['status', 'check_in_method', 'attendance_session__date']
    search_fields = ['student__matricule', 'student__user__first_name', 'student__user__last_name']


@admin.register(AbsenceRequest)
class AbsenceRequestAdmin(admin.ModelAdmin):
    list_display = ['student', 'start_date', 'end_date', 'status', 'submitted_at', 'reviewed_by']
    list_filter = ['status', 'start_date']
    search_fields = ['student__matricule', 'student__user__first_name', 'reason']
    ordering = ['-submitted_at']
