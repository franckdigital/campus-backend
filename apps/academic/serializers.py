from rest_framework import serializers
from .models import (
    Program, Level, Cycle, Class, Subject, TeacherProfile, TeacherSite,
    ClassSubjectTeacher, Enrollment, Room, Session, Semester, LevelSubject,
    TeacherDocument, TeacherExperience,
)
from apps.accounts.serializers import UserSerializer, UserCreateSerializer
from apps.core.models import Site


class SemesterSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    class Meta:
        model = Semester
        fields = '__all__'
        read_only_fields = ['created_at']


class ProgramSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    # Populated by an annotate(levels_count=Count(...)) on the ViewSet's
    # queryset instead of a per-row .count() query.
    levels_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Program
        fields = [
            'id', 'name', 'code', 'description', 'duration_years',
            'site', 'site_name', 'levels_count', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CycleSerializer(serializers.ModelSerializer):
    # Populated by an annotate(levels_count=Count(...)) on the ViewSet's queryset.
    levels_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Cycle
        fields = ['id', 'name', 'code', 'order', 'levels_count', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class LevelSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_code = serializers.CharField(source='program.code', read_only=True)
    cycle_display = serializers.CharField(source='cycle.name', read_only=True, default=None)
    # Populated by annotate(classes_count=..., subjects_count=...) on the
    # ViewSet's queryset instead of two per-row .count() queries.
    classes_count = serializers.IntegerField(read_only=True, default=0)
    subjects_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Level
        fields = [
            'id', 'name', 'code', 'order', 'cycle', 'cycle_display', 'program', 'program_name', 'program_code',
            'classes_count', 'subjects_count', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SubjectSerializer(serializers.ModelSerializer):
    # Populated by an annotate(levels_count=Count(...)) on the ViewSet's
    # queryset instead of a per-row .count() query.
    levels_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'description', 'coefficient',
            'hours_per_week', 'levels_count', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TeacherSiteSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = TeacherSite
        fields = ['id', 'teacher', 'site', 'site_name', 'is_primary', 'created_at']
        read_only_fields = ['id', 'created_at']


class TeacherDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = TeacherDocument
        fields = [
            'id', 'teacher', 'document_type', 'title', 'file', 'file_url',
            'uploaded_by', 'uploaded_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'teacher', 'uploaded_by', 'created_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None


class TeacherExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherExperience
        fields = ['id', 'teacher', 'position', 'company', 'start_date', 'end_date', 'is_current', 'description', 'created_at']
        read_only_fields = ['id', 'teacher', 'created_at']


class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    sites = serializers.SerializerMethodField()
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    monthly_hours = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = [
            'id', 'user', 'employee_id', 'specialization', 'qualification',
            'hire_date', 'contract_type', 'hourly_rate', 'bio', 'sites',
            'academic_year', 'academic_year_name',
            'contract_hours_per_week', 'monthly_hours',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_sites(self, obj):
        teacher_sites = obj.teacher_sites.select_related('site')
        return TeacherSiteSerializer(teacher_sites, many=True).data

    def get_monthly_hours(self, obj):
        if obj.contract_hours_per_week is not None:
            return obj.contract_hours_per_week * 4
        return None


class TeacherProfileCreateSerializer(serializers.ModelSerializer):
    user_data = UserCreateSerializer(write_only=True)
    site = serializers.PrimaryKeyRelatedField(
        queryset=Site.objects.all(),
        required=False, allow_null=True, write_only=True,
    )

    class Meta:
        model = TeacherProfile
        fields = [
            'user_data', 'employee_id', 'specialization', 'qualification',
            'hire_date', 'contract_type', 'hourly_rate', 'bio',
            'academic_year', 'contract_hours_per_week', 'site',
        ]

    def create(self, validated_data):
        from apps.accounts.models import User
        site = validated_data.pop('site', None)
        user_data = validated_data.pop('user_data')
        user_data['user_type'] = 'TEACHER'

        password = user_data.pop('password')
        user_data.pop('password_confirm', None)

        user = User.objects.create(**user_data)
        user.set_password(password)
        user.save()

        teacher = TeacherProfile.objects.create(user=user, **validated_data)
        if site:
            TeacherSite.objects.create(teacher=teacher, site=site, is_primary=True)
        return teacher


class TeacherListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = TeacherProfile
        fields = [
            'id', 'employee_id', 'full_name', 'email',
            'specialization', 'contract_type', 'is_active'
        ]


class ClassSubjectTeacherSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.full_name', read_only=True)
    teacher_employee_id = serializers.CharField(source='teacher.employee_id', read_only=True)
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    class_code = serializers.CharField(source='class_obj.code', read_only=True)
    level_name = serializers.CharField(source='class_obj.level.name', read_only=True)
    program_name = serializers.CharField(source='class_obj.level.program.name', read_only=True)

    class Meta:
        model = ClassSubjectTeacher
        fields = [
            'id', 'class_obj', 'class_name', 'class_code', 'level_name', 'program_name',
            'subject', 'subject_name', 'subject_code',
            'teacher', 'teacher_name', 'teacher_employee_id',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ClassSerializer(serializers.ModelSerializer):
    level_name = serializers.CharField(source='level.name', read_only=True)
    program_name = serializers.CharField(source='level.program.name', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    main_teacher_name = serializers.CharField(source='main_teacher.user.full_name', read_only=True)
    student_count = serializers.IntegerField(read_only=True, default=0)
    subject_teachers = ClassSubjectTeacherSerializer(many=True, read_only=True)

    class Meta:
        model = Class
        fields = [
            'id', 'name', 'code', 'level', 'level_name', 'program_name',
            'academic_year', 'academic_year_name', 'site', 'site_name',
            'max_students', 'student_count', 'main_teacher', 'main_teacher_name',
            'subject_teachers', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClassListSerializer(serializers.ModelSerializer):
    level_name = serializers.CharField(source='level.name', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    student_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Class
        fields = [
            'id', 'name', 'code', 'level', 'level_name',
            'academic_year', 'academic_year_name',
            'site', 'site_name', 'max_students', 'student_count', 'is_active'
        ]


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_matricule = serializers.CharField(source='student.matricule', read_only=True)
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    is_up_to_date = serializers.SerializerMethodField()
    has_payment_schedule = serializers.SerializerMethodField()
    echeance_override = serializers.BooleanField(source='student.echeance_override', read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id', 'student', 'student_name', 'student_matricule',
            'class_obj', 'class_name', 'academic_year', 'academic_year_name',
            'enrollment_date', 'status', 'is_active', 'created_at',
            'is_up_to_date', 'has_payment_schedule', 'echeance_override',
        ]
        read_only_fields = ['id', 'enrollment_date', 'created_at']

    def _schedule_status(self, obj):
        if not hasattr(obj, '_tuition_schedule_status_cache'):
            from apps.finance.models import compute_tuition_schedule_status
            obj._tuition_schedule_status_cache = compute_tuition_schedule_status(obj.student)
        return obj._tuition_schedule_status_cache

    def get_is_up_to_date(self, obj):
        return self._schedule_status(obj)['is_up_to_date']

    def get_has_payment_schedule(self, obj):
        return self._schedule_status(obj)['has_schedule']


class RoomSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = Room
        fields = [
            'id', 'name', 'code', 'site', 'site_name', 'building',
            'floor', 'capacity', 'room_type', 'equipment',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SessionSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.full_name', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)
    semester_name = serializers.CharField(source='semester.label', read_only=True)
    academic_year_id = serializers.UUIDField(source='class_obj.academic_year_id', read_only=True)
    academic_year_name = serializers.CharField(source='class_obj.academic_year.name', read_only=True)
    site_id = serializers.UUIDField(source='class_obj.site_id', read_only=True)
    day_name = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id', 'class_obj', 'class_name', 'subject', 'subject_name',
            'teacher', 'teacher_name', 'room', 'room_name',
            'semester', 'semester_name', 'academic_year_id', 'academic_year_name',
            'site_id', 'day_of_week', 'day_name', 'start_time', 'end_time',
            'is_recurring', 'specific_date', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_day_name(self, obj):
        return dict(Session.DAY_CHOICES).get(obj.day_of_week, '')


class LevelSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    subject_coefficient = serializers.DecimalField(source='subject.coefficient', max_digits=4, decimal_places=2, read_only=True)
    subject_hours = serializers.DecimalField(source='subject.hours_per_week', max_digits=4, decimal_places=2, read_only=True)
    level_name = serializers.CharField(source='level.name', read_only=True)
    program_name = serializers.CharField(source='level.program.name', read_only=True)
    program_id = serializers.UUIDField(source='level.program.id', read_only=True)

    class Meta:
        model = LevelSubject
        fields = [
            'id', 'level', 'level_name', 'program_name', 'program_id',
            'subject', 'subject_name', 'subject_code', 'subject_coefficient', 'subject_hours',
            'coefficient', 'hours_per_week', 'is_mandatory',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
