from rest_framework import serializers
from .models import StaffProfile, StaffExperience, StaffDocument
from apps.accounts.serializers import UserSerializer, UserCreateSerializer


class StaffExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffExperience
        fields = ['id', 'staff', 'position', 'company', 'start_date', 'end_date', 'is_current', 'description', 'created_at']
        read_only_fields = ['id', 'staff', 'created_at']


class StaffDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = StaffDocument
        fields = ['id', 'staff', 'document_type', 'title', 'file', 'file_url', 'uploaded_by', 'uploaded_by_name', 'created_at']
        read_only_fields = ['id', 'staff', 'uploaded_by', 'created_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None


class StaffProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)
    monthly_hours = serializers.SerializerMethodField()
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = StaffProfile
        fields = [
            'id', 'user', 'full_name', 'email',
            'employee_id', 'department', 'position', 'hire_date',
            'contract_type', 'site', 'site_name',
            'academic_year', 'academic_year_name',
            'contract_hours_per_week', 'monthly_hours',
            'bio', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_monthly_hours(self, obj):
        if obj.contract_hours_per_week is not None:
            return obj.contract_hours_per_week * 4
        return None


class StaffProfileCreateSerializer(serializers.ModelSerializer):
    user_data = UserCreateSerializer(write_only=True)

    class Meta:
        model = StaffProfile
        fields = [
            'user_data', 'employee_id', 'department', 'position', 'hire_date',
            'contract_type', 'site', 'academic_year', 'contract_hours_per_week', 'bio',
        ]

    def create(self, validated_data):
        from apps.accounts.models import User
        user_data = validated_data.pop('user_data')
        user_data['user_type'] = 'STAFF'
        password = user_data.pop('password')
        user_data.pop('password_confirm', None)
        user = User.objects.create(**user_data)
        user.set_password(password)
        user.save()
        return StaffProfile.objects.create(user=user, **validated_data)


class StaffListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = StaffProfile
        fields = ['id', 'employee_id', 'full_name', 'email', 'department', 'position', 'contract_type', 'contract_hours_per_week', 'site_name', 'is_active']
