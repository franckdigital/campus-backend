from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import StaffProfile, StaffExperience, StaffDocument
from .serializers import (
    StaffProfileSerializer, StaffProfileCreateSerializer,
    StaffListSerializer, StaffExperienceSerializer, StaffDocumentSerializer,
)


class StaffViewSet(viewsets.ModelViewSet):
    queryset = StaffProfile.objects.select_related('user', 'site', 'academic_year').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['user__first_name', 'user__last_name', 'employee_id', 'department', 'position']
    filterset_fields = ['department', 'contract_type', 'is_active', 'site']
    ordering_fields = ['user__last_name', 'hire_date', 'department']

    def get_serializer_class(self):
        if self.action == 'list':
            return StaffListSerializer
        if self.action == 'create':
            return StaffProfileCreateSerializer
        return StaffProfileSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ('true', '1', 'yes'))
        return qs

    @action(detail=True, methods=['get'], url_path='profil')
    def profil(self, request, pk=None):
        staff = self.get_object()
        user = staff.user
        experiences = staff.experiences.all()
        exp_data = [
            {
                'id': str(e.id),
                'position': e.position,
                'company': e.company,
                'start_date': e.start_date.strftime('%Y-%m-%d') if e.start_date else None,
                'end_date': e.end_date.strftime('%Y-%m-%d') if e.end_date else None,
                'is_current': e.is_current,
                'description': e.description,
            }
            for e in experiences
        ]
        monthly_hours = (staff.contract_hours_per_week * 4) if staff.contract_hours_per_week else None
        return Response({
            'id': str(staff.id),
            'employee_id': staff.employee_id,
            'full_name': user.full_name,
            'email': user.email,
            'phone': getattr(user, 'phone', ''),
            'department': staff.department,
            'position': staff.position,
            'hire_date': staff.hire_date.strftime('%Y-%m-%d') if staff.hire_date else None,
            'contract_type': staff.contract_type,
            'site_name': staff.site.name if staff.site else None,
            'academic_year': str(staff.academic_year_id) if staff.academic_year_id else None,
            'academic_year_name': staff.academic_year.name if staff.academic_year_id else None,
            'contract_hours_per_week': staff.contract_hours_per_week,
            'monthly_hours': monthly_hours,
            'bio': staff.bio,
            'is_active': staff.is_active,
            'experiences': exp_data,
        })

    @action(detail=True, methods=['get', 'post'], url_path='experiences')
    def experiences(self, request, pk=None):
        staff = self.get_object()
        if request.method == 'GET':
            return Response(StaffExperienceSerializer(staff.experiences.all(), many=True).data)
        serializer = StaffExperienceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(staff=staff)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='experiences/(?P<exp_id>[^/.]+)')
    def delete_experience(self, request, pk=None, exp_id=None):
        staff = self.get_object()
        try:
            exp = staff.experiences.get(pk=exp_id)
        except StaffExperience.DoesNotExist:
            return Response({'detail': 'Introuvable'}, status=status.HTTP_404_NOT_FOUND)
        exp.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'], url_path='documents')
    def documents(self, request, pk=None):
        staff = self.get_object()
        if request.method == 'GET':
            return Response(StaffDocumentSerializer(staff.documents.all(), many=True, context={'request': request}).data)
        serializer = StaffDocumentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(staff=staff, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='documents/(?P<doc_id>[^/.]+)')
    def delete_document(self, request, pk=None, doc_id=None):
        staff = self.get_object()
        try:
            doc = staff.documents.get(pk=doc_id)
        except StaffDocument.DoesNotExist:
            return Response({'detail': 'Document introuvable'}, status=status.HTTP_404_NOT_FOUND)
        doc.file.delete(save=False)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='fiche',
            permission_classes=[], authentication_classes=[])
    def fiche(self, request, pk=None):
        from django.http import HttpResponse
        import html as html_mod
        import logging
        logger = logging.getLogger(__name__)

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        token_str = request.query_params.get('token', '')
        jwt_token = token_str or (auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else '')
        if jwt_token:
            try:
                from rest_framework_simplejwt.authentication import JWTAuthentication
                jwt_auth = JWTAuthentication()
                validated = jwt_auth.get_validated_token(jwt_token)
                user = jwt_auth.get_user(validated)
            except Exception:
                from rest_framework.response import Response as DRFResponse
                return DRFResponse({'detail': 'Token invalide'}, status=401)
        else:
            from rest_framework.response import Response as DRFResponse
            return DRFResponse({'detail': 'Non autorisé'}, status=401)

        try:
            staff = StaffProfile.objects.select_related('user', 'site', 'academic_year').prefetch_related('experiences').get(pk=pk)
        except StaffProfile.DoesNotExist:
            from rest_framework.response import Response as DRFResponse
            return DRFResponse({'detail': 'Introuvable'}, status=404)

        try:
            from .staff_pdf_utils import generate_staff_fiche_html
            html = generate_staff_fiche_html(staff)
            return HttpResponse(html, content_type='text/html; charset=utf-8')
        except Exception as exc:
            logger.exception('Erreur génération fiche staff: %s', exc)
            return HttpResponse(
                f'<html><body><h2 style="color:red">Erreur</h2><pre>{html_mod.escape(str(exc))}</pre></body></html>',
                content_type='text/html; charset=utf-8', status=500,
            )
