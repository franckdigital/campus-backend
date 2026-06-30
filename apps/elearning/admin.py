from django.contrib import admin
from .models import (
    ZoomMeeting, Lesson, LessonAttachment, Chapter, LessonProgress,
    Quiz, Question, Choice, QuizAttempt, AttemptAnswer,
    Assignment, AssignmentSubmission, AssignmentCorrection,
    LibraryDocument, DocumentFavorite, ReadingProgress,
    SecureExam, ExamSession,
    VirtualLab, LabSubmission,
    AIConversation, AIMessage,
    VideoLibrary, VideoSubtitle, VideoProgress, VideoDownloadToken,
    VirtualClassroom, ClassroomPoll, PollResponse, ClassroomChatMessage, HandRaise,
)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'class_obj', 'subject', 'lesson', 'pass_score_percent', 'is_published']
    list_filter = ['is_published', 'class_obj', 'subject']
    search_fields = ['title']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'question_type', 'order', 'points']
    list_filter = ['question_type', 'quiz']


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['question', 'text', 'is_correct', 'order']
    list_filter = ['is_correct']


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'quiz', 'percent', 'is_passed', 'is_graded', 'submitted_at']
    list_filter = ['is_passed', 'is_graded']
    search_fields = ['student__matricule', 'quiz__title']


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['title', 'class_obj', 'subject', 'order', 'is_published']
    list_filter = ['is_published', 'class_obj', 'subject']
    search_fields = ['title']
    ordering = ['class_obj', 'subject', 'order']


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'lesson', 'watch_percent', 'time_spent_seconds', 'is_completed']
    list_filter = ['is_completed']
    search_fields = ['student__matricule', 'lesson__title']


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


@admin.register(LibraryDocument)
class LibraryDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'authors', 'doc_type', 'year', 'is_downloadable', 'is_published', 'download_count', 'view_count']
    list_filter = ['doc_type', 'language', 'is_published', 'is_downloadable']
    search_fields = ['title', 'authors', 'abstract', 'keywords', 'isbn', 'doi']
    filter_horizontal = ['subjects']
    ordering = ['-created_at']


@admin.register(DocumentFavorite)
class DocumentFavoriteAdmin(admin.ModelAdmin):
    list_display = ['student', 'document', 'created_at']
    search_fields = ['student__matricule', 'document__title']


@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'document', 'current_page', 'last_read_at']
    search_fields = ['student__matricule', 'document__title']


@admin.register(SecureExam)
class SecureExamAdmin(admin.ModelAdmin):
    list_display = ['title', 'class_obj', 'subject', 'exam_type', 'duration_minutes', 'start_date', 'is_published']
    list_filter = ['exam_type', 'is_published', 'fullscreen_required', 'webcam_required']
    search_fields = ['title', 'description']
    ordering = ['-start_date']


@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam', 'status', 'started_at', 'submitted_at', 'tab_switch_count', 'is_flagged']
    list_filter = ['status', 'is_flagged']
    search_fields = ['student__matricule', 'exam__title']
    ordering = ['-started_at']


@admin.register(VirtualLab)
class VirtualLabAdmin(admin.ModelAdmin):
    list_display = ['title', 'class_obj', 'subject', 'lab_type', 'duration_minutes', 'is_published']
    list_filter = ['lab_type', 'is_published']
    search_fields = ['title', 'description']
    ordering = ['class_obj', 'subject', 'order']


@admin.register(LabSubmission)
class LabSubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'lab', 'status', 'score', 'submitted_at', 'graded_at']
    list_filter = ['status']
    search_fields = ['student__matricule', 'lab__title']
    ordering = ['-started_at']


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ['user', 'conv_type', 'title', 'subject', 'created_at', 'updated_at']
    list_filter = ['conv_type']
    search_fields = ['user__email', 'title']
    ordering = ['-updated_at']


@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'role', 'tokens_used', 'created_at']
    list_filter = ['role']
    ordering = ['-created_at']


# Lot 9 — Vidéothèque
class VideoSubtitleInline(admin.TabularInline):
    model = VideoSubtitle
    extra = 1


@admin.register(VideoLibrary)
class VideoLibraryAdmin(admin.ModelAdmin):
    list_display  = ['title', 'source_type', 'class_obj', 'subject', 'is_published', 'view_count', 'order']
    list_filter   = ['source_type', 'is_published', 'is_downloadable', 'watermark_enabled']
    search_fields = ['title', 'description', 'tags']
    inlines       = [VideoSubtitleInline]
    ordering      = ['order', 'title']


@admin.register(VideoProgress)
class VideoProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'video', 'position_seconds', 'is_completed', 'last_watched_at']
    list_filter  = ['is_completed']
    ordering     = ['-last_watched_at']


@admin.register(VideoDownloadToken)
class VideoDownloadTokenAdmin(admin.ModelAdmin):
    list_display = ['student', 'video', 'expires_at', 'is_used']
    list_filter  = ['is_used']
    ordering     = ['-created_at']


# Lot 8 — Classes virtuelles
@admin.register(VirtualClassroom)
class VirtualClassroomAdmin(admin.ModelAdmin):
    list_display  = ['title', 'provider', 'class_obj', 'start_time', 'duration_minutes', 'is_ended']
    list_filter   = ['provider', 'is_ended', 'enable_recording']
    search_fields = ['title', 'meeting_id', 'jitsi_room_name']
    ordering      = ['-start_time']


@admin.register(ClassroomPoll)
class ClassroomPollAdmin(admin.ModelAdmin):
    list_display = ['question', 'classroom', 'is_active', 'show_results', 'created_at']
    list_filter  = ['is_active', 'show_results']


@admin.register(PollResponse)
class PollResponseAdmin(admin.ModelAdmin):
    list_display = ['poll', 'student', 'selected_option']


@admin.register(ClassroomChatMessage)
class ClassroomChatMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'classroom', 'is_pinned', 'created_at']
    list_filter  = ['is_pinned']
    ordering     = ['-created_at']


@admin.register(HandRaise)
class HandRaiseAdmin(admin.ModelAdmin):
    list_display = ['student', 'classroom', 'is_raised', 'raised_at']
    list_filter  = ['is_raised']
