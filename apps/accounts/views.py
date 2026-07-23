from django.db.models import ProtectedError
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.models import AuditLog
from .models import User, Role, Permission, UserRole, UserSite
from .permissions import IsAdminOrStaff
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    UserListSerializer, ChangePasswordSerializer, SelfProfileUpdateSerializer,
    RoleSerializer, RoleListSerializer,
    PermissionSerializer, UserRoleSerializer, UserSiteSerializer,
    LoginSerializer
)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        refresh = RefreshToken.for_user(user)
        refresh['email'] = user.email
        refresh['full_name'] = user.full_name
        refresh['user_type'] = user.user_type
        if user.site:
            refresh['site_id'] = str(user.site.id)

        AuditLog.log(
            user=user,
            action='LOGIN',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            site=user.site
        )

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })


class MeView(APIView):
    # Critical: both web and mobile call this at app bootstrap to resolve
    # user_type and route accordingly — must never be blocked by the
    # registration-fee gate, or unpaid students couldn't even load the app.
    fee_gate_exempt = True

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        # Deliberately NOT UserUpdateSerializer here — that one also exposes
        # user_type/site/is_active, which would let any authenticated user
        # self-promote to ADMIN via this exact endpoint.
        serializer = SelfProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': 'Mot de passe actuel incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        
        return Response({'detail': 'Mot de passe modifié avec succès'})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('site').all()
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering_fields = ['last_name', 'first_name', 'date_joined']
    filterset_fields = ['user_type', 'is_active', 'site']

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        # Permanent deletion — cascades to the linked Student/Teacher/Parent
        # profile (OneToOneField(..., on_delete=CASCADE)) and everything
        # under it (enrollments, grades, attendance...). Invoice.student is
        # on_delete=PROTECT specifically so a student with any billing
        # history can't be silently wiped this way — surface that as a
        # clear 400 instead of DRF's generic 500, telling the admin to
        # deactivate instead when they hit it.
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({
                'detail': "Impossible de supprimer définitivement : cet utilisateur a des factures ou d'autres "
                          "données financières liées. Désactivez le compte à la place."
            })

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        user = self.get_object()
        new_password = request.data.get('password', '').strip()
        if len(new_password) < 6:
            return Response(
                {'detail': 'Le mot de passe doit contenir au moins 6 caractères.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(new_password)
        user.save(update_fields=['password'])
        return Response({'detail': 'Mot de passe réinitialisé avec succès.'})

    @action(detail=True, methods=['post'])
    def assign_role(self, request, pk=None):
        user = self.get_object()
        role_id = request.data.get('role_id')
        site_id = request.data.get('site_id')
        
        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            return Response({'detail': 'Rôle non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        
        user_role, created = UserRole.objects.get_or_create(
            user=user,
            role=role,
            site_id=site_id,
            defaults={'is_active': True}
        )
        
        if not created:
            user_role.is_active = True
            user_role.save()
        
        return Response(UserRoleSerializer(user_role).data)

    @action(detail=True, methods=['post'])
    def remove_role(self, request, pk=None):
        user = self.get_object()
        role_id = request.data.get('role_id')
        site_id = request.data.get('site_id')
        
        try:
            user_role = UserRole.objects.get(user=user, role_id=role_id, site_id=site_id)
            user_role.is_active = False
            user_role.save()
            return Response({'detail': 'Rôle retiré'})
        except UserRole.DoesNotExist:
            return Response({'detail': 'Attribution non trouvée'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def add_site_access(self, request, pk=None):
        user = self.get_object()
        site_id = request.data.get('site_id')
        is_default = request.data.get('is_default', False)
        
        user_site, created = UserSite.objects.get_or_create(
            user=user,
            site_id=site_id,
            defaults={'is_default': is_default}
        )
        
        if not created and is_default:
            user_site.is_default = True
            user_site.save()
        
        return Response(UserSiteSerializer(user_site).data)

    @action(detail=True, methods=['post'])
    def remove_site_access(self, request, pk=None):
        user = self.get_object()
        site_id = request.data.get('site_id')
        
        try:
            user_site = UserSite.objects.get(user=user, site_id=site_id)
            user_site.delete()
            return Response({'detail': 'Accès au site retiré'})
        except UserSite.DoesNotExist:
            return Response({'detail': 'Accès non trouvé'}, status=status.HTTP_404_NOT_FOUND)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related('permissions').all()
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'code']
    filterset_fields = ['is_active', 'is_system']

    def get_serializer_class(self):
        if self.action == 'list':
            return RoleListSerializer
        return RoleSerializer

    def perform_destroy(self, instance):
        if instance.is_system:
            return Response(
                {'detail': 'Impossible de supprimer un rôle système'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.is_active = False
        instance.save()


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['code', 'name']
    filterset_fields = ['module', 'is_active']
