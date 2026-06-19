from django.contrib import admin
from .models import (
    Program, Level, Class, Subject, TeacherProfile, TeacherSite,
    ClassSubjectTeacher, Enrollment, Room, Session
)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'site', 'duration_years', 'is_active']
    list_filter = ['site', 'is_active']
    search_fields = ['name', 'code']


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'program', 'order', 'is_active']
    list_filter = ['program', 'is_active']
    search_fields = ['name', 'code']


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'level', 'site', 'academic_year', 'max_students', 'is_active']
    list_filter = ['site', 'academic_year', 'level', 'is_active']
    search_fields = ['name', 'code']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'coefficient', 'hours_per_week', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'get_full_name', 'specialization', 'contract_type', 'is_active']
    list_filter = ['contract_type', 'is_active']
    search_fields = ['employee_id', 'user__email', 'user__first_name', 'user__last_name']

    def get_full_name(self, obj):
        return obj.user.full_name
    get_full_name.short_description = 'Nom complet'


@admin.register(TeacherSite)
class TeacherSiteAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'site', 'is_primary']
    list_filter = ['site', 'is_primary']


@admin.register(ClassSubjectTeacher)
class ClassSubjectTeacherAdmin(admin.ModelAdmin):
    list_display = ['class_obj', 'subject', 'teacher', 'is_active']
    list_filter = ['class_obj', 'subject', 'is_active']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'class_obj', 'academic_year', 'status', 'enrollment_date']
    list_filter = ['academic_year', 'class_obj', 'status']
    search_fields = ['student__matricule', 'student__user__first_name']


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'site', 'building', 'capacity', 'room_type', 'is_active']
    list_filter = ['site', 'room_type', 'is_active']
    search_fields = ['name', 'code', 'building']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['class_obj', 'subject', 'teacher', 'day_of_week', 'start_time', 'end_time', 'room']
    list_filter = ['day_of_week', 'class_obj', 'is_active']
    search_fields = ['class_obj__code', 'subject__name', 'teacher__user__first_name']
