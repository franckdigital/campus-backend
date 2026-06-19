from rest_framework import serializers
from .models import (
    ZoomMeeting, Lesson, LessonAttachment,
    Assignment, AssignmentSubmission, AssignmentCorrection
)


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
        fields = ['id', 'lesson', 'title', 'file', 'file_type', 'file_size', 'is_active']
        read_only_fields = ['id', 'file_type', 'file_size']


class LessonSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.full_name', read_only=True)
    attachments = LessonAttachmentSerializer(many=True, read_only=True)
    zoom_meeting = ZoomMeetingSerializer(read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'description', 'content', 'class_obj', 'class_name',
            'subject', 'subject_name', 'teacher', 'teacher_name', 'order',
            'is_published', 'published_at', 'zoom_meeting', 'attachments',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'published_at', 'created_at', 'updated_at']


class LessonListSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'class_obj', 'class_name', 'subject', 'subject_name',
            'order', 'is_published', 'published_at'
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

    class Meta:
        model = Assignment
        fields = [
            'id', 'title', 'class_obj', 'class_name', 'subject', 'subject_name',
            'due_date', 'max_score', 'status', 'submission_count'
        ]


class CreateZoomMeetingSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    topic = serializers.CharField(max_length=255)
    start_time = serializers.DateTimeField()
    duration = serializers.IntegerField(default=60)
