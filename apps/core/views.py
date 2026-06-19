from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Site, AcademicYear, AuditLog, SystemConfig
from .serializers import (
    SiteSerializer, SiteListSerializer,
    AcademicYearSerializer, AuditLogSerializer,
    SystemConfigSerializer, SystemConfigPublicSerializer
)


class SiteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Sites/Campus."""
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'code', 'city']
    ordering_fields = ['name', 'created_at']
    filterset_fields = ['is_active', 'is_main', 'city']

    def get_permissions(self):
        # Permettre l'accès en lecture sans authentification
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'list':
            return SiteListSerializer
        return SiteSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class AcademicYearViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Academic Years."""
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['start_date', 'name']
    filterset_fields = ['is_active', 'is_current', 'registration_open']

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get the current academic year."""
        current_year = AcademicYear.get_current()
        if current_year:
            serializer = self.get_serializer(current_year)
            return Response(serializer.data)
        return Response(
            {'detail': 'Aucune année académique en cours'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=True, methods=['post'])
    def set_current(self, request, pk=None):
        """Set an academic year as current."""
        academic_year = self.get_object()
        academic_year.is_current = True
        academic_year.save()
        return Response(self.get_serializer(academic_year).data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing Audit Logs (read-only)."""
    queryset = AuditLog.objects.select_related('user', 'site').all()
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['object_repr', 'model_name']
    ordering_fields = ['timestamp']
    filterset_fields = ['action', 'model_name', 'user', 'site']


class SystemConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for managing System Configurations."""
    queryset = SystemConfig.objects.all()
    serializer_class = SystemConfigSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['key', 'description']
    filterset_fields = ['is_active', 'is_public', 'site']

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def public(self, request):
        """Get public configurations."""
        configs = SystemConfig.objects.filter(is_public=True, is_active=True)
        serializer = SystemConfigPublicSerializer(configs, many=True)
        return Response(serializer.data)
