from django.db.models import Q, Count, Avg
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

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
    ExamSnapshot,
    Course, CourseSection, CourseChapter, CourseLesson,
    mention_for_percent,
)
from .serializers import (
    ZoomMeetingSerializer, LessonSerializer, LessonListSerializer,
    LessonAttachmentSerializer, ChapterSerializer, LessonProgressSerializer,
    QuizSerializer, QuizListSerializer, QuizTakeSerializer,
    QuestionSerializer, ChoiceSerializer,
    AttemptAnswerSubmitSerializer, QuizAttemptSerializer,
    AssignmentSerializer, AssignmentListSerializer,
    AssignmentSubmissionSerializer, AssignmentCorrectionSerializer,
    CreateZoomMeetingSerializer,
    LibraryDocumentSerializer, DocumentFavoriteSerializer, ReadingProgressSerializer,
    SecureExamSerializer, ExamSessionSerializer, ExamSnapshotSerializer,
    VirtualLabSerializer, LabSubmissionSerializer,
    AIConversationSerializer, AIConversationListSerializer, AIMessageSerializer,
    AISendMessageSerializer, AIGenerateSerializer, AIGradeSubmissionSerializer,
    VideoLibrarySerializer, VideoSubtitleSerializer, VideoProgressSerializer,
    VirtualClassroomSerializer, VirtualClassroomDetailSerializer,
    ClassroomPollSerializer, PollResponseSerializer,
    ClassroomChatMessageSerializer, HandRaiseSerializer, AITranscriptSerializer,
    MeetingSegmentSerializer, SessionParticipantSerializer, SessionLogSerializer,
    CourseSerializer, CourseListSerializer,
    CourseSectionSerializer, CourseChapterSerializer, CourseLessonSerializer,
)
from .services import ZoomService
from apps.academic.models import Session


class TeacherScopedContentMixin:
    """Restricts Lesson/Quiz/Assignment list/retrieve/create/update to the
    class+subject pairs the requesting user actually teaches (ClassSubjectTeacher,
    is_active), when that user is a TEACHER. Admins/staff and non-teacher
    requesters (students, parents) are completely unaffected — these viewsets
    previously had no scoping at all and were only ever reached through
    admin-only frontend routes, so this only activates once a real teacher
    request comes in (e.g. from the new teacher-facing e-learning pages).
    """
    def _teacher_profile(self):
        user = self.request.user
        if getattr(user, 'user_type', None) in ('ADMIN', 'STAFF'):
            return None
        return getattr(user, 'teacher_profile', None)

    def get_queryset(self):
        qs = super().get_queryset()
        teacher = self._teacher_profile()
        if not teacher:
            return qs
        pairs = teacher.class_subjects.filter(is_active=True).values_list('class_obj_id', 'subject_id')
        if not pairs:
            return qs.none()
        scope = Q()
        for class_id, subject_id in pairs:
            scope |= Q(class_obj_id=class_id, subject_id=subject_id)
        return qs.filter(scope)

    def _check_teacher_scope(self, serializer):
        teacher = self._teacher_profile()
        if not teacher:
            return None
        instance = getattr(serializer, 'instance', None)
        class_obj = serializer.validated_data.get('class_obj') or (instance.class_obj if instance else None)
        subject = serializer.validated_data.get('subject') or (instance.subject if instance else None)
        if not teacher.class_subjects.filter(class_obj=class_obj, subject=subject, is_active=True).exists():
            raise PermissionDenied("Vous n'enseignez pas cette matière pour cette classe.")
        return teacher

    def perform_create(self, serializer):
        teacher = self._check_teacher_scope(serializer)
        if teacher is not None and 'teacher' in serializer.fields:
            serializer.save(teacher=teacher)
        else:
            serializer.save()

    def perform_update(self, serializer):
        self._check_teacher_scope(serializer)
        serializer.save()


class InstructorScopedCourseMixin:
    """Restricts Course (and its nested Section/Chapter/Lesson) to courses
    authored by the requesting teacher. Course.instructor is a plain User FK
    — a "cours autonome" isn't tied to one class+subject like Lesson/Quiz/
    Assignment/SecureExam/VirtualLab are — so this needs its own simpler
    scoping instead of TeacherScopedContentMixin. Admins/staff and non-teacher
    requesters are unaffected.
    """
    instructor_lookup = 'instructor'

    def _is_teacher_request(self):
        user = self.request.user
        if getattr(user, 'user_type', None) in ('ADMIN', 'STAFF'):
            return False
        return hasattr(user, 'teacher_profile')

    def get_queryset(self):
        qs = super().get_queryset()
        if not self._is_teacher_request():
            return qs
        return qs.filter(**{self.instructor_lookup: self.request.user})


class ZoomMeetingViewSet(viewsets.ModelViewSet):
    queryset = ZoomMeeting.objects.select_related('session', 'host', 'created_by').all()
    serializer_class = ZoomMeetingSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['start_time']
    filterset_fields = ['session', 'host', 'is_recorded', 'is_active']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CreateZoomMeetingView(APIView):
    def post(self, request):
        serializer = CreateZoomMeetingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        try:
            session = Session.objects.get(id=data['session_id'])
        except Session.DoesNotExist:
            return Response(
                {'detail': 'Séance non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        zoom_service = ZoomService()
        result = zoom_service.create_meeting(
            topic=data['topic'],
            start_time=data['start_time'],
            duration=data['duration']
        )
        
        if result['success']:
            meeting = ZoomMeeting.objects.create(
                session=session,
                meeting_id=result['meeting_id'],
                topic=data['topic'],
                start_time=data['start_time'],
                duration=data['duration'],
                join_url=result['join_url'],
                start_url=result['start_url'],
                password=result['password'],
                host=request.user,
                created_by=request.user
            )
            return Response(
                ZoomMeetingSerializer(meeting).data,
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {'detail': result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )


class LessonViewSet(TeacherScopedContentMixin, viewsets.ModelViewSet):
    queryset = Lesson.objects.select_related(
        'class_obj', 'subject', 'teacher__user', 'chapter', 'zoom_meeting'
    ).prefetch_related('attachments').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['order', 'created_at', 'published_at']
    filterset_fields = ['class_obj', 'subject', 'teacher', 'chapter', 'is_published', 'is_active']

    def get_serializer_class(self):
        if self.action == 'list':
            return LessonListSerializer
        return LessonSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Pre-fetch this student's completed-lesson IDs once for the whole list
        # instead of LessonListSerializer hitting progress_records per row.
        if self.action == 'list':
            student = getattr(self.request.user, 'student_profile', None)
            if student:
                context['completed_lesson_ids'] = set(
                    LessonProgress.objects.filter(
                        student=student, is_completed=True
                    ).values_list('lesson_id', flat=True)
                )
        return context

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        lesson = self.get_object()
        lesson.publish()
        return Response(LessonSerializer(lesson, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='add-attachment')
    def add_attachment(self, request, pk=None):
        lesson = self.get_object()
        serializer = LessonAttachmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lesson=lesson)
        return Response(LessonSerializer(lesson, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='track-progress')
    def track_progress(self, request, pk=None):
        """Student reports viewing progress on a lesson; re-evaluates completion gates."""
        lesson = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({'detail': 'Profil étudiant requis'}, status=status.HTTP_400_BAD_REQUEST)

        if not lesson.is_unlocked_for(student):
            return Response({'detail': 'Cette leçon est verrouillée'}, status=status.HTTP_403_FORBIDDEN)

        from django.utils import timezone
        progress, created = LessonProgress.objects.get_or_create(
            student=student, lesson=lesson,
            defaults={'started_at': timezone.now()}
        )
        if created or not progress.started_at:
            progress.started_at = timezone.now()

        watch_percent = request.data.get('watch_percent')
        time_spent_seconds = request.data.get('time_spent_seconds')
        if watch_percent is not None:
            progress.watch_percent = max(progress.watch_percent, min(100, int(watch_percent)))
        if time_spent_seconds is not None:
            progress.time_spent_seconds = max(progress.time_spent_seconds, int(time_spent_seconds))
        progress.save()
        progress.evaluate_completion()

        return Response(LessonProgressSerializer(progress).data)

    @action(detail=False, methods=['get'], url_path='progress-overview')
    def progress_overview(self, request):
        """Lots 7 & 10 — Admin view: per-lesson completion stats for a class+subject."""
        class_id   = request.query_params.get('class_obj')
        subject_id = request.query_params.get('subject')
        if not class_id or not subject_id:
            return Response({'detail': 'class_obj et subject requis'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.students.models import Student
        lessons = Lesson.objects.filter(
            class_obj_id=class_id, subject_id=subject_id, is_active=True, is_published=True
        ).order_by('order').select_related('chapter')

        students_qs = Student.objects.filter(current_class_id=class_id, is_active=True).select_related('user')
        total_students = students_qs.count()

        result = []
        for lesson in lessons:
            completions = LessonProgress.objects.filter(lesson=lesson, is_completed=True).count()
            started     = LessonProgress.objects.filter(lesson=lesson).exclude(started_at=None).count()
            avg_pct     = LessonProgress.objects.filter(lesson=lesson).aggregate(a=Avg('watch_percent'))['a'] or 0
            result.append({
                'lesson_id':     str(lesson.id),
                'title':         lesson.title,
                'chapter_title': lesson.chapter.title if lesson.chapter else None,
                'order':         lesson.order,
                'total_students': total_students,
                'started':       started,
                'completed':     completions,
                'completion_rate': round(completions / total_students * 100, 1) if total_students else 0,
                'avg_watch_percent': round(float(avg_pct), 1),
            })

        # Per-student overview
        student_overview = []
        for st in students_qs:
            done = LessonProgress.objects.filter(student=st, lesson__in=lessons, is_completed=True).count()
            student_overview.append({
                'matricule':    st.matricule,
                'name':         f"{st.user.first_name} {st.user.last_name}".strip(),
                'completed':    done,
                'total':        lessons.count(),
                'percent':      round(done / lessons.count() * 100, 1) if lessons.count() else 0,
            })

        return Response({
            'lessons': result,
            'students': sorted(student_overview, key=lambda x: -x['percent']),
            'total_lessons': lessons.count(),
            'total_students': total_students,
        })

    @action(detail=False, methods=['get'], url_path='my-completed')
    def my_completed(self, request):
        """Return lesson IDs completed by the current student."""
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response([])
        ids = LessonProgress.objects.filter(
            student=student, is_completed=True
        ).values_list('lesson_id', flat=True)
        return Response(list(ids))

    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None):
        """Manual completion for non-trackable lessons (text/pdf/file)."""
        lesson = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({'detail': 'Profil étudiant requis'}, status=status.HTTP_400_BAD_REQUEST)
        if not lesson.is_unlocked_for(student):
            return Response({'detail': 'Cette leçon est verrouillée'}, status=status.HTTP_403_FORBIDDEN)

        from django.utils import timezone
        progress, _ = LessonProgress.objects.get_or_create(
            student=student, lesson=lesson,
            defaults={'started_at': timezone.now()}
        )
        # Only auto-satisfy the watch gate for lessons with no trackable media —
        # video/audio lessons must reach min_watch_percent via real playback.
        has_media = lesson.attachments.filter(block_type__in=['VIDEO', 'AUDIO'], is_active=True).exists()
        if not has_media and lesson.min_watch_percent > 0:
            progress.watch_percent = 100
        progress.save()
        progress.evaluate_completion()
        return Response(LessonProgressSerializer(progress).data)


class ChapterViewSet(viewsets.ModelViewSet):
    queryset = Chapter.objects.select_related('class_obj', 'subject').prefetch_related('lessons').all()
    serializer_class = ChapterSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['order', 'created_at']
    filterset_fields = ['class_obj', 'subject', 'is_published', 'is_active']


class LearningPathView(APIView):
    """Structured Programme → Chapitre → Leçon view with per-student lock state."""

    def get(self, request):
        class_obj_id = request.query_params.get('class_obj')
        subject_id = request.query_params.get('subject')
        if not class_obj_id or not subject_id:
            return Response(
                {'detail': 'class_obj et subject sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        student = getattr(request.user, 'student_profile', None)

        chapters = Chapter.objects.filter(
            class_obj_id=class_obj_id, subject_id=subject_id, is_active=True, is_published=True
        ).order_by('order').prefetch_related('lessons')

        def serialize_lesson(lesson):
            data = LessonListSerializer(lesson, context={'request': request}).data
            return data

        chapters_data = []
        for chapter in chapters:
            lessons = chapter.lessons.filter(is_active=True, is_published=True).order_by('order')
            chapters_data.append({
                'id': str(chapter.id),
                'title': chapter.title,
                'description': chapter.description,
                'order': chapter.order,
                'is_unlocked': chapter.is_unlocked_for(student) if student else True,
                'is_completed': chapter.is_completed_by(student) if student else False,
                'lessons': [serialize_lesson(l) for l in lessons],
            })

        ungrouped = Lesson.objects.filter(
            class_obj_id=class_obj_id, subject_id=subject_id, chapter__isnull=True,
            is_active=True, is_published=True
        ).order_by('order')

        return Response({
            'chapters': chapters_data,
            'ungrouped_lessons': [serialize_lesson(l) for l in ungrouped],
        })


class LessonAttachmentViewSet(viewsets.ModelViewSet):
    queryset = LessonAttachment.objects.select_related('lesson').all()
    serializer_class = LessonAttachmentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['order', 'created_at']
    filterset_fields = ['lesson', 'block_type', 'is_active']

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Bulk-update block order after a drag&drop reorder.
        Body: { "blocks": [{"id": "<uuid>", "order": 0}, ...] }
        """
        blocks = request.data.get('blocks', [])
        ids = [b['id'] for b in blocks]
        existing = {
            str(a.id): a for a in
            LessonAttachment.objects.filter(id__in=ids)
        }
        updated = []
        for b in blocks:
            attachment = existing.get(str(b['id']))
            if attachment:
                attachment.order = b['order']
                updated.append(attachment)
        LessonAttachment.objects.bulk_update(updated, ['order'])
        return Response({'updated': len(updated)})


class QuizViewSet(TeacherScopedContentMixin, viewsets.ModelViewSet):
    queryset = Quiz.objects.select_related('class_obj', 'subject', 'lesson').prefetch_related('questions__choices').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description']
    filterset_fields = ['class_obj', 'subject', 'lesson', 'is_published', 'is_active']
    # A student behind on their tuition échéancier can't start a quiz attempt
    # (browsing the quiz itself is unaffected — see apps.elearning.permissions).
    tuition_gate_actions = ('start_attempt',)

    def get_serializer_class(self):
        if self.action == 'list':
            return QuizListSerializer
        return QuizSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Pre-fetch this student's attempts once for the whole list instead of
        # QuizListSerializer hitting the DB twice per quiz (attempts_used, best_score).
        if self.action == 'list':
            student = getattr(self.request.user, 'student_profile', None)
            if student:
                attempts_by_quiz = {}
                for a in QuizAttempt.objects.filter(student=student):
                    attempts_by_quiz.setdefault(a.quiz_id, []).append(a)
                context['my_attempts_by_quiz'] = attempts_by_quiz
        return context

    @action(detail=True, methods=['get'])
    def take(self, request, pk=None):
        """Sanitized quiz (no correct answers) for a student about to attempt it."""
        quiz = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        attempts_used = quiz.attempts.filter(student=student).count() if student else 0
        if quiz.max_attempts and attempts_used >= quiz.max_attempts:
            return Response({'detail': 'Nombre maximum de tentatives atteint'}, status=status.HTTP_403_FORBIDDEN)
        data = QuizTakeSerializer(quiz).data
        if quiz.shuffle_questions:
            import random
            random.shuffle(data['questions'])
        data['attempts_used'] = attempts_used
        return Response(data)

    @action(detail=True, methods=['post'], url_path='start-attempt')
    def start_attempt(self, request, pk=None):
        quiz = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({'detail': 'Profil étudiant requis'}, status=status.HTTP_400_BAD_REQUEST)

        # Resume existing in-progress attempt (not yet submitted) instead of creating a new one
        in_progress = quiz.attempts.filter(student=student, submitted_at__isnull=True).first()
        if in_progress:
            return Response(QuizAttemptSerializer(in_progress).data, status=status.HTTP_200_OK)

        # Only count submitted attempts toward the limit
        attempts_used = quiz.attempts.filter(student=student, submitted_at__isnull=False).count()
        if quiz.max_attempts and attempts_used >= quiz.max_attempts:
            return Response({'detail': 'Nombre maximum de tentatives atteint'}, status=status.HTTP_403_FORBIDDEN)

        if quiz.lesson_id and not quiz.lesson.is_unlocked_for(student):
            return Response({'detail': 'Ce quiz est verrouillé'}, status=status.HTTP_403_FORBIDDEN)

        attempt = QuizAttempt.objects.create(quiz=quiz, student=student, max_score=quiz.max_score)
        return Response(QuizAttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='my-attempts')
    def my_attempts(self, request, pk=None):
        quiz = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response([])
        attempts = quiz.attempts.filter(student=student).order_by('-started_at')
        return Response(QuizAttemptSerializer(attempts, many=True).data)

    @action(detail=True, methods=['get'], url_path='analytics')
    def analytics(self, request, pk=None):
        """Lot 11 — Admin quiz analytics: per-question stats, pass rate, rankings."""
        from decimal import Decimal
        quiz = self.get_object()
        attempts = quiz.attempts.filter(submitted_at__isnull=False).select_related('student__user').prefetch_related('answers__question', 'answers__selected_choices')

        total = attempts.count()
        passed = attempts.filter(is_passed=True).count()
        avg_score = attempts.aggregate(avg=Avg('percent'))['avg'] or 0

        # Per-question stats — one aggregated query for all questions instead
        # of 3 queries (total/correct/pending) per question in a loop.
        answer_stats = AttemptAnswer.objects.filter(
            question__quiz=quiz, attempt__submitted_at__isnull=False
        ).values('question_id').annotate(
            total=Count('id'),
            correct=Count('id', filter=Q(is_correct=True)),
            pending=Count('id', filter=Q(is_correct__isnull=True)),
        )
        stats_by_question = {row['question_id']: row for row in answer_stats}

        questions_stats = []
        for q in quiz.questions.filter(is_active=True).order_by('order'):
            row = stats_by_question.get(q.id, {'total': 0, 'correct': 0, 'pending': 0})
            q_total, q_correct, q_pending = row['total'], row['correct'], row['pending']
            questions_stats.append({
                'id': str(q.id),
                'text': q.text[:100],
                'question_type': q.question_type,
                'points': float(q.points),
                'total_answers': q_total,
                'correct': q_correct,
                'incorrect': q_total - q_correct - q_pending,
                'pending': q_pending,
                'success_rate': round(q_correct / q_total * 100, 1) if q_total else 0,
            })

        # Per-student results
        student_results = []
        for att in attempts.order_by('-percent')[:50]:
            student_results.append({
                'student_name': f"{att.student.user.first_name} {att.student.user.last_name}".strip(),
                'matricule': att.student.matricule,
                'score': float(att.score),
                'percent': float(att.percent),
                'is_passed': att.is_passed,
                'is_graded': att.is_graded,
                'submitted_at': att.submitted_at,
                'attempt_id': str(att.id),
            })

        # Ungraded TEXT answers
        ungraded = AttemptAnswer.objects.filter(
            question__quiz=quiz, is_correct__isnull=True, question__question_type='TEXT',
            attempt__submitted_at__isnull=False
        ).select_related('attempt__student__user', 'question').order_by('-attempt__submitted_at')[:30]
        ungraded_data = [{
            'id': str(a.id),
            'attempt_id': str(a.attempt_id),
            'student_name': f"{a.attempt.student.user.first_name} {a.attempt.student.user.last_name}".strip(),
            'question_text': a.question.text[:200],
            'question_id': str(a.question_id),
            'max_points': float(a.question.points),
            'response': a.text_response,
            'expected': a.question.text_answer,
        } for a in ungraded]

        return Response({
            'total_attempts': total,
            'passed': passed,
            'pass_rate': round(passed / total * 100, 1) if total else 0,
            'average_score': round(float(avg_score), 1),
            'questions': questions_stats,
            'student_results': student_results,
            'ungraded_count': ungraded.count() if hasattr(ungraded, 'count') else len(ungraded_data),
            'ungraded': ungraded_data,
        })

    @action(detail=True, methods=['post'], url_path='ai-generate')
    def ai_generate(self, request, pk=None):
        """Lot 11 — Generate quiz questions with AI."""
        from .ai_service import _call_claude
        import json as _json
        quiz = self.get_object()
        topic   = request.data.get('topic', quiz.title)
        count   = min(int(request.data.get('count', 5)), 20)
        q_type  = request.data.get('question_type', 'QCU')
        level   = request.data.get('level', 'moyen')

        system = (
            "Tu es un générateur de quiz pédagogique. Génère des questions en JSON valide UNIQUEMENT, "
            "sans texte autour. Format: [{\"text\": \"...\", \"explanation\": \"...\", \"points\": 1, "
            "\"choices\": [{\"text\": \"...\", \"is_correct\": false}, ...]}]. "
            "Pour QCU: 4 choix dont 1 correct. Pour QCM: 4 choix dont 2+ corrects. "
            "Pour TEXT: pas de choices, ajouter \"text_answer\": \"réponse\". "
            "Pour NUMERIC: pas de choices, ajouter \"numeric_answer\": 42. "
        )
        messages = [{
            "role": "user",
            "content": f"Génère {count} questions de type {q_type} niveau {level} sur le sujet: {topic}. Matière: {quiz.subject_name if hasattr(quiz, 'subject_name') else ''}. Langue: français."
        }]

        raw, tokens = _call_claude(system, messages, max_tokens=3000)

        # Extract JSON array from response
        try:
            match = __import__('re').search(r'\[.*\]', raw, __import__('re').DOTALL)
            items = _json.loads(match.group()) if match else []
        except Exception:
            return Response({'detail': 'Erreur de parsing IA', 'raw': raw}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        created_questions = []
        for i, item in enumerate(items):
            q_data = {
                'quiz': quiz.id,
                'question_type': q_type,
                'text': item.get('text', ''),
                'points': item.get('points', 1),
                'explanation': item.get('explanation', ''),
                'order': quiz.questions.count() + i,
            }
            if q_type == 'TEXT':
                q_data['text_answer'] = item.get('text_answer', '')
            elif q_type == 'NUMERIC':
                q_data['numeric_answer'] = item.get('numeric_answer')

            from .serializers import QuestionSerializer as QS
            ser = QS(data=q_data)
            if ser.is_valid():
                question = ser.save()
                # Create choices
                for c in item.get('choices', []):
                    Choice.objects.create(
                        question=question,
                        text=c.get('text', ''),
                        is_correct=c.get('is_correct', False),
                        order=0
                    )
                created_questions.append(question)

        return Response({
            'created': len(created_questions),
            'tokens_used': tokens,
            'message': f'{len(created_questions)} question(s) générée(s) par IA'
        })


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.select_related('quiz').prefetch_related('choices').all()
    serializer_class = QuestionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['order']
    filterset_fields = ['quiz', 'quiz__subject', 'question_type', 'is_active']


class ChoiceViewSet(viewsets.ModelViewSet):
    queryset = Choice.objects.select_related('question').all()
    serializer_class = ChoiceSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['order']
    filterset_fields = ['question', 'is_active']


class QuizAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = QuizAttempt.objects.select_related('quiz', 'student__user').prefetch_related('answers__question').all()
    serializer_class = QuizAttemptSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['started_at']
    filterset_fields = ['quiz', 'student', 'is_passed', 'is_graded']
    tuition_gate_actions = ('submit',)

    @action(detail=True, methods=['post'], url_path='grade-text')
    def grade_text(self, request, pk=None):
        """Lot 11 — Manually grade a TEXT answer."""
        attempt = self.get_object()
        answer_id  = request.data.get('answer_id')
        is_correct = request.data.get('is_correct', False)
        points     = request.data.get('points_earned', None)
        feedback   = request.data.get('feedback', '')
        try:
            answer = AttemptAnswer.objects.get(id=answer_id, attempt=attempt)
        except AttemptAnswer.DoesNotExist:
            return Response({'detail': 'Réponse introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        from decimal import Decimal
        answer.is_correct     = is_correct
        answer.points_earned  = Decimal(str(points)) if points is not None else (answer.question.points if is_correct else Decimal('0'))
        answer.manual_feedback = feedback
        answer.save()
        attempt.finalize()
        return Response({'status': 'graded', 'attempt_percent': float(attempt.percent), 'is_passed': attempt.is_passed})

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Grade every submitted answer, finalize the attempt, and re-evaluate
        lesson completion if this quiz gates a lesson (requires_quiz)."""
        attempt = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student or attempt.student_id != student.id:
            return Response({'detail': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        if attempt.submitted_at:
            return Response({'detail': 'Cette tentative a déjà été soumise'}, status=status.HTTP_400_BAD_REQUEST)

        raw_answers = request.data.get('answers', [])
        for raw in raw_answers:
            ser = AttemptAnswerSubmitSerializer(data=raw)
            ser.is_valid(raise_exception=True)
            d = ser.validated_data
            try:
                question = attempt.quiz.questions.get(id=d['question_id'])
            except Question.DoesNotExist:
                continue

            answer, _ = AttemptAnswer.objects.update_or_create(
                attempt=attempt, question=question,
                defaults={
                    'text_response': d.get('text_response', ''),
                    'numeric_response': d.get('numeric_response'),
                    'ordering_response': d.get('ordering_response', []),
                    'matching_response': d.get('matching_response', {}),
                }
            )
            if d.get('choice_ids'):
                answer.selected_choices.set(d['choice_ids'])
            else:
                answer.selected_choices.clear()
            answer.grade()

        attempt.finalize()

        if attempt.quiz.lesson_id:
            progress = LessonProgress.objects.filter(student=student, lesson_id=attempt.quiz.lesson_id).first()
            if progress:
                progress.evaluate_completion()

        # Keep the linked secure-exam session in sync — without this, ExamSession.status
        # never leaves STARTED, so "completed exams" lists never show it and the
        # anti-cheat auto-submit never actually closes the session.
        try:
            exam_session = attempt.exam_session
        except ExamSession.DoesNotExist:
            exam_session = None
        if exam_session and exam_session.status == 'STARTED':
            from django.utils import timezone as tz
            exam_session.status = 'SUBMITTED'
            exam_session.submitted_at = exam_session.submitted_at or tz.now()
            exam_session.save(update_fields=['status', 'submitted_at'])
            exam_session.check_webcam_integrity()

        # Re-fetch from DB so serializer gets fresh graded answers (not stale prefetch)
        fresh = QuizAttempt.objects.prefetch_related(
            'answers__question', 'answers__selected_choices'
        ).get(pk=attempt.pk)
        return Response(QuizAttemptSerializer(fresh).data)


class AssignmentViewSet(TeacherScopedContentMixin, viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related(
        'class_obj', 'subject', 'teacher__user', 'lesson'
    ).prefetch_related('submissions', 'submissions__correction').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'created_at']
    filterset_fields = ['class_obj', 'subject', 'teacher', 'status', 'is_active']

    def get_serializer_class(self):
        if self.action == 'list':
            return AssignmentListSerializer
        return AssignmentSerializer

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        assignment = self.get_object()
        assignment.publish()
        return Response(AssignmentSerializer(assignment).data)

    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        assignment = self.get_object()
        submissions = assignment.submissions.select_related('student__user')
        serializer = AssignmentSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)


class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    queryset = AssignmentSubmission.objects.select_related(
        'assignment', 'student__user'
    ).all()
    serializer_class = AssignmentSubmissionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['submitted_at']
    filterset_fields = ['assignment', 'student', 'status', 'is_late', 'is_active']
    tuition_gate_actions = ('create',)


class SubmitAssignmentView(APIView):
    tuition_gate_required = True

    def post(self, request, assignment_id):
        from apps.students.models import Student
        
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response(
                {'detail': 'Devoir non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if assignment.status != 'PUBLISHED':
            return Response(
                {'detail': 'Ce devoir n\'est pas ouvert aux soumissions'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = request.user.student_profile
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Profil étudiant non trouvé'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if AssignmentSubmission.objects.filter(assignment=assignment, student=student).exists():
            return Response(
                {'detail': 'Vous avez déjà soumis ce devoir'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student,
            content=request.data.get('content', ''),
            file=request.FILES.get('file')
        )
        
        return Response(
            AssignmentSubmissionSerializer(submission).data,
            status=status.HTTP_201_CREATED
        )


class CorrectSubmissionView(APIView):
    def post(self, request, submission_id):
        try:
            submission = AssignmentSubmission.objects.get(id=submission_id)
        except AssignmentSubmission.DoesNotExist:
            return Response(
                {'detail': 'Soumission non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if hasattr(submission, 'correction'):
            return Response(
                {'detail': 'Cette soumission a déjà été corrigée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        score = request.data.get('score')
        if score is None:
            return Response(
                {'detail': 'La note est requise'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        correction = AssignmentCorrection.objects.create(
            submission=submission,
            score=score,
            feedback=request.data.get('feedback', ''),
            corrected_file=request.FILES.get('corrected_file'),
            corrected_by=request.user
        )
        
        return Response(
            AssignmentCorrectionSerializer(correction).data,
            status=status.HTTP_201_CREATED
        )


# ─────────────────────────────────────────────────────────────────────────────
# LOT 14 — Bibliothèque numérique
# ─────────────────────────────────────────────────────────────────────────────

class LibraryDocumentViewSet(viewsets.ModelViewSet):
    queryset = LibraryDocument.objects.prefetch_related('subjects', 'favorites').all()
    serializer_class = LibraryDocumentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'authors', 'abstract', 'keywords', 'isbn', 'doi']
    ordering_fields = ['title', 'year', 'download_count', 'view_count', 'created_at']
    filterset_fields = ['doc_type', 'language', 'is_downloadable', 'is_online_readable', 'is_published', 'is_active', 'site']

    def get_queryset(self):
        qs = LibraryDocument.objects.prefetch_related('subjects', 'favorites').all()
        user = self.request.user
        # Non-admin users only see documents shared with all sites (site=null)
        # or rattached to their own site — never another site's library.
        if user.is_authenticated and not (user.is_staff or user.is_superuser) and user.site_id:
            qs = qs.filter(Q(site__isnull=True) | Q(site_id=user.site_id))
        return qs

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        doc = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({'detail': 'Profil étudiant requis'}, status=status.HTTP_400_BAD_REQUEST)
        fav, created = DocumentFavorite.objects.get_or_create(student=student, document=doc)
        if not created:
            fav.delete()
            return Response({'is_favorite': False})
        return Response({'is_favorite': True})

    @action(detail=True, methods=['post'], url_path='track-view')
    def track_view(self, request, pk=None):
        doc = self.get_object()
        LibraryDocument.objects.filter(pk=doc.pk).update(view_count=doc.view_count + 1)
        return Response({'view_count': doc.view_count + 1})

    @action(detail=True, methods=['post'], url_path='track-download')
    def track_download(self, request, pk=None):
        doc = self.get_object()
        LibraryDocument.objects.filter(pk=doc.pk).update(download_count=doc.download_count + 1)
        return Response({'download_count': doc.download_count + 1})

    @action(detail=True, methods=['post'], url_path='save-progress')
    def save_progress(self, request, pk=None):
        doc = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({'detail': 'Profil étudiant requis'}, status=status.HTTP_400_BAD_REQUEST)
        page = request.data.get('current_page', 1)
        progress, _ = ReadingProgress.objects.update_or_create(
            student=student, document=doc,
            defaults={'current_page': max(1, int(page))}
        )
        return Response(ReadingProgressSerializer(progress).data)

    @action(detail=False, methods=['get'], url_path='my-favorites')
    def my_favorites(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response([])
        doc_ids = DocumentFavorite.objects.filter(student=student).values_list('document_id', flat=True)
        docs = LibraryDocument.objects.filter(id__in=doc_ids, is_active=True)
        return Response(LibraryDocumentSerializer(docs, many=True, context={'request': request}).data)


# ─────────────────────────────────────────────────────────────────────────────
# LOT 12 — Examens sécurisés
# ─────────────────────────────────────────────────────────────────────────────

class SecureExamViewSet(TeacherScopedContentMixin, viewsets.ModelViewSet):
    queryset = SecureExam.objects.select_related('class_obj', 'subject', 'quiz').all()
    serializer_class = SecureExamSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['start_date', 'created_at']
    filterset_fields = ['class_obj', 'subject', 'exam_type', 'is_published', 'is_active']
    # A student behind on their tuition échéancier can't start an exam session
    # (browsing/listing exams is unaffected — see apps.elearning.permissions).
    tuition_gate_actions = ('start_session',)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Pre-fetch this student's exam sessions once for the whole list
        # instead of SecureExamSerializer.get_my_session hitting the DB per exam.
        if self.action == 'list':
            student = getattr(self.request.user, 'student_profile', None)
            if student:
                context['my_sessions_by_exam'] = {
                    s.exam_id: s for s in ExamSession.objects.filter(student=student)
                }
        return context

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        exam = self.get_object()
        exam.is_published = True
        exam.save()
        return Response(SecureExamSerializer(exam).data)

    @action(detail=True, methods=['post'], url_path='start-session')
    def start_session(self, request, pk=None):
        """Student starts a secure exam session."""
        exam = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({'detail': 'Profil étudiant requis'}, status=status.HTTP_400_BAD_REQUEST)
        if not exam.is_available():
            return Response({'detail': 'Cet examen n\'est pas disponible'}, status=status.HTTP_403_FORBIDDEN)

        existing = ExamSession.objects.filter(exam=exam, student=student).first()
        if existing and existing.status in ('SUBMITTED', 'FLAGGED'):
            return Response({'detail': 'Vous avez déjà soumis cet examen'}, status=status.HTTP_400_BAD_REQUEST)

        session, created = ExamSession.objects.get_or_create(
            exam=exam, student=student,
            defaults={'status': 'STARTED', 'time_remaining_seconds': exam.duration_minutes * 60}
        )

        if created and exam.quiz:
            # The student's frontend flow calls quiz start-attempt (which resumes
            # any in-progress attempt) BEFORE this endpoint, and submits answers
            # against that attempt's id. Blindly creating a new QuizAttempt here
            # produced a second, permanently-empty attempt disconnected from the
            # one actually being answered — the admin correction screen read this
            # orphaned attempt and showed 0 for every question despite a real
            # submission existing. Reuse the in-progress attempt if one exists.
            attempt = exam.quiz.attempts.filter(student=student, submitted_at__isnull=True).first()
            if not attempt:
                attempt = QuizAttempt.objects.create(quiz=exam.quiz, student=student, max_score=exam.quiz.max_score)
            session.quiz_attempt = attempt
            session.save()

        from .serializers import QuizTakeSerializer
        result = ExamSessionSerializer(session).data
        if session.quiz_attempt:
            quiz_data = QuizTakeSerializer(exam.quiz).data
            if exam.quiz.shuffle_questions:
                import random
                random.shuffle(quiz_data['questions'])
            result['quiz'] = quiz_data
        return Response(result, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='log-event')
    def log_event(self, request, pk=None):
        """Anti-cheat: log a suspicious event in the student's exam session."""
        exam = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({'detail': 'Profil étudiant requis'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session = ExamSession.objects.get(exam=exam, student=student)
        except ExamSession.DoesNotExist:
            return Response({'detail': 'Session non trouvée'}, status=status.HTTP_404_NOT_FOUND)

        event_type = request.data.get('event_type', 'OTHER')
        details = request.data.get('details', {})
        session.log_event(event_type, details)
        return Response({
            'status': 'logged',
            'is_flagged': session.is_flagged,
            'fraud_block_count': session.fraud_block_count,
        })

    @action(detail=True, methods=['get'], url_path='sessions')
    def sessions(self, request, pk=None):
        exam = self.get_object()
        qs = ExamSession.objects.filter(exam=exam).select_related('student__user', 'quiz_attempt')
        return Response(ExamSessionSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'], url_path='ranking')
    def ranking(self, request, pk=None):
        """Student-facing leaderboard — rank + mention only (Excellent/Très
        bien/.../Insuffisant), never the raw score or any other session
        detail (feedback, flags, submitted files...). Deliberately a
        separate, narrower action from `sessions` above, which dumps full
        ExamSession data and is meant for teacher/admin use only.
        """
        exam = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        sessions = ExamSession.objects.filter(
            exam=exam, status__in=['SUBMITTED', 'FLAGGED']
        ).select_related('student__user', 'quiz_attempt')

        graded = []
        for s in sessions:
            percent = s.resolve_percent()
            if percent is not None:
                graded.append((s, percent))
        graded.sort(key=lambda pair: -pair[1])

        result = [
            {
                'rank': rank,
                'is_me': bool(student) and s.student_id == student.id,
                'full_name': s.student.user.full_name or s.student.matricule,
                'mention': mention_for_percent(percent),
            }
            for rank, (s, percent) in enumerate(graded, 1)
        ]
        return Response({'results': result, 'total_graded': len(result)})

    @action(detail=True, methods=['get'], url_path='my-session')
    def my_session(self, request, pk=None):
        exam = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response(None)
        session = ExamSession.objects.filter(exam=exam, student=student).first()
        return Response(ExamSessionSerializer(session).data if session else None)


class ExamSessionSnapshotView(APIView):
    """POST /elearning/exams/sessions/<session_id>/snapshot/ — student uploads a webcam snapshot.
    GET  /elearning/exams/sessions/<session_id>/snapshot/ — admin/teacher reviews all snapshots
    (with AI analysis) captured for that session, most recent first.
    """

    def get(self, request, session_id):
        try:
            session = ExamSession.objects.get(id=session_id)
        except ExamSession.DoesNotExist:
            return Response({'detail': 'Session introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        snapshots = session.snapshots.all()
        return Response(ExamSnapshotSerializer(snapshots, many=True, context={'request': request}).data)

    def post(self, request, session_id):
        try:
            session = ExamSession.objects.get(id=session_id)
        except ExamSession.DoesNotExist:
            return Response({'detail': 'Session introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        image = request.FILES.get('snapshot')
        if not image:
            return Response({'detail': 'Image requise.'}, status=status.HTTP_400_BAD_REQUEST)

        # Read the raw bytes before handing the file to the ORM — saving the
        # ImageField consumes the upload stream, so reading it again afterwards
        # returns empty/garbage bytes and silently corrupts the AI analysis below.
        image_bytes = image.read()
        image.seek(0)
        snapshot = ExamSnapshot.objects.create(session=session, image=image)

        # Gemini vision analysis — a real natural-language description of what
        # the snapshot shows (not just boolean flags), stored directly on the
        # snapshot so the admin review screen can display it right next to
        # the image without a second round-trip.
        from .ai_service import analyze_exam_snapshot
        analysis = analyze_exam_snapshot(image_bytes)
        face_detected  = analysis['face_detected']
        phone_detected = analysis['phone_detected']
        snapshot.face_detected  = face_detected
        snapshot.phone_detected = phone_detected
        snapshot.ai_analysis    = analysis['description']
        snapshot.save()

        if not face_detected or phone_detected or analysis['multiple_faces'] or analysis['suspicious']:
            session.log_event('AI_FLAG', analysis['description'])

        return Response({
            'snapshot_id': str(snapshot.id),
            'face_detected': face_detected,
            'phone_detected': phone_detected,
            'description': analysis['description'],
        })


# ─────────────────────────────────────────────────────────────────────────────
# Exam session grading + student submission upload
# ─────────────────────────────────────────────────────────────────────────────

class ExamSessionGradeView(APIView):
    """POST /elearning/exam-sessions/<session_id>/grade/ — Corriger une session (prof/admin).
    Accepte multipart/form-data (avec fichier) ou application/json (sans fichier).
    """

    def post(self, request, session_id):
        try:
            session = ExamSession.objects.get(id=session_id)
        except ExamSession.DoesNotExist:
            return Response({'detail': 'Session introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        score = request.data.get('score')
        feedback = request.data.get('feedback', '')
        corrected_file = request.FILES.get('corrected_file')

        if score is not None:
            try:
                score = float(score)
            except (TypeError, ValueError):
                return Response({'detail': 'Score invalide.'}, status=status.HTTP_400_BAD_REQUEST)
            # Defense in depth: this endpoint had no bound check at all, so a
            # client-side computation bug (e.g. a ratio that divided by a
            # stale/mismatched max_score and clamped to a false "full marks")
            # could silently persist an out-of-range grade with nothing here
            # to catch it.
            max_score = float(session.exam.max_score or 0)
            if score < 0 or (max_score > 0 and score > max_score):
                return Response(
                    {'detail': f"Le score doit être compris entre 0 et {max_score}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            session.score = score
        if feedback:
            session.feedback = feedback
        if corrected_file:
            session.corrected_file = corrected_file

        session.corrected_by = request.user
        from django.utils import timezone as tz
        session.corrected_at = tz.now()
        if session.status == 'STARTED':
            # A session being graded has necessarily been turned in — without this,
            # exams submitted via file upload stay stuck in STARTED forever since
            # that path never flips status (see ExamSessionSubmitFileView), which
            # keeps them out of the student's "Complétés" list even once graded.
            session.status = 'SUBMITTED'
            session.submitted_at = session.submitted_at or tz.now()
        session.save()
        session.check_webcam_integrity()
        return Response(ExamSessionSerializer(session).data)


class ExamSessionSubmitFileView(APIView):
    """POST /elearning/exam-sessions/<session_id>/submit-file/ — Étudiant uploade sa copie."""
    tuition_gate_required = True

    def post(self, request, session_id):
        try:
            session = ExamSession.objects.get(id=session_id)
        except ExamSession.DoesNotExist:
            return Response({'detail': 'Session introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        # Vérifier que c'est bien l'étudiant propriétaire
        student = getattr(request.user, 'student_profile', None)
        if student and session.student_id != student.id:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)

        submission_file = request.FILES.get('submission_file')
        if not submission_file:
            return Response({'detail': 'Fichier requis.'}, status=status.HTTP_400_BAD_REQUEST)

        session.submission_file = submission_file
        session.submission_note = request.data.get('note', '')
        if session.status == 'STARTED':
            from django.utils import timezone as tz
            session.status = 'SUBMITTED'
            session.submitted_at = session.submitted_at or tz.now()
        session.save()
        session.check_webcam_integrity()
        return Response(ExamSessionSerializer(session).data)


# ─────────────────────────────────────────────────────────────────────────────
# LOT 13 — Laboratoires virtuels
# ─────────────────────────────────────────────────────────────────────────────

class VirtualLabViewSet(TeacherScopedContentMixin, viewsets.ModelViewSet):
    queryset = VirtualLab.objects.select_related('class_obj', 'subject', 'lesson').annotate(
        submission_count=Count('submissions')
    ).all()
    serializer_class = VirtualLabSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description', 'instructions']
    ordering_fields = ['order', 'due_date', 'created_at']
    filterset_fields = ['class_obj', 'subject', 'lesson', 'lab_type', 'is_published', 'is_active']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Pre-fetch this student's lab submissions once for the whole list
        # instead of VirtualLabSerializer.get_my_submission hitting the DB per lab.
        if self.action == 'list':
            student = getattr(self.request.user, 'student_profile', None)
            if student:
                latest = {}
                for sub in LabSubmission.objects.filter(student=student).order_by('-started_at'):
                    latest.setdefault(sub.lab_id, sub)
                context['my_submissions_by_lab'] = latest
        return context

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        lab = self.get_object()
        lab.is_published = True
        lab.save()
        return Response(VirtualLabSerializer(lab, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='start')
    def start(self, request, pk=None):
        lab = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({'detail': 'Profil étudiant requis'}, status=status.HTTP_400_BAD_REQUEST)

        attempts = LabSubmission.objects.filter(lab=lab, student=student).count()
        if lab.max_attempts and attempts >= lab.max_attempts:
            return Response({'detail': 'Nombre maximum de tentatives atteint'}, status=status.HTTP_403_FORBIDDEN)

        submission = LabSubmission.objects.create(lab=lab, student=student, status='STARTED')
        return Response(LabSubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='submissions')
    def lab_submissions(self, request, pk=None):
        lab = self.get_object()
        qs = LabSubmission.objects.filter(lab=lab).select_related('student__user', 'graded_by__user')
        return Response(LabSubmissionSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'], url_path='my-submission')
    def my_submission(self, request, pk=None):
        lab = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response(None)
        sub = LabSubmission.objects.filter(lab=lab, student=student).order_by('-started_at').first()
        return Response(LabSubmissionSerializer(sub).data if sub else None)


class LabSubmissionViewSet(viewsets.ModelViewSet):
    queryset = LabSubmission.objects.select_related('lab', 'student__user', 'graded_by__user').all()
    serializer_class = LabSubmissionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['started_at', 'submitted_at']
    filterset_fields = ['lab', 'student', 'status', 'is_active']

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        from django.utils import timezone
        submission = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student or submission.student_id != student.id:
            return Response({'detail': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)

        submission.status = 'SUBMITTED'
        submission.submitted_at = timezone.now()
        submission.report_text = request.data.get('report_text', submission.report_text)
        if 'report_file' in request.FILES:
            submission.report_file = request.FILES['report_file']
        if 'screenshot' in request.FILES:
            submission.screenshot = request.FILES['screenshot']
        submission.save()
        return Response(LabSubmissionSerializer(submission).data)

    @action(detail=True, methods=['post'])
    def grade(self, request, pk=None):
        from django.utils import timezone
        submission = self.get_object()
        teacher = getattr(request.user, 'teacher_profile', None)
        score = request.data.get('score')
        if score is None:
            return Response({'detail': 'Note requise'}, status=status.HTTP_400_BAD_REQUEST)
        submission.score = score
        submission.feedback = request.data.get('feedback', '')
        submission.graded_by = teacher
        submission.graded_at = timezone.now()
        submission.status = 'GRADED'
        submission.save()
        return Response(LabSubmissionSerializer(submission).data)


# ─────────────────────────────────────────────────────────────────────────────
# LOTS 15/16/17 — IA pédagogique / IA Enseignant / Correction automatique
# ─────────────────────────────────────────────────────────────────────────────

class AIConversationViewSet(viewsets.ModelViewSet):
    serializer_class = AIConversationSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title']
    ordering_fields = ['updated_at', 'created_at']
    filterset_fields = ['conv_type', 'subject', 'lesson', 'is_active']

    def get_queryset(self):
        return AIConversation.objects.filter(
            user=self.request.user, is_active=True
        ).select_related('subject', 'lesson').prefetch_related('messages').order_by('-updated_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return AIConversationListSerializer
        return AIConversationSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='send')
    def send_message(self, request, pk=None):
        """Send a message and get AI response (Lots 15/16)."""
        from .ai_service import chat_tutor, chat_teacher
        from django.utils import timezone

        conversation = self.get_object()
        if conversation.user_id != request.user.id:
            return Response({'detail': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)

        ser = AISendMessageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_content = ser.validated_data['content']

        AIMessage.objects.create(conversation=conversation, role='user', content=user_content)

        history = [
            {'role': m.role, 'content': m.content}
            for m in conversation.messages.order_by('created_at')
        ]

        subject_name = conversation.subject.name if conversation.subject else ''
        lesson_title = conversation.lesson.title if conversation.lesson else ''

        if conversation.conv_type in ('TEACHER', 'CONTENT', 'QUIZ_GEN'):
            ai_text, tokens = chat_teacher(history, subject_name)
        else:
            ai_text, tokens = chat_tutor(history, subject_name, lesson_title)

        ai_msg = AIMessage.objects.create(
            conversation=conversation, role='assistant',
            content=ai_text, tokens_used=tokens,
        )
        AIConversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())

        if not conversation.title and len(history) <= 2:
            short = user_content[:80].strip()
            AIConversation.objects.filter(pk=conversation.pk).update(title=short)

        return Response(AIMessageSerializer(ai_msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='clear')
    def clear_messages(self, request, pk=None):
        conversation = self.get_object()
        conversation.messages.all().delete()
        return Response({'status': 'cleared'})


class AIGenerateView(APIView):
    """Lot 16 — One-shot content generation (no conversation history)."""

    def post(self, request):
        from .ai_service import generate_content
        ser = AIGenerateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        text, tokens = generate_content(d['generate_type'], d['prompt'], d.get('options', {}))
        return Response({'result': text, 'tokens_used': tokens})


class AIGradeView(APIView):
    """Lot 17 — AI grading of a text submission."""

    def post(self, request):
        from .ai_service import grade_submission
        ser = AIGradeSubmissionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        try:
            submission = AssignmentSubmission.objects.get(id=d['submission_id'])
        except AssignmentSubmission.DoesNotExist:
            return Response({'detail': 'Soumission non trouvée'}, status=status.HTTP_404_NOT_FOUND)

        text_to_grade = submission.content or ''
        ai_result, tokens = grade_submission(text_to_grade, d.get('grading_criteria', ''), d.get('max_score', 20))

        import json as _json
        try:
            parsed = _json.loads(ai_result)
        except Exception:
            parsed = {'feedback': ai_result}

        return Response({'ai_result': parsed, 'tokens_used': tokens, 'submission_id': str(submission.id)})


# =============================================================================
# LOT 9 — VIDÉOTHÈQUE
# =============================================================================

class VideoLibraryViewSet(viewsets.ModelViewSet):
    serializer_class = VideoLibrarySerializer
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['class_obj', 'subject', 'lesson', 'source_type', 'is_published']
    search_fields    = ['title', 'description', 'tags']
    ordering_fields  = ['order', 'title', 'view_count', 'created_at']

    def get_queryset(self):
        return VideoLibrary.objects.filter(is_active=True).prefetch_related('subtitles')

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'], url_path='track-progress')
    def track_progress(self, request, pk=None):
        video = self.get_object()
        from apps.students.models import Student
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'detail': 'Profil étudiant introuvable'}, status=status.HTTP_404_NOT_FOUND)

        position  = int(request.data.get('position_seconds', 0))
        completed = bool(request.data.get('is_completed', False))

        prog, created = VideoProgress.objects.get_or_create(
            student=student, video=video,
            defaults={'position_seconds': position, 'is_completed': completed}
        )
        if not created:
            watched_delta = position - prog.position_seconds if position > prog.position_seconds else 0
            prog.position_seconds = position
            prog.total_watched_seconds = (prog.total_watched_seconds or 0) + watched_delta
            if completed:
                prog.is_completed = True
            prog.save()

        if created or position > (prog.position_seconds - 30):
            VideoLibrary.objects.filter(pk=video.pk).update(view_count=video.view_count + 1)

        return Response({'position_seconds': prog.position_seconds, 'is_completed': prog.is_completed})

    @action(detail=True, methods=['post'], url_path='download-token')
    def download_token(self, request, pk=None):
        video = self.get_object()
        if not video.is_downloadable:
            return Response({'detail': 'Téléchargement non autorisé pour cette vidéo.'},
                            status=status.HTTP_403_FORBIDDEN)
        from apps.students.models import Student
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'detail': 'Profil étudiant introuvable'}, status=status.HTTP_404_NOT_FOUND)

        token_obj = video.generate_download_token(student)
        return Response({
            'token': token_obj.token,
            'expires_at': token_obj.expires_at,
            'download_url': request.build_absolute_uri(
                f'/api/elearning/videos/{video.id}/download/?token={token_obj.token}'
            )
        })

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        from django.http import FileResponse, Http404
        video = self.get_object()
        token_str = request.query_params.get('token', '')
        try:
            token_obj = VideoDownloadToken.objects.get(token=token_str, video=video)
        except VideoDownloadToken.DoesNotExist:
            return Response({'detail': 'Token invalide.'}, status=status.HTTP_403_FORBIDDEN)
        if not token_obj.is_valid():
            return Response({'detail': 'Token expiré ou déjà utilisé.'}, status=status.HTTP_403_FORBIDDEN)
        token_obj.is_used = True
        token_obj.save()
        if video.video_file:
            return FileResponse(video.video_file.open('rb'), as_attachment=True,
                                filename=f"{video.title}.mp4")
        return Response({'detail': 'Pas de fichier à télécharger.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='recommendations')
    def recommendations(self, request):
        from apps.students.models import Student
        from .ai_service import _call_claude
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response([])

        watched_ids = VideoProgress.objects.filter(student=student).values_list('video_id', flat=True)
        watched_titles = list(VideoLibrary.objects.filter(id__in=watched_ids).values_list('title', flat=True))
        all_videos_qs = VideoLibrary.objects.filter(is_published=True, is_active=True).exclude(id__in=watched_ids)

        if not all_videos_qs.exists():
            return Response([])

        candidate_titles = list(all_videos_qs.values_list('title', 'tags')[:30])
        candidates_text  = '\n'.join([f"- {t[0]} [tags: {t[1]}]" for t in candidate_titles])
        watched_text     = ', '.join(watched_titles[:10]) if watched_titles else 'aucune'

        system = "Tu es un moteur de recommandation pédagogique. Réponds uniquement avec une liste JSON d'indices (0-basé) des vidéos recommandées, ex: [0,2,5]."
        messages = [{"role": "user", "content": f"Vidéos vues : {watched_text}\n\nCandidats :\n{candidates_text}\n\nRecommande les 5 meilleures vidéos pour cet étudiant."}]
        result, _ = _call_claude(system, messages, max_tokens=200)

        import json as _json, re
        try:
            indices = _json.loads(re.search(r'\[.*\]', result, re.DOTALL).group())
        except Exception:
            indices = list(range(min(5, len(candidate_titles))))

        all_videos = list(all_videos_qs[:30])
        recommended = [all_videos[i] for i in indices if 0 <= i < len(all_videos)]
        serializer = VideoLibrarySerializer(recommended[:5], many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='upload-subtitle')
    def upload_subtitle(self, request, pk=None):
        video = self.get_object()
        lang_code  = request.data.get('language_code', 'fr')
        lang_label = request.data.get('language_label', 'Français')
        file_obj   = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'Fichier requis.'}, status=status.HTTP_400_BAD_REQUEST)
        sub, created = VideoSubtitle.objects.update_or_create(
            video=video, language_code=lang_code,
            defaults={'language_label': lang_label, 'file': file_obj}
        )
        return Response(VideoSubtitleSerializer(sub, context={'request': request}).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='my-progress')
    def my_progress(self, request):
        from apps.students.models import Student
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response([])
        qs = VideoProgress.objects.filter(student=student).select_related('video')
        return Response(VideoProgressSerializer(qs, many=True).data)


# =============================================================================
# LOT 8 — CLASSES VIRTUELLES
# =============================================================================

class VirtualClassroomViewSet(viewsets.ModelViewSet):
    serializer_class = VirtualClassroomSerializer
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['class_obj', 'subject', 'provider', 'is_ended']
    search_fields    = ['title']
    ordering_fields  = ['start_time', 'created_at']

    def get_queryset(self):
        return VirtualClassroom.objects.filter(is_active=True)

    def perform_create(self, serializer):
        import uuid
        data = serializer.validated_data
        provider = data.get('provider', 'JITSI')
        room_name = data.get('jitsi_room_name') or f"campus-{uuid.uuid4().hex[:8]}"
        extra = {}
        if provider == 'JITSI':
            extra['jitsi_room_name'] = room_name
            extra['join_url'] = f"https://meet.jit.si/{room_name}"
        serializer.save(created_by=self.request.user, **extra)

    @action(detail=True, methods=['post'], url_path='end')
    def end_session(self, request, pk=None):
        from django.utils import timezone
        classroom = self.get_object()
        classroom.is_ended = True
        classroom.ended_at = timezone.now()
        classroom.save()
        return Response({'status': 'ended', 'ended_at': classroom.ended_at})

    @action(detail=True, methods=['get'], url_path='polls')
    def polls(self, request, pk=None):
        classroom = self.get_object()
        qs = classroom.polls.filter(is_active=True)
        return Response(ClassroomPollSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='polls/create')
    def create_poll(self, request, pk=None):
        classroom = self.get_object()
        question = request.data.get('question', '')
        options  = request.data.get('options', [])
        if not question or len(options) < 2:
            return Response({'detail': 'Question et au moins 2 options requis.'},
                            status=status.HTTP_400_BAD_REQUEST)
        poll = ClassroomPoll.objects.create(classroom=classroom, question=question, options=options)
        return Response(ClassroomPollSerializer(poll, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='polls/(?P<poll_id>[^/.]+)/vote')
    def vote_poll(self, request, pk=None, poll_id=None):
        classroom = self.get_object()
        from apps.students.models import Student
        try:
            student = Student.objects.get(user=request.user)
            poll    = ClassroomPoll.objects.get(id=poll_id, classroom=classroom, is_active=True)
        except Exception:
            return Response({'detail': 'Sondage introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        option_idx = int(request.data.get('option', -1))
        if option_idx < 0 or option_idx >= len(poll.options):
            return Response({'detail': 'Option invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        PollResponse.objects.update_or_create(
            poll=poll, student=student,
            defaults={'selected_option': option_idx}
        )
        return Response({'voted': True, 'option': option_idx})

    @action(detail=True, methods=['post'], url_path='polls/(?P<poll_id>[^/.]+)/reveal')
    def reveal_poll(self, request, pk=None, poll_id=None):
        classroom = self.get_object()
        try:
            poll = ClassroomPoll.objects.get(id=poll_id, classroom=classroom)
        except ClassroomPoll.DoesNotExist:
            return Response({'detail': 'Sondage introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        poll.show_results = True
        poll.save()
        return Response(ClassroomPollSerializer(poll, context={'request': request}).data)

    @action(detail=True, methods=['get'], url_path='chat')
    def chat(self, request, pk=None):
        classroom = self.get_object()
        qs = classroom.chat_messages.order_by('created_at')
        return Response(ClassroomChatMessageSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'], url_path='chat/send')
    def send_chat(self, request, pk=None):
        classroom = self.get_object()
        msg_text  = request.data.get('message', '').strip()
        if not msg_text:
            return Response({'detail': 'Message vide.'}, status=status.HTTP_400_BAD_REQUEST)
        msg = ClassroomChatMessage.objects.create(
            classroom=classroom, user=request.user, message=msg_text
        )
        return Response(ClassroomChatMessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='hand-raises')
    def hand_raises(self, request, pk=None):
        classroom = self.get_object()
        qs = classroom.hand_raises.filter(is_raised=True).order_by('raised_at')
        return Response(HandRaiseSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'], url_path='raise-hand')
    def raise_hand(self, request, pk=None):
        classroom = self.get_object()
        from apps.students.models import Student
        from django.utils import timezone
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'detail': 'Profil étudiant requis.'}, status=status.HTTP_400_BAD_REQUEST)
        hr, _ = HandRaise.objects.get_or_create(classroom=classroom, student=student)
        hr.is_raised = True
        hr.lowered_at = None
        hr.save()
        return Response({'raised': True})

    @action(detail=True, methods=['post'], url_path='lower-hand')
    def lower_hand(self, request, pk=None):
        classroom = self.get_object()
        from apps.students.models import Student
        from django.utils import timezone
        try:
            student = Student.objects.get(user=request.user)
            hr = HandRaise.objects.get(classroom=classroom, student=student)
        except Exception:
            return Response({'raised': False})
        hr.is_raised = False
        hr.lowered_at = timezone.now()
        hr.save()
        return Response({'raised': False})

    @action(detail=True, methods=['post'], url_path='ai-summarize')
    def ai_summarize(self, request, pk=None):
        classroom = self.get_object()
        transcript = request.data.get('transcript', classroom.transcript_text)
        if not transcript:
            return Response({'detail': 'Transcription requise.'}, status=status.HTTP_400_BAD_REQUEST)

        from .ai_service import _call_claude
        system = "Tu es un assistant pédagogique. Génère un résumé structuré de la session de classe virtuelle en français. Inclus : points clés abordés, décisions, actions à effectuer, questions soulevées."
        messages = [{"role": "user", "content": f"Transcription :\n{transcript}"}]
        summary, tokens = _call_claude(system, messages, max_tokens=1024)

        classroom.transcript_text = transcript
        classroom.ai_summary = summary
        classroom.save()
        return Response({'ai_summary': summary, 'tokens_used': tokens})

    # ── Segments ────────────────────────────────────────────────────────────

    def retrieve(self, request, *args, **kwargs):
        """Return classroom with segments."""
        instance = self.get_object()
        serializer = VirtualClassroomDetailSerializer(instance, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='generate-segments')
    def generate_segments(self, request, pk=None):
        """Split the classroom duration into ≤60-min segments and persist them."""
        from django.utils import timezone
        import math, uuid

        classroom = self.get_object()
        segment_max = int(request.data.get('segment_duration', 55))  # min par segment
        force = request.data.get('force', False)

        if classroom.segments.exists() and not force:
            return Response(
                {'detail': 'Des segments existent déjà. Passez force=true pour regénérer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Supprimer anciens si force
        if force:
            classroom.segments.all().delete()

        total = classroom.duration_minutes
        n_segments = math.ceil(total / segment_max)
        provider = classroom.provider
        segments = []

        for i in range(n_segments):
            seq = i + 1
            seg_start = classroom.start_time + __import__('datetime').timedelta(minutes=i * segment_max)
            seg_duration = min(segment_max, total - i * segment_max)
            seg_end = seg_start + __import__('datetime').timedelta(minutes=seg_duration)

            # URL de réunion par fournisseur
            if provider == 'JITSI':
                room = f"{classroom.jitsi_room_name or 'campus'}-seg{seq}"
                meeting_url = f"https://meet.jit.si/{room}"
            elif provider == 'MEET':
                meeting_url = classroom.join_url  # URL existante (Google Meet)
            else:
                meeting_url = classroom.join_url

            seg = MeetingSegment.objects.create(
                virtual_class=classroom,
                sequence=seq,
                meeting_url=meeting_url,
                start_time=seg_start,
                end_time=seg_end,
                status='PLANIFIEE',
            )
            segments.append(seg)

        SessionLog.objects.create(
            virtual_class=classroom,
            log_type='CREATED',
            actor=request.user,
            detail=f'{n_segments} segments générés (durée totale {total} min)',
        )
        return Response(MeetingSegmentSerializer(segments, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='segments')
    def segments(self, request, pk=None):
        classroom = self.get_object()
        qs = classroom.segments.order_by('sequence')
        return Response(MeetingSegmentSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'], url_path='logs')
    def logs(self, request, pk=None):
        classroom = self.get_object()
        qs = classroom.logs.order_by('-created_at')[:50]
        return Response(SessionLogSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'], url_path='schedule-tasks')
    def schedule_tasks(self, request, pk=None):
        """Planifie toutes les tâches Celery (notifications + auto-transitions) pour les segments."""
        from .tasks import schedule_classroom_tasks
        classroom = self.get_object()
        if not classroom.segments.exists():
            return Response(
                {'detail': 'Générez d\'abord les segments (generate-segments).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = schedule_classroom_tasks.delay(str(classroom.id))
        return Response({'task_id': result.id, 'detail': 'Planification en cours.'})

    @action(detail=True, methods=['get'], url_path='attendance-summary')
    def attendance_summary(self, request, pk=None):
        """Résumé de présence par segment."""
        classroom = self.get_object()
        result = []
        for seg in classroom.segments.order_by('sequence'):
            participants = seg.participants.all()
            result.append({
                'segment': seg.sequence,
                'status': seg.status,
                'start_time': seg.start_time,
                'end_time': seg.end_time,
                'participants_count': participants.count(),
                'avg_duration_seconds': int(
                    sum(p.attendance_duration for p in participants) / max(participants.count(), 1)
                ),
            })
        return Response(result)


class MeetingSegmentViewSet(viewsets.ModelViewSet):
    serializer_class = MeetingSegmentSerializer
    filter_backends  = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['virtual_class', 'status', 'sequence']
    ordering_fields  = ['sequence', 'start_time']

    def get_queryset(self):
        return MeetingSegment.objects.filter(is_active=True)

    @action(detail=True, methods=['post'], url_path='start')
    def start_segment(self, request, pk=None):
        from django.utils import timezone
        seg = self.get_object()
        if seg.status not in ('PLANIFIEE', 'EN_ATTENTE'):
            return Response({'detail': 'Impossible de démarrer ce segment.'}, status=400)
        seg.status = 'EN_COURS'
        seg.started_at = timezone.now()
        seg.save()
        SessionLog.objects.create(
            virtual_class=seg.virtual_class,
            segment=seg,
            log_type='STARTED',
            actor=request.user,
            detail=f'Segment {seg.sequence} démarré',
        )
        return Response(MeetingSegmentSerializer(seg).data)

    @action(detail=True, methods=['post'], url_path='end')
    def end_segment(self, request, pk=None):
        from django.utils import timezone
        seg = self.get_object()
        if seg.status != 'EN_COURS':
            return Response({'detail': 'Le segment n\'est pas en cours.'}, status=400)
        seg.status = 'TERMINEE'
        seg.ended_at = timezone.now()
        seg.save()
        SessionLog.objects.create(
            virtual_class=seg.virtual_class,
            segment=seg,
            log_type='ENDED',
            actor=request.user,
            detail=f'Segment {seg.sequence} terminé',
        )

        # Chercher le segment suivant
        next_seg = MeetingSegment.objects.filter(
            virtual_class=seg.virtual_class,
            sequence=seg.sequence + 1,
        ).first()
        if next_seg:
            next_seg.status = 'EN_ATTENTE'
            next_seg.save()
            SessionLog.objects.create(
                virtual_class=seg.virtual_class,
                segment=next_seg,
                log_type='TRANSITION',
                actor=request.user,
                detail=f'Transition vers segment {next_seg.sequence}',
            )
        else:
            # Toutes les sessions terminées — marquer la classe comme terminée
            classroom = seg.virtual_class
            classroom.is_ended = True
            classroom.ended_at = timezone.now()
            classroom.save()

        return Response({
            'ended': MeetingSegmentSerializer(seg).data,
            'next': MeetingSegmentSerializer(next_seg).data if next_seg else None,
        })

    @action(detail=True, methods=['post'], url_path='join')
    def join_segment(self, request, pk=None):
        from django.utils import timezone
        from apps.students.models import Student
        seg = self.get_object()
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({'detail': 'Profil étudiant requis.'}, status=400)

        part, created = SessionParticipant.objects.get_or_create(
            segment=seg, student=student,
            defaults={'joined_at': timezone.now()},
        )
        if not created and not part.joined_at:
            part.joined_at = timezone.now()
            part.save()

        SessionLog.objects.create(
            virtual_class=seg.virtual_class,
            segment=seg,
            log_type='JOINED',
            actor=request.user,
            detail=f'{student.matricule} a rejoint le segment {seg.sequence}',
        )
        return Response({'joined': True, 'meeting_url': seg.meeting_url})

    @action(detail=True, methods=['post'], url_path='leave')
    def leave_segment(self, request, pk=None):
        from django.utils import timezone
        from apps.students.models import Student
        seg = self.get_object()
        try:
            student = Student.objects.get(user=request.user)
            part = SessionParticipant.objects.get(segment=seg, student=student)
        except Exception:
            return Response({'detail': 'Participation introuvable.'}, status=404)

        part.left_at = timezone.now()
        part.save()
        part.calculate_duration()

        SessionLog.objects.create(
            virtual_class=seg.virtual_class,
            segment=seg,
            log_type='LEFT',
            actor=request.user,
            detail=f'{student.matricule} a quitté le segment {seg.sequence}',
        )
        return Response({'left': True, 'duration_seconds': part.attendance_duration})

    @action(detail=True, methods=['get'], url_path='participants')
    def participants(self, request, pk=None):
        seg = self.get_object()
        qs = seg.participants.select_related('student__user')
        return Response(SessionParticipantSerializer(qs, many=True).data)


# ── Cours autonomes ──────────────────────────────────────────────────────────

class CourseViewSet(InstructorScopedCourseMixin, viewsets.ModelViewSet):
    queryset = Course.objects.select_related('site', 'instructor').prefetch_related(
        'sections__chapters__lessons'
    ).filter(is_active=True)
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields   = ['title', 'subtitle', 'description']
    ordering_fields = ['created_at', 'title', 'status', 'total_students', 'average_rating']
    filterset_fields = ['site', 'status', 'level', 'is_free', 'is_active']

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        return CourseSerializer

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        instance = self.get_object()
        # Handle multipart (thumbnail upload)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(CourseSerializer(instance, context={'request': request}).data)

    @action(detail=True, methods=['get'], url_path='find-quiz')
    def find_quiz(self, request, pk=None):
        """Return the quiz for this course: direct FK first, then title-based search."""
        course = self.get_object()
        quiz = None

        # 1. Use direct FK if already configured
        if course.quiz_id:
            quiz = course.quiz
        else:
            # 2. Search by course title keywords
            import re
            words = re.findall(r'\b\w{4,}\b', course.title, re.UNICODE)
            for word in words[:3]:
                qs = Quiz.objects.filter(title__icontains=word, is_published=True, is_active=True)
                if qs.count() == 1:
                    quiz = qs.first()
                    break
            # 3. Broader: any quiz with a word match
            if not quiz and words:
                from django.db.models import Q
                q_filter = Q()
                for word in words[:3]:
                    q_filter |= Q(title__icontains=word)
                qs = Quiz.objects.filter(q_filter, is_published=True, is_active=True)
                if qs.exists():
                    quiz = qs.first()

        if quiz:
            return Response({'id': str(quiz.id), 'title': quiz.title})
        return Response({'id': None, 'title': None})


class CourseSectionViewSet(InstructorScopedCourseMixin, viewsets.ModelViewSet):
    queryset = CourseSection.objects.prefetch_related('chapters__lessons').filter(is_active=True)
    serializer_class = CourseSectionSerializer
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ['course', 'is_active']
    instructor_lookup = 'course__instructor'

    def perform_create(self, serializer):
        if self._is_teacher_request():
            course = serializer.validated_data.get('course')
            if course and course.instructor_id != self.request.user.id:
                raise PermissionDenied("Ce cours ne vous appartient pas.")
        serializer.save()


class CourseChapterViewSet(InstructorScopedCourseMixin, viewsets.ModelViewSet):
    queryset = CourseChapter.objects.prefetch_related('lessons').filter(is_active=True)
    serializer_class = CourseChapterSerializer
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ['section', 'is_active']
    instructor_lookup = 'section__course__instructor'

    def perform_create(self, serializer):
        if self._is_teacher_request():
            section = serializer.validated_data.get('section')
            if section and section.course.instructor_id != self.request.user.id:
                raise PermissionDenied("Ce cours ne vous appartient pas.")
        serializer.save()


class CourseLessonViewSet(InstructorScopedCourseMixin, viewsets.ModelViewSet):
    queryset = CourseLesson.objects.filter(is_active=True)
    serializer_class = CourseLessonSerializer
    filter_backends  = [DjangoFilterBackend]
    filterset_fields = ['chapter', 'content_type', 'is_active']
    instructor_lookup = 'chapter__section__course__instructor'

    def perform_create(self, serializer):
        if self._is_teacher_request():
            chapter = serializer.validated_data.get('chapter')
            if chapter and chapter.section.course.instructor_id != self.request.user.id:
                raise PermissionDenied("Ce cours ne vous appartient pas.")
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='my-completed')
    def my_completed(self, request):
        """Return CourseLesson IDs completed by the current student."""
        from .models import CourseLessonProgress
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response([])
        ids = CourseLessonProgress.objects.filter(
            student=student, is_completed=True
        ).values_list('lesson_id', flat=True)
        return Response(list(ids))

    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None):
        """Manual completion for a course lesson (self-paced course player)."""
        from .models import CourseLessonProgress
        lesson = self.get_object()
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({'detail': 'Profil étudiant requis'}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        progress, _ = CourseLessonProgress.objects.get_or_create(
            student=student, lesson=lesson,
            defaults={'is_completed': True, 'completed_at': timezone.now()}
        )
        if not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            progress.save(update_fields=['is_completed', 'completed_at'])
        return Response({'lesson': str(lesson.id), 'is_completed': True})
