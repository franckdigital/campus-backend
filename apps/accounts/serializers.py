from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from .models import User, Role, Permission, UserRole, UserSite


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['full_name'] = user.full_name
        token['user_type'] = user.user_type
        if user.site:
            token['site_id'] = str(user.site.id)
        return token


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'code', 'name', 'description', 'module', 'is_active']
        read_only_fields = ['id']


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Role
        fields = [
            'id', 'name', 'code', 'description', 'permissions',
            'permission_ids', 'is_system', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'is_system']

    def create(self, validated_data):
        permission_ids = validated_data.pop('permission_ids', [])
        role = Role.objects.create(**validated_data)
        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids)
            role.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        permission_ids = validated_data.pop('permission_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if permission_ids is not None:
            permissions = Permission.objects.filter(id__in=permission_ids)
            instance.permissions.set(permissions)
        return instance


class RoleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'code', 'is_system', 'is_active']


class UserRoleSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = UserRole
        fields = ['id', 'user', 'role', 'role_name', 'site', 'site_name', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserSiteSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = UserSite
        fields = ['id', 'user', 'site', 'site_name', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    full_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    accessible_sites = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'phone',
            'user_type', 'avatar', 'site', 'site_name',
            'is_active', 'is_staff', 'date_joined', 'last_login',
            'roles', 'accessible_sites'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

    def get_full_name(self, obj):
        return obj.full_name

    def get_roles(self, obj):
        user_roles = obj.user_roles.filter(is_active=True).select_related('role', 'site')
        return UserRoleSerializer(user_roles, many=True).data

    def get_accessible_sites(self, obj):
        user_sites = obj.user_sites.select_related('site')
        return UserSiteSerializer(user_sites, many=True).data


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone', 'user_type',
            'avatar', 'site', 'is_active'
        ]
        read_only_fields = ['id']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Les mots de passe ne correspondent pas'})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class _UpdateFieldsOnlyMixin:
    """Saves only the fields present in this request's payload (via
    update_fields), instead of Django's default full-row save. Two requests
    editing different fields on the same User concurrently (e.g. the admin
    "Téléphone & mot de passe" modal firing a phone PATCH and a password
    reset in parallel) would otherwise each write back a full snapshot of
    every field taken at their own SELECT time — whichever commits last
    silently reverts the other's change to its stale in-memory value. This
    was reproduced in production: a phone number set together with a
    password reset saved the password but left the phone blank."""

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if validated_data:
            instance.save(update_fields=list(validated_data.keys()))
        return instance


class UserUpdateSerializer(_UpdateFieldsOnlyMixin, serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'user_type',
            'avatar', 'site', 'is_active'
        ]


class SelfProfileUpdateSerializer(_UpdateFieldsOnlyMixin, serializers.ModelSerializer):
    """Used by MeView.patch — a user editing their own profile. Deliberately
    excludes user_type/site/is_active (see UserUpdateSerializer), which are
    admin-only fields and must never be self-editable."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'avatar']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Les mots de passe ne correspondent pas'})
        return data


class UserListSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone',
            'user_type', 'site', 'site_name', 'is_active', 'date_joined'
        ]


class LoginSerializer(serializers.Serializer):
    # Accepts an email OR a phone number — EmailOrPhoneBackend resolves which one it is.
    email = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Identifiant ou mot de passe incorrect')
        if not user.is_active:
            raise serializers.ValidationError('Ce compte est désactivé')
        data['user'] = user
        return data
