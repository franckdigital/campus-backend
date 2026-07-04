from rest_framework import serializers
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
    MeetingSegment, SessionParticipant, SessionLog,
    Course, CourseSection, CourseChapter, CourseLesson,
)


class ChapterSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    lesson_count = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = [
            'id', 'title', 'description', 'class_obj', 'class_name',
            'subject', 'subject_name', 'order', 'is_published',
            'lesson_count', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_lesson_count(self, obj):
        return obj.lessons.filter(is_active=True).count()


class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = [
            'id', 'student', 'lesson', 'started_at', 'completed_at',
            'watch_percent', 'time_spent_seconds', 'is_completed', 'is_active'
        ]
        read_only_fields = ['id', 'completed_at', 'is_completed']


# ── Quiz : édition (admin / enseignant) — expose les bonnes réponses ───────

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'question', 'text', 'is_correct', 'match_text', 'order', 'is_active']
        read_only_fields = ['id']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'quiz', 'question_type', 'text', 'image', 'order', 'points',
            'explanation', 'numeric_answer', 'numeric_tolerance', 'text_answer',
            'choices', 'is_active'
        ]
        read_only_fields = ['id']


class QuizSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    question_count = serializers.SerializerMethodField()
    max_score = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    attempts_used = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'class_obj', 'class_name', 'subject', 'subject_name',
            'lesson', 'time_limit_minutes', 'max_attempts', 'pass_score_percent',
            'shuffle_questions', 'is_published', 'subject_file', 'questions', 'question_count', 'max_score',
            'attempts_used', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_question_count(self, obj):
        return obj.questions.filter(is_active=True).count()

    def get_attempts_used(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'student_profile'):
            return 0
        return obj.attempts.filter(student=request.user.student_profile).count()


class QuizListSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    question_count = serializers.SerializerMethodField()
    attempts_used = serializers.SerializerMethodField()
    best_score = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'class_obj', 'class_name', 'subject', 'subject_name',
            'lesson', 'time_limit_minutes', 'max_attempts', 'pass_score_percent',
            'is_published', 'question_count', 'attempts_used', 'best_score'
        ]

    def get_question_count(self, obj):
        return obj.questions.filter(is_active=True).count()

    def get_attempts_used(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'student_profile'):
            return 0
        return obj.attempts.filter(student=request.user.student_profile).count()

    def get_best_score(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'student_profile'):
            return None
        best = obj.attempts.filter(student=request.user.student_profile, submitted_at__isnull=False).order_by('-percent').first()
        if best is None:
            return None
        return {'percent': float(best.percent or 0), 'is_passed': best.is_passed}


# ── Quiz : passage (étudiant) — masque les bonnes réponses ─────────────────

class ChoiceTakeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'order']


class QuestionTakeSerializer(serializers.ModelSerializer):
    choices = ChoiceTakeSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'question_type', 'text', 'image', 'order', 'points', 'choices']


class QuizTakeSerializer(serializers.ModelSerializer):
    questions = QuestionTakeSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'time_limit_minutes',
            'max_attempts', 'pass_score_percent', 'shuffle_questions', 'questions'
        ]


# ── Quiz : tentatives et réponses ───────────────────────────────────────────

class AttemptAnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    choice_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    text_response = serializers.CharField(required=False, allow_blank=True, default='')
    numeric_response = serializers.DecimalField(max_digits=12, decimal_places=4, required=False, allow_null=True, default=None)
    ordering_response = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    matching_response = serializers.DictField(child=serializers.CharField(), required=False, default=dict)


class AttemptAnswerReviewSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.text', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    explanation = serializers.CharField(source='question.explanation', read_only=True)
    selected_choice_ids = serializers.SerializerMethodField()

    class Meta:
        model = AttemptAnswer
        fields = [
            'id', 'question', 'question_text', 'question_type', 'explanation',
            'selected_choice_ids', 'text_response', 'numeric_response',
            'ordering_response', 'matching_response',
            'is_correct', 'points_earned', 'manual_feedback'
        ]

    def get_selected_choice_ids(self, obj):
        return [str(c.id) for c in obj.selected_choices.all()]


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    answers = AttemptAnswerReviewSerializer(many=True, read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            'id', 'quiz', 'quiz_title', 'student', 'started_at', 'submitted_at',
            'score', 'max_score', 'percent', 'is_passed', 'is_graded', 'answers'
        ]
        read_only_fields = ['id', 'started_at', 'score', 'max_score', 'percent', 'is_passed', 'is_graded']


class ZoomMeetingSerializer(serializers.ModelSerializer):
    session_info = serializers.SerializerMethodField()
    host_name = serializers.CharField(source='host.full_name', read_only=True)

    class Meta:
        model = ZoomMeeting
        fields = [
            'id', 'session', 'session_info', 'meeting_id', 'topic',
            'start_time', 'duration', 'join_url', 'start_url', 'password',
            'host', 'host_name', 'is_recorded', 'recording_url',
            'created_by', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'meeting_id', 'join_url', 'start_url', 'created_at']

    def get_session_info(self, obj):
        return {
            'class': obj.session.class_obj.name,
            'subject': obj.session.subject.name,
            'day': obj.session.day_of_week
        }


class LessonAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonAttachment
        fields = [
            'id', 'lesson', 'title', 'block_type', 'order',
            'file', 'file_type', 'file_size', 'content', 'url', 'is_active'
        ]
        read_only_fields = ['id', 'file_type', 'file_size']


class _LessonStudentMixin:
    """Shared helpers to expose per-student unlock/completion state."""

    def _student(self):
        request = self.context.get('request')
        if not request or not getattr(request.user, 'is_authenticated', False):
            return None
        return getattr(request.user, 'student_profile', None)

    def get_is_unlocked(self, obj):
        student = self._student()
        if not student:
            return True
        return obj.is_unlocked_for(student)

    def get_is_completed(self, obj):
        student = self._student()
        if not student:
            return False
        return obj.is_completed_by(student)


class LessonSerializer(_LessonStudentMixin, serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.full_name', read_only=True)
    chapter_title = serializers.CharField(source='chapter.title', read_only=True)
    attachments = LessonAttachmentSerializer(many=True, read_only=True)
    zoom_meeting = ZoomMeetingSerializer(read_only=True)
    is_unlocked = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    my_progress = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'description', 'content', 'class_obj', 'class_name',
            'subject', 'subject_name', 'teacher', 'teacher_name',
            'chapter', 'chapter_title', 'order',
            'is_published', 'published_at', 'zoom_meeting', 'attachments',
            'min_watch_percent', 'min_duration_seconds', 'requires_assignment', 'requires_quiz',
            'is_unlocked', 'is_completed', 'my_progress',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'published_at', 'created_at', 'updated_at']

    def get_my_progress(self, obj):
        student = self._student()
        if not student:
            return None
        progress = obj.progress_records.filter(student=student).first()
        return LessonProgressSerializer(progress).data if progress else None


class LessonListSerializer(_LessonStudentMixin, serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_title = serializers.CharField(source='chapter.title', read_only=True)
    is_unlocked = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'class_obj', 'class_name', 'subject', 'subject_name',
            'chapter', 'chapter_title', 'order', 'is_published', 'published_at',
            'is_unlocked', 'is_completed',
        ]


class AssignmentCorrectionSerializer(serializers.ModelSerializer):
    corrected_by_name = serializers.CharField(source='corrected_by.full_name', read_only=True)

    class Meta:
        model = AssignmentCorrection
        fields = [
            'id', 'submission', 'score', 'feedback', 'corrected_file',
            'corrected_by', 'corrected_by_name', 'corrected_at', 'is_active'
        ]
        read_only_fields = ['id', 'corrected_at']


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_matricule = serializers.CharField(source='student.matricule', read_only=True)
    correction = AssignmentCorrectionSerializer(read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = [
            'id', 'assignment', 'student', 'student_name', 'student_matricule',
            'content', 'file', 'submitted_at', 'status', 'is_late',
            'correction', 'is_active'
        ]
        read_only_fields = ['id', 'submitted_at', 'is_late']


class AssignmentSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.full_name', read_only=True)
    submission_count = serializers.IntegerField(read_only=True)
    submissions = AssignmentSubmissionSerializer(many=True, read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'id', 'title', 'description', 'instructions', 'class_obj', 'class_name',
            'subject', 'subject_name', 'teacher', 'teacher_name', 'lesson',
            'due_date', 'max_score', 'status', 'published_at',
            'allow_late_submission', 'late_penalty_percent', 'attachment',
            'submission_count', 'submissions', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'published_at', 'created_at']


class AssignmentListSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    submission_count = serializers.IntegerField(read_only=True)
    submission = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            'id', 'title', 'class_obj', 'class_name', 'subject', 'subject_name',
            'due_date', 'max_score', 'status', 'submission_count', 'submission'
        ]

    def get_submission(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'student_profile'):
            return None
        sub = obj.submissions.filter(student=request.user.student_profile).first()
        if not sub:
            return None
        correction = getattr(sub, 'correction', None)
        return {
            'id': str(sub.id),
            'status': sub.status,
            'submitted_at': sub.submitted_at,
            'is_late': sub.is_late,
            'content': sub.content,
            'file': sub.file.url if sub.file else None,
            'correction': {
                'score': correction.score,
                'feedback': correction.feedback,
                'corrected_file': correction.corrected_file.url if correction.corrected_file else None,
            } if correction else None,
        }


class CreateZoomMeetingSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    topic = serializers.CharField(max_length=255)
    start_time = serializers.DateTimeField()
    duration = serializers.IntegerField(default=60)


# ─────────────────────────────────────────────────────────────────────────────
# LOT 14 — Bibliothèque numérique
# ─────────────────────────────────────────────────────────────────────────────

class LibraryDocumentSerializer(serializers.ModelSerializer):
    subject_names = serializers.SerializerMethodField()
    doc_type_label = serializers.CharField(source='get_doc_type_display', read_only=True)
    is_favorite = serializers.SerializerMethodField()
    my_progress = serializers.SerializerMethodField()
    site_name = serializers.CharField(source='site.name', read_only=True, default=None)

    class Meta:
        model = LibraryDocument
        fields = [
            'id', 'title', 'authors', 'doc_type', 'doc_type_label',
            'year', 'isbn', 'doi', 'abstract', 'publisher', 'language',
            'pages', 'keywords', 'cover_image', 'file', 'external_url',
            'subjects', 'subject_names', 'site', 'site_name',
            'is_downloadable', 'is_online_readable', 'is_published',
            'download_count', 'view_count',
            'uploaded_by', 'is_favorite', 'my_progress',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'download_count', 'view_count', 'created_at']

    def get_subject_names(self, obj):
        return [s.name for s in obj.subjects.all()]

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return False
        return obj.favorites.filter(student=student).exists()

    def get_my_progress(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return None
        progress = obj.reading_progress.filter(student=student).first()
        return {'current_page': progress.current_page} if progress else None


class DocumentFavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentFavorite
        fields = ['id', 'student', 'document', 'created_at']
        read_only_fields = ['id', 'created_at']


class ReadingProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingProgress
        fields = ['id', 'student', 'document', 'current_page', 'last_read_at']
        read_only_fields = ['id', 'last_read_at']


# ─────────────────────────────────────────────────────────────────────────────
# LOT 12 — Examens sécurisés
# ─────────────────────────────────────────────────────────────────────────────

class SecureExamSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True, default=None)
    subject_name = serializers.CharField(source='subject.name', read_only=True, default=None)
    is_available = serializers.SerializerMethodField()
    exam_type_label = serializers.CharField(source='get_exam_type_display', read_only=True)
    exam_pdf = serializers.SerializerMethodField()
    my_session = serializers.SerializerMethodField()

    def to_internal_value(self, data):
        # When frontend sends subject_file as a string URL (existing file), strip it.
        # Actual file uploads arrive as InMemoryUploadedFile, not strings.
        if isinstance(data.get('subject_file'), str):
            data = data.copy() if hasattr(data, 'copy') else dict(data)
            data.pop('subject_file', None)
        return super().to_internal_value(data)

    class Meta:
        model = SecureExam
        fields = [
            'id', 'title', 'description',
            'class_obj', 'class_name', 'subject', 'subject_name',
            'quiz', 'exam_type', 'exam_type_label',
            'duration_minutes', 'start_date', 'end_date', 'max_attempts',
            'fullscreen_required', 'webcam_required', 'block_copy_paste',
            'max_tab_switches', 'require_student_photo', 'ai_proctoring',
            'is_published', 'pass_score_percent', 'coefficient',
            'max_score', 'subject_file', 'exam_pdf', 'pdf_extra_duration',
            'is_available', 'my_session', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'class_obj': {'required': False, 'allow_null': True},
            'subject':   {'required': False, 'allow_null': True},
            'title':     {'required': False, 'allow_blank': True, 'default': ''},
        }

    def get_is_available(self, obj):
        return obj.is_available()

    def get_exam_pdf(self, obj):
        if not obj.subject_file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.subject_file.url)
        return obj.subject_file.url

    def get_my_session(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'student_profile'):
            return None
        try:
            student = request.user.student_profile
            session = obj.sessions.filter(student=student).order_by('-started_at').first()
            if session:
                return {
                    'id': str(session.id),
                    'status': session.status,
                    'submitted_at': session.submitted_at,
                    'score': session.score,
                    'feedback': session.feedback,
                    'submission_file': request.build_absolute_uri(session.submission_file.url) if session.submission_file else None,
                    'corrected_file': request.build_absolute_uri(session.corrected_file.url) if session.corrected_file else None,
                }
        except Exception:
            pass
        return None


class ExamSessionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_matricule = serializers.CharField(source='student.matricule', read_only=True)

    class Meta:
        model = ExamSession
        fields = [
            'id', 'exam', 'student', 'student_name', 'student_matricule',
            'quiz_attempt', 'started_at', 'submitted_at', 'status',
            'time_remaining_seconds',
            'tab_switch_count', 'fullscreen_exit_count', 'copy_attempt_count', 'focus_lost_count',
            'is_flagged', 'flag_reason', 'events_log',
            # correction prof
            'score', 'feedback', 'corrected_file', 'corrected_by', 'corrected_at',
            # copie étudiant
            'submission_file', 'submission_note',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'started_at', 'created_at', 'events_log',
                            'tab_switch_count', 'fullscreen_exit_count',
                            'copy_attempt_count', 'focus_lost_count']


# ─────────────────────────────────────────────────────────────────────────────
# LOT 13 — Laboratoires virtuels
# ─────────────────────────────────────────────────────────────────────────────

class VirtualLabSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    lab_type_label = serializers.CharField(source='get_lab_type_display', read_only=True)
    submission_count = serializers.SerializerMethodField()
    my_submission = serializers.SerializerMethodField()

    class Meta:
        model = VirtualLab
        fields = [
            'id', 'title', 'description', 'instructions', 'objectives',
            'lab_type', 'lab_type_label',
            'class_obj', 'class_name', 'subject', 'subject_name', 'lesson',
            'access_url', 'embed_url', 'thumbnail',
            'duration_minutes', 'due_date', 'max_attempts', 'max_score',
            'is_published', 'order',
            'submission_count', 'my_submission',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_submission_count(self, obj):
        return obj.submissions.count()

    def get_my_submission(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return None
        sub = obj.submissions.filter(student=student).order_by('-started_at').first()
        if not sub:
            return None
        return {'id': str(sub.id), 'status': sub.status, 'score': sub.score}


class LabSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_matricule = serializers.CharField(source='student.matricule', read_only=True)
    lab_title = serializers.CharField(source='lab.title', read_only=True)

    class Meta:
        model = LabSubmission
        fields = [
            'id', 'lab', 'lab_title', 'student', 'student_name', 'student_matricule',
            'started_at', 'submitted_at', 'status',
            'report_text', 'report_file', 'screenshot',
            'score', 'feedback', 'graded_by', 'graded_at',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'started_at', 'created_at', 'graded_at']


# ─────────────────────────────────────────────────────────────────────────────
# LOTS 15/16/17 — IA pédagogique / IA Enseignant / Correction automatique
# ─────────────────────────────────────────────────────────────────────────────

class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = ['id', 'conversation', 'role', 'content', 'tokens_used', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at', 'tokens_used', 'metadata']


class AIConversationSerializer(serializers.ModelSerializer):
    messages = AIMessageSerializer(many=True, read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    conv_type_label = serializers.CharField(source='get_conv_type_display', read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = AIConversation
        fields = [
            'id', 'user', 'conv_type', 'conv_type_label', 'title',
            'subject', 'subject_name', 'lesson', 'lesson_title',
            'messages', 'message_count',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()


class AIConversationListSerializer(serializers.ModelSerializer):
    conv_type_label = serializers.CharField(source='get_conv_type_display', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = AIConversation
        fields = ['id', 'conv_type', 'conv_type_label', 'title', 'subject_name', 'message_count', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()


class AISendMessageSerializer(serializers.Serializer):
    content = serializers.CharField()


class AIGenerateSerializer(serializers.Serializer):
    GENERATE_TYPE_CHOICES = [
        'quiz', 'summary', 'flashcards', 'plan', 'slides', 'exam', 'rubric', 'feedback'
    ]
    generate_type = serializers.ChoiceField(choices=GENERATE_TYPE_CHOICES)
    prompt = serializers.CharField()
    lesson_id = serializers.UUIDField(required=False, allow_null=True)
    subject_id = serializers.UUIDField(required=False, allow_null=True)
    class_id = serializers.UUIDField(required=False, allow_null=True)
    options = serializers.DictField(required=False, default=dict)


class AIGradeSubmissionSerializer(serializers.Serializer):
    submission_id = serializers.UUIDField()
    grading_criteria = serializers.CharField(required=False, default='')
    max_score = serializers.FloatField(default=20)


# =============================================================================
# LOT 9 — VIDÉOTHÈQUE
# =============================================================================

class VideoSubtitleSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoSubtitle
        fields = ['id', 'language_code', 'language_label', 'file', 'file_url']

    def get_file_url(self, obj):
        req = self.context.get('request')
        return req.build_absolute_uri(obj.file.url) if req and obj.file else None


class VideoLibrarySerializer(serializers.ModelSerializer):
    subtitles       = VideoSubtitleSerializer(many=True, read_only=True)
    class_name      = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name    = serializers.CharField(source='subject.name', read_only=True)
    lesson_title    = serializers.CharField(source='lesson.title', read_only=True)
    video_url       = serializers.SerializerMethodField()
    thumbnail_url   = serializers.SerializerMethodField()
    my_progress     = serializers.SerializerMethodField()

    class Meta:
        model = VideoLibrary
        fields = [
            'id', 'title', 'description', 'thumbnail', 'thumbnail_url',
            'source_type', 'video_file', 'video_url', 'source_url',
            'duration_seconds', 'tags',
            'class_obj', 'class_name', 'subject', 'subject_name', 'lesson', 'lesson_title',
            'is_downloadable', 'token_lifetime_hours',
            'watermark_enabled', 'watermark_template', 'disable_right_click',
            'is_published', 'order', 'view_count',
            'subtitles', 'my_progress',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'view_count', 'created_at']

    def get_video_url(self, obj):
        req = self.context.get('request')
        if obj.source_type == 'FILE' and obj.video_file:
            return req.build_absolute_uri(obj.video_file.url) if req else obj.video_file.url
        return obj.source_url

    def get_thumbnail_url(self, obj):
        req = self.context.get('request')
        if obj.thumbnail:
            return req.build_absolute_uri(obj.thumbnail.url) if req else obj.thumbnail.url
        return None

    def get_my_progress(self, obj):
        req = self.context.get('request')
        if not req or not req.user.is_authenticated:
            return None
        try:
            from apps.students.models import Student
            student = Student.objects.get(user=req.user)
            prog = VideoProgress.objects.get(student=student, video=obj)
            return {
                'position_seconds': prog.position_seconds,
                'total_watched_seconds': prog.total_watched_seconds,
                'is_completed': prog.is_completed,
                'last_watched_at': prog.last_watched_at,
            }
        except Exception:
            return None


class VideoProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoProgress
        fields = ['id', 'video', 'position_seconds', 'total_watched_seconds', 'is_completed', 'last_watched_at']
        read_only_fields = ['id', 'last_watched_at']


# =============================================================================
# LOT 8 — CLASSES VIRTUELLES
# =============================================================================

class HandRaiseSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = HandRaise
        fields = ['id', 'student', 'student_name', 'raised_at', 'lowered_at', 'is_raised']

    def get_student_name(self, obj):
        return f"{obj.student.user.first_name} {obj.student.user.last_name}".strip()


class ClassroomChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = ClassroomChatMessage
        fields = ['id', 'user', 'sender_name', 'message', 'is_pinned', 'created_at']
        read_only_fields = ['id', 'created_at', 'user']

    def get_sender_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class PollResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollResponse
        fields = ['id', 'poll', 'student', 'selected_option']
        read_only_fields = ['id', 'student']


class ClassroomPollSerializer(serializers.ModelSerializer):
    results      = serializers.SerializerMethodField()
    total_votes  = serializers.SerializerMethodField()
    my_response  = serializers.SerializerMethodField()

    class Meta:
        model = ClassroomPoll
        fields = ['id', 'classroom', 'question', 'options', 'is_active', 'show_results',
                  'results', 'total_votes', 'my_response', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_results(self, obj):
        if not obj.show_results:
            return None
        return obj.results()

    def get_total_votes(self, obj):
        return obj.responses.count()

    def get_my_response(self, obj):
        req = self.context.get('request')
        if not req or not req.user.is_authenticated:
            return None
        try:
            from apps.students.models import Student
            student = Student.objects.get(user=req.user)
            resp = PollResponse.objects.get(poll=obj, student=student)
            return resp.selected_option
        except Exception:
            return None


class VirtualClassroomSerializer(serializers.ModelSerializer):
    class_name   = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    creator_name = serializers.SerializerMethodField()
    polls_count  = serializers.SerializerMethodField()
    jitsi_url    = serializers.SerializerMethodField()

    class Meta:
        model = VirtualClassroom
        fields = [
            'id', 'title', 'provider', 'class_obj', 'class_name', 'subject', 'subject_name', 'lesson',
            'start_time', 'duration_minutes',
            'join_url', 'host_url', 'meeting_id', 'password', 'jitsi_room_name', 'jitsi_url',
            'enable_recording', 'recording_url',
            'enable_whiteboard', 'enable_polls', 'enable_chat', 'enable_hand_raise', 'breakout_rooms',
            'transcript_text', 'ai_summary',
            'is_ended', 'ended_at',
            'created_by', 'creator_name', 'polls_count',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_by', 'is_ended', 'ended_at', 'ai_summary', 'created_at']

    def get_creator_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None

    def get_polls_count(self, obj):
        return obj.polls.filter(is_active=True).count()

    def get_jitsi_url(self, obj):
        if obj.provider != 'JITSI':
            return None
        return obj.get_jitsi_url()


class MeetingSegmentSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.ReadOnlyField()
    participants_count = serializers.SerializerMethodField()

    class Meta:
        model = MeetingSegment
        fields = [
            'id', 'virtual_class', 'sequence', 'meeting_url', 'meeting_id',
            'start_time', 'end_time', 'status', 'started_at', 'ended_at',
            'duration_minutes', 'participants_count', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'started_at', 'ended_at', 'created_at']

    def get_participants_count(self, obj):
        return obj.participants.count()


class SessionParticipantSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    matricule    = serializers.CharField(source='student.matricule', read_only=True)

    class Meta:
        model = SessionParticipant
        fields = ['id', 'segment', 'student', 'student_name', 'matricule',
                  'joined_at', 'left_at', 'attendance_duration', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_student_name(self, obj):
        u = obj.student.user
        return f"{u.first_name} {u.last_name}".strip() or u.email


class SessionLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = SessionLog
        fields = ['id', 'virtual_class', 'segment', 'log_type', 'actor', 'actor_name', 'detail', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_actor_name(self, obj):
        if obj.actor:
            return f"{obj.actor.first_name} {obj.actor.last_name}".strip() or obj.actor.email
        return None


class VirtualClassroomDetailSerializer(VirtualClassroomSerializer):
    """Extended serializer that includes segments."""
    segments = MeetingSegmentSerializer(many=True, read_only=True)

    class Meta(VirtualClassroomSerializer.Meta):
        fields = VirtualClassroomSerializer.Meta.fields + ['segments']


class AITranscriptSerializer(serializers.Serializer):
    transcript = serializers.CharField()
    classroom_id = serializers.UUIDField()


# ── Cours autonomes ──────────────────────────────────────────────────────────

class CourseLessonSerializer(serializers.ModelSerializer):
    has_media = serializers.BooleanField(read_only=True)

    class Meta:
        model = CourseLesson
        fields = [
            'id', 'chapter', 'title', 'content_type', 'duration_seconds',
            'is_preview_free', 'download_allowed', 'text_content',
            'external_embed_url', 'video_file', 'document_file',
            'has_media', 'order', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'has_media', 'created_at']


class CourseChapterSerializer(serializers.ModelSerializer):
    lessons = CourseLessonSerializer(many=True, read_only=True)

    class Meta:
        model = CourseChapter
        fields = ['id', 'section', 'title', 'description', 'order', 'lessons', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class CourseSectionSerializer(serializers.ModelSerializer):
    chapters = CourseChapterSerializer(many=True, read_only=True)

    class Meta:
        model = CourseSection
        fields = ['id', 'course', 'title', 'order', 'chapters', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class CourseSerializer(serializers.ModelSerializer):
    sections       = CourseSectionSerializer(many=True, read_only=True)
    instructor_name = serializers.SerializerMethodField()
    thumbnail_url  = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'site', 'instructor', 'instructor_name',
            'quiz',
            'title', 'subtitle', 'description', 'thumbnail', 'thumbnail_url',
            'level', 'language', 'status',
            'price', 'is_free', 'certificate_enabled',
            'target_audience', 'requirements', 'what_you_will_learn',
            'video_url',
            'total_students', 'average_rating',
            'sections', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'total_students', 'average_rating', 'created_at', 'updated_at']

    def get_instructor_name(self, obj):
        if obj.instructor:
            return f"{obj.instructor.first_name} {obj.instructor.last_name}".strip() or obj.instructor.email
        return None

    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None


class CourseListSerializer(serializers.ModelSerializer):
    instructor_name = serializers.SerializerMethodField()
    thumbnail_url   = serializers.SerializerMethodField()
    section_count   = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'subtitle', 'thumbnail_url', 'level', 'status',
            'price', 'is_free', 'average_rating', 'total_students',
            'instructor', 'instructor_name', 'section_count',
            'quiz', 'video_url',
            'certificate_enabled', 'is_active', 'created_at',
        ]

    def get_instructor_name(self, obj):
        if obj.instructor:
            return f"{obj.instructor.first_name} {obj.instructor.last_name}".strip() or obj.instructor.email
        return None

    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None

    def get_section_count(self, obj):
        return obj.sections.filter(is_active=True).count()
