from rest_framework import serializers
from .models import AttendanceSession, AttendanceRecord, AbsenceRequest


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_matricule = serializers.CharField(source='student.matricule', read_only=True)
    marked_by_name = serializers.CharField(source='marked_by.full_name', read_only=True)
    date = serializers.DateField(source='attendance_session.date', read_only=True)
    subject_name = serializers.CharField(source='attendance_session.session.subject.name', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'attendance_session', 'student', 'student_name', 'student_matricule',
            'status', 'date', 'subject_name', 'check_in_time', 'check_in_method', 'notes',
            'marked_by', 'marked_by_name', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'check_in_time', 'created_at']


class AttendanceSessionSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='session.class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='session.subject.name', read_only=True)
    teacher_name = serializers.CharField(source='session.teacher.user.full_name', read_only=True)
    opened_by_name = serializers.CharField(source='opened_by.full_name', read_only=True)
    present_count = serializers.IntegerField(read_only=True)
    absent_count = serializers.IntegerField(read_only=True)
    is_qr_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = AttendanceSession
        fields = [
            'id', 'session', 'class_name', 'subject_name', 'teacher_name',
            'date', 'qr_code', 'qr_expiry', 'status', 'opened_by', 'opened_by_name',
            'opened_at', 'closed_at', 'notes', 'present_count', 'absent_count',
            'is_qr_valid', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'qr_code', 'opened_at', 'created_at']


class AttendanceSessionDetailSerializer(AttendanceSessionSerializer):
    records = AttendanceRecordSerializer(many=True, read_only=True)

    class Meta(AttendanceSessionSerializer.Meta):
        fields = AttendanceSessionSerializer.Meta.fields + ['records']


class QRScanSerializer(serializers.Serializer):
    qr_code = serializers.CharField()
    student_id = serializers.UUIDField(required=False)

    def validate_qr_code(self, value):
        try:
            attendance_session = AttendanceSession.objects.get(qr_code=value)
        except AttendanceSession.DoesNotExist:
            raise serializers.ValidationError('QR code invalide')
        if not attendance_session.is_qr_valid():
            raise serializers.ValidationError('QR code expire ou session fermee')
        return value


class AbsenceRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_matricule = serializers.CharField(source='student.matricule', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)
    student_class = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    def get_student_class(self, obj):
        from apps.academic.models import Enrollment
        enrollment = Enrollment.objects.filter(
            student=obj.student, is_active=True
        ).select_related('class_obj').first()
        return enrollment.class_obj.name if enrollment else None

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.attachment.url)
        return obj.attachment.url

    class Meta:
        model = AbsenceRequest
        fields = [
            'id', 'student', 'student_name', 'student_matricule', 'student_class',
            'start_date', 'end_date', 'reason', 'attachment', 'attachment_url', 'status',
            'submitted_at', 'reviewed_by', 'reviewed_by_name',
            'reviewed_at', 'review_notes', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'submitted_at', 'reviewed_by', 'reviewed_at', 'created_at']


class AbsenceRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbsenceRequest
        fields = ['student', 'start_date', 'end_date', 'reason', 'attachment']

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError({
                'end_date': 'La date de fin doit etre apres la date de debut'
            })
        return data
