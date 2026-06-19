from django.contrib import admin
from .models import (
    ZoomMeeting, Lesson, LessonAttachment,
    Assignment, AssignmentSubmission, AssignmentCorrection
)


@admin.register(ZoomMeeting)
class ZoomMeetingAdmin(admin.ModelAdmin):
    list_display = ['topic', 'session', 'meeting_id', 'start_time', 'duration', 'host']
    list_filter = ['is_recorded', 'start_time']
    search_fields = ['topic', 'meeting_id']
    ordering = ['-start_time']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'class_obj', 'subject', 'teacher', 'order', 'is_published']
    list_filter = ['is_published', 'class_obj', 'subject']
    search_fields = ['title', 'description']
    ordering = ['class_obj', 'subject', 'order']


@admin.register(LessonAttachment)
class LessonAttachmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'file_type', 'file_size']
    list_filter = ['file_type']
    search_fields = ['title', 'lesson__title']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'class_obj', 'subject', 'due_date', 'max_score', 'status', 'submission_count']
    list_filter = ['status', 'class_obj', 'subject', 'due_date']
    search_fields = ['title', 'description']
    ordering = ['-due_date']


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'student', 'submitted_at', 'status', 'is_late']
    list_filter = ['status', 'is_late', 'assignment']
    search_fields = ['student__matricule', 'assignment__title']
    ordering = ['-submitted_at']


@admin.register(AssignmentCorrection)
class AssignmentCorrectionAdmin(admin.ModelAdmin):
    list_display = ['submission', 'score', 'corrected_by', 'corrected_at']
    list_filter = ['corrected_at']
    search_fields = ['submission__student__matricule', 'feedback']
    ordering = ['-corrected_at']
