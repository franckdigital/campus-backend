from rest_framework import serializers
from .models import GradeCategory, Evaluation, Grade, ReportCard


class GradeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeCategory
        fields = '__all__'


class EvaluationSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    class_name = serializers.CharField(source='class_group.name', read_only=True)
    class_code = serializers.CharField(source='class_group.code', read_only=True)
    semester_name = serializers.CharField(source='semester.label', read_only=True)
    locked_by_name = serializers.SerializerMethodField()
    grades_count = serializers.SerializerMethodField()

    class Meta:
        model = Evaluation
        fields = '__all__'
        read_only_fields = ['is_locked', 'locked_by', 'locked_at', 'created_by', 'created_at', 'updated_at']

    def get_locked_by_name(self, obj):
        return obj.locked_by.full_name if obj.locked_by else None

    def get_grades_count(self, obj):
        return obj.grades.count()


class GradeSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_matricule = serializers.CharField(source='student.matricule', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    semester_name = serializers.CharField(source='semester.label', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    class_name = serializers.CharField(source='class_group.name', read_only=True)
    evaluation_title = serializers.CharField(source='evaluation.title', read_only=True)
    percentage = serializers.ReadOnlyField()

    class Meta:
        model = Grade
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def get_student_name(self, obj):
        return obj.student.user.full_name if obj.student and obj.student.user else ''


class ReportCardSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_matricule = serializers.CharField(source='student.matricule', read_only=True)
    class_name = serializers.CharField(source='class_group.name', read_only=True)
    semester_name = serializers.CharField(source='semester.label', read_only=True)
    academic_year_name = serializers.CharField(source='semester.academic_year.name', read_only=True)
    academic_year = serializers.IntegerField(source='semester.academic_year.id', read_only=True)
    # Retourne le vrai statut académique (PASS/FAIL/HONORS) pour compatibilité admin
    academic_mention = serializers.CharField(source='status', read_only=True)
    # Pour l'ancien frontend étudiant qui filtre c.status === 'PUBLISHED'
    status = serializers.SerializerMethodField()

    class Meta:
        model = ReportCard
        fields = '__all__'
        read_only_fields = ['generated_at', 'total_students', 'subject_averages']

    def get_student_name(self, obj):
        return obj.student.user.full_name if obj.student and obj.student.user else ''

    def get_status(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        # Étudiant non-staff : retourne 'PUBLISHED' si publié (compat ancien frontend)
        if user and not user.is_staff and hasattr(user, 'student_profile'):
            return 'PUBLISHED' if obj.is_published else 'PENDING'
        return obj.status
