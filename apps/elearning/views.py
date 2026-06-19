from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import (
    ZoomMeeting, Lesson, LessonAttachment,
    Assignment, AssignmentSubmission, AssignmentCorrection
)
from .serializers import (
    ZoomMeetingSerializer, LessonSerializer, LessonListSerializer,
    LessonAttachmentSerializer, AssignmentSerializer, AssignmentListSerializer,
    AssignmentSubmissionSerializer, AssignmentCorrectionSerializer,
    CreateZoomMeetingSerializer
)
from .services import ZoomService
from apps.academic.models import Session


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


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.select_related(
        'class_obj', 'subject', 'teacher__user', 'zoom_meeting'
    ).prefetch_related('attachments').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['order', 'created_at', 'published_at']
    filterset_fields = ['class_obj', 'subject', 'teacher', 'is_published', 'is_active']

    def get_serializer_class(self):
        if self.action == 'list':
            return LessonListSerializer
        return LessonSerializer

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        lesson = self.get_object()
        lesson.publish()
        return Response(LessonSerializer(lesson).data)

    @action(detail=True, methods=['post'], url_path='add-attachment')
    def add_attachment(self, request, pk=None):
        lesson = self.get_object()
        serializer = LessonAttachmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lesson=lesson)
        return Response(LessonSerializer(lesson).data)


class LessonAttachmentViewSet(viewsets.ModelViewSet):
    queryset = LessonAttachment.objects.select_related('lesson').all()
    serializer_class = LessonAttachmentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['lesson', 'is_active']


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related(
        'class_obj', 'subject', 'teacher__user', 'lesson'
    ).prefetch_related('submissions').all()
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


class SubmitAssignmentView(APIView):
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
