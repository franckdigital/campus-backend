from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from .models import Parent, Student, StudentParent, StudentFile, StudentCard
from apps.accounts.serializers import UserSerializer, UserCreateSerializer


class ParentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_data = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = Parent
        fields = [
            'id', 'user', 'user_data', 'profession', 'employer',
            'address', 'city', 'emergency_contact', 'relationship',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        from apps.accounts.models import User
        user_data = validated_data.pop('user_data', {})
        password = user_data.pop('password', 'Campus2026!')
        user_data.pop('password_confirm', None)
        email = user_data.get('email', '').strip()

        existing_user = User.objects.filter(email=email).first() if email else None
        if existing_user:
            try:
                return existing_user.parent_profile
            except Parent.DoesNotExist:
                return Parent.objects.create(user=existing_user, **validated_data)

        user_data['user_type'] = 'PARENT'
        user = User.objects.create(**user_data)
        user.set_password(password)
        user.save()
        return Parent.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        try:
            user_data = validated_data.pop('user_data', None)
            if user_data:
                user = instance.user
                for attr in ('first_name', 'last_name', 'phone'):
                    v = user_data.get(attr)
                    if v:
                        setattr(user, attr, v)
                new_email = user_data.get('email')
                if new_email and new_email != user.email:
                    user.email = new_email
                user.save()
            return super().update(instance, validated_data)
        except Exception as e:
            raise serializers.ValidationError({'detail': str(e)})


class ParentListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)

    class Meta:
        model = Parent
        fields = ['id', 'full_name', 'email', 'phone', 'relationship', 'is_active']


class StudentParentSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.user.full_name', read_only=True)
    parent_phone = serializers.CharField(source='parent.user.phone', read_only=True)
    parent_email = serializers.CharField(source='parent.user.email', read_only=True)
    relationship = serializers.CharField(source='parent.relationship', read_only=True)

    class Meta:
        model = StudentParent
        fields = [
            'id', 'student', 'parent', 'parent_name', 'parent_phone',
            'parent_email', 'relationship', 'is_primary', 'can_pickup',
            'receives_notifications', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class StudentCardSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)

    class Meta:
        model = StudentCard
        fields = [
            'id', 'student', 'academic_year', 'academic_year_name',
            'card_number', 'qr_code', 'issue_date', 'expiry_date',
            'is_valid', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'card_number', 'issue_date', 'created_at']


class StudentFileSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = StudentFile
        fields = [
            'id', 'student', 'academic_year', 'academic_year_name',
            'file_type', 'title', 'description', 'data', 'attachment',
            'created_by', 'created_by_name', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_data = serializers.DictField(write_only=True, required=False)
    site_name = serializers.CharField(source='site.name', read_only=True)
    parents = serializers.SerializerMethodField()
    current_card = serializers.SerializerMethodField()
    current_class = serializers.SerializerMethodField()
    # Editable — an admin correcting a wrong/duplicate matricule (e.g. a
    # transfer student re-keyed under the wrong year prefix) needs to be able
    # to change it after creation, not just at StudentCreateSerializer time.
    matricule = serializers.CharField(
        validators=[UniqueValidator(queryset=Student.objects.all(), message="Ce matricule est déjà utilisé.")]
    )

    class Meta:
        model = Student
        fields = [
            'id', 'user', 'user_data', 'matricule', 'gender', 'birth_date', 'birth_place',
            'nationality', 'address', 'city', 'site', 'site_name', 'status', 'modality', 'affectation_status',
            'admission_date', 'graduation_date', 'emergency_contact_name',
            'emergency_contact_phone', 'emergency_contact_relation',
            'medical_info', 'notes', 'photo', 'parents', 'current_card', 'current_class',
            'registration_fee', 'is_enrolled', 'tuition_fee',
            'total_paid', 'remaining_balance', 'echeance_override',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user_data', None)
        if user_data:
            user = instance.user
            for attr in ('first_name', 'last_name', 'phone'):
                if attr in user_data and user_data[attr]:
                    setattr(user, attr, user_data[attr])
            new_email = user_data.get('email')
            if new_email and new_email != user.email:
                user.email = new_email
            user.save()
        return super().update(instance, validated_data)

    def get_parents(self, obj):
        student_parents = obj.student_parents.select_related('parent__user')
        return StudentParentSerializer(student_parents, many=True).data

    def get_current_card(self, obj):
        from apps.core.models import AcademicYear
        current_year = AcademicYear.get_current()
        if current_year:
            card = obj.cards.filter(academic_year=current_year, is_valid=True).first()
            if card:
                return StudentCardSerializer(card).data
        return None

    def get_current_class(self, obj):
        enrollment = obj.enrollments.filter(
            status='ENROLLED', is_active=True
        ).select_related('class_obj__level__program', 'academic_year').first()
        if not enrollment:
            return None
        c = enrollment.class_obj
        return {
            'id': str(c.id),
            'name': c.name,
            'level_id': str(c.level.id) if c.level else None,
            'level_name': c.level.name if c.level else None,
            'program_id': str(c.level.program.id) if c.level and c.level.program else None,
            'program_name': c.level.program.name if c.level and c.level.program else None,
            'academic_year': enrollment.academic_year.name if enrollment.academic_year else None,
            'academic_year_id': str(enrollment.academic_year.id) if enrollment.academic_year else None,
            'enrollment_id': str(enrollment.id),
        }


class StudentCreateSerializer(serializers.ModelSerializer):
    user_data = UserCreateSerializer(write_only=True)
    class_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    # Optional — when the client (admin form) already computed a matricule
    # (manual entry for an affected/former student, or a site-aware generated
    # one), it's used as-is; left blank, Student.save() falls back to its own
    # generate_matricule().
    matricule = serializers.CharField(
        required=False, allow_blank=True,
        validators=[UniqueValidator(queryset=Student.objects.all(), message="Ce matricule est déjà utilisé.")]
    )

    class Meta:
        model = Student
        # 'id' MUST be listed — ModelSerializer only auto-includes the PK in
        # its output when it's explicitly in `fields` (it doesn't add it for
        # free the way the admin might expect). Without it, POST /students/
        # returned a 201 body with no `id` at all, so the admin form's own
        # `if (newStudent?.id && formData.class_id && ...)` guard right after
        # creation silently evaluated false and *never even attempted* to
        # create the student's Enrollment — no error, nothing in the
        # network tab to suggest anything failed, just a student created
        # with zero enrollments every single time, regardless of which
        # classe/filière the admin actually picked in the form. That empty
        # enrollment is exactly what later let a separate signal
        # (create_enrollment_on_first_tuition_invoice, see apps.finance.models)
        # auto-guess an unrelated class (in practice, always BTS) the moment
        # any invoice was created for the student.
        fields = [
            'id', 'user_data', 'matricule', 'gender', 'birth_date', 'birth_place',
            'nationality', 'address', 'city', 'site', 'status', 'modality', 'affectation_status',
            'admission_date', 'emergency_contact_name',
            'emergency_contact_phone', 'emergency_contact_relation',
            'medical_info', 'notes', 'photo', 'registration_fee',
            'tuition_fee', 'class_id'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        from apps.accounts.models import User
        from apps.academic.models import Enrollment, Class, AcademicYear
        
        user_data = validated_data.pop('user_data')
        class_id = validated_data.pop('class_id', None)
        user_data['user_type'] = 'STUDENT'
        
        password = user_data.pop('password')
        user_data.pop('password_confirm', None)
        
        user = User.objects.create(**user_data)
        user.set_password(password)
        user.save()
        
        student = Student.objects.create(user=user, **validated_data)
        
        # Auto-create enrollment if class_id is provided
        if class_id:
            try:
                class_obj = Class.objects.get(id=class_id)
                academic_year = AcademicYear.get_current()
                
                if academic_year:
                    Enrollment.objects.create(
                        student=student,
                        class_obj=class_obj,
                        academic_year=academic_year,
                        status='ENROLLED',
                        is_active=True
                    )
            except Class.DoesNotExist:
                pass  # Silently skip if class doesn't exist
        
        return student


class StudentListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)
    program_name = serializers.SerializerMethodField()
    tuition_up_to_date = serializers.SerializerMethodField()
    has_payment_schedule = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'matricule', 'full_name', 'email', 'phone',
            'gender', 'site', 'site_name', 'status', 'modality', 'affectation_status', 'is_active',
            'is_enrolled', 'echeance_override', 'program_name',
            'tuition_up_to_date', 'has_payment_schedule',
        ]

    def get_program_name(self, obj):
        enrollments = getattr(obj, 'active_enrollments', None)
        if enrollments is not None:
            enrollment = enrollments[0] if enrollments else None
        else:
            enrollment = obj.enrollments.filter(
                status='ENROLLED', is_active=True
            ).select_related('class_obj__level__program').first()
        if enrollment and enrollment.class_obj and enrollment.class_obj.level:
            prog = enrollment.class_obj.level.program
            return prog.name if prog else None
        return None

    def _schedule_status(self, obj):
        if not hasattr(obj, '_tuition_schedule_status_cache'):
            from apps.finance.models import compute_tuition_schedule_status
            obj._tuition_schedule_status_cache = compute_tuition_schedule_status(obj)
        return obj._tuition_schedule_status_cache

    def get_tuition_up_to_date(self, obj):
        return self._schedule_status(obj)['is_up_to_date']

    def get_has_payment_schedule(self, obj):
        return self._schedule_status(obj)['has_schedule']


class StudentDossierSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)
    parents = serializers.SerializerMethodField()
    files = StudentFileSerializer(many=True, read_only=True)
    cards = StudentCardSerializer(many=True, read_only=True)
    current_class = serializers.SerializerMethodField()
    tuition_up_to_date = serializers.SerializerMethodField()
    has_payment_schedule = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'user', 'matricule', 'gender', 'birth_date', 'birth_place',
            'nationality', 'address', 'city', 'site', 'site_name', 'status', 'modality', 'affectation_status',
            'admission_date', 'graduation_date', 'emergency_contact_name',
            'emergency_contact_phone', 'emergency_contact_relation',
            'medical_info', 'notes', 'photo', 'parents', 'files', 'cards',
            'current_class',
            'is_enrolled', 'tuition_fee',
            'total_paid', 'remaining_balance', 'echeance_override',
            'tuition_up_to_date', 'has_payment_schedule',
            'is_active', 'created_at', 'updated_at'
        ]

    def _schedule_status(self, obj):
        if not hasattr(obj, '_tuition_schedule_status_cache'):
            from apps.finance.models import compute_tuition_schedule_status
            obj._tuition_schedule_status_cache = compute_tuition_schedule_status(obj)
        return obj._tuition_schedule_status_cache

    def get_tuition_up_to_date(self, obj):
        return self._schedule_status(obj)['is_up_to_date']

    def get_has_payment_schedule(self, obj):
        return self._schedule_status(obj)['has_schedule']

    def get_parents(self, obj):
        student_parents = obj.student_parents.select_related('parent__user')
        return StudentParentSerializer(student_parents, many=True).data

    def get_current_class(self, obj):
        enrollment = obj.enrollments.filter(
            status='ENROLLED', is_active=True
        ).select_related('class_obj__level__program', 'academic_year').first()
        if not enrollment:
            return None
        c = enrollment.class_obj
        return {
            'id': str(c.id),
            'name': c.name,
            'level_id': str(c.level.id) if c.level else None,
            'level_name': c.level.name if c.level else None,
            'program_id': str(c.level.program.id) if c.level and c.level.program else None,
            'program_name': c.level.program.name if c.level and c.level.program else None,
            'academic_year': enrollment.academic_year.name if enrollment.academic_year else None,
            'academic_year_id': str(enrollment.academic_year.id) if enrollment.academic_year else None,
            'enrollment_id': str(enrollment.id),
        }
