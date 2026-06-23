from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Parent, Student, StudentParent, StudentFile, StudentCard
from .serializers import (
    ParentSerializer, ParentListSerializer,
    StudentSerializer, StudentCreateSerializer, StudentListSerializer,
    StudentDossierSerializer, StudentParentSerializer,
    StudentFileSerializer, StudentCardSerializer
)


class ParentViewSet(viewsets.ModelViewSet):
    queryset = Parent.objects.select_related('user').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'user__phone']
    ordering_fields = ['user__last_name', 'created_at']
    filterset_fields = ['is_active', 'relationship']

    def get_serializer_class(self):
        if self.action == 'list':
            return ParentListSerializer
        return ParentSerializer

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        parent = self.get_object()
        student_parents = parent.parent_students.select_related('student__user')
        students = [sp.student for sp in student_parents]
        serializer = StudentListSerializer(students, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        parent = self.get_object()
        new_password = request.data.get('password', '').strip()
        if len(new_password) < 6:
            return Response(
                {'detail': 'Le mot de passe doit contenir au moins 6 caractères.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        parent.user.set_password(new_password)
        parent.user.save()
        return Response({'detail': 'Mot de passe réinitialisé avec succès.'})

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Get the parent profile of the currently authenticated user."""
        try:
            parent = Parent.objects.select_related('user').get(user=request.user)
            serializer = ParentSerializer(parent)
            return Response(serializer.data)
        except Parent.DoesNotExist:
            return Response({'detail': 'Profil parent non trouvé.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='me/students')
    def my_students(self, request):
        """Get all students linked to the currently authenticated parent."""
        try:
            parent = Parent.objects.select_related('user').get(user=request.user)
            student_parents = parent.parent_students.select_related('student__user', 'student__site')
            students = [sp.student for sp in student_parents]
            serializer = StudentDossierSerializer(students, many=True)
            return Response(serializer.data)
        except Parent.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)


class StudentViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['matricule', 'user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['user__last_name', 'matricule', 'admission_date']
    filterset_fields = ['status', 'is_active', 'site', 'gender']

    def get_queryset(self):
        base = Student.objects.select_related('user', 'site')
        if self.action == 'list':
            from django.db.models import Prefetch
            from apps.academic.models import Enrollment
            return base.prefetch_related(
                Prefetch(
                    'enrollments',
                    queryset=Enrollment.objects.filter(
                        status='ENROLLED', is_active=True
                    ).select_related('class_obj__level__program'),
                    to_attr='active_enrollments',
                )
            )
        return base.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return StudentListSerializer
        if self.action == 'create':
            return StudentCreateSerializer
        if self.action in ('dossier', 'me'):
            return StudentDossierSerializer
        return StudentSerializer

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        try:
            student = Student.objects.select_related('user', 'site').get(user=request.user)
            serializer = StudentDossierSerializer(student)
            return Response(serializer.data)
        except Student.DoesNotExist:
            return Response({'detail': 'Profil étudiant non trouvé.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def dossier(self, request, pk=None):
        student = self.get_object()
        serializer = StudentDossierSerializer(student)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='link-parent')
    def link_parent(self, request, pk=None):
        student = self.get_object()
        parent_id = request.data.get('parent_id')
        is_primary = request.data.get('is_primary', False)
        can_pickup = request.data.get('can_pickup', True)
        receives_notifications = request.data.get('receives_notifications', True)

        try:
            parent = Parent.objects.get(id=parent_id)
        except Parent.DoesNotExist:
            return Response(
                {'detail': 'Parent non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

        student_parent, created = StudentParent.objects.get_or_create(
            student=student,
            parent=parent,
            defaults={
                'is_primary': is_primary,
                'can_pickup': can_pickup,
                'receives_notifications': receives_notifications
            }
        )

        if not created:
            student_parent.is_primary = is_primary
            student_parent.can_pickup = can_pickup
            student_parent.receives_notifications = receives_notifications
            student_parent.save()

        return Response(StudentParentSerializer(student_parent).data)

    @action(detail=True, methods=['post'], url_path='unlink-parent')
    def unlink_parent(self, request, pk=None):
        student = self.get_object()
        parent_id = request.data.get('parent_id')

        try:
            student_parent = StudentParent.objects.get(
                student=student, parent_id=parent_id
            )
            student_parent.delete()
            return Response({'detail': 'Lien supprimé'})
        except StudentParent.DoesNotExist:
            return Response(
                {'detail': 'Lien non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        student = self.get_object()
        files = student.files.all()
        
        file_type = request.query_params.get('type')
        if file_type:
            files = files.filter(file_type=file_type)
        
        academic_year_id = request.query_params.get('academic_year_id')
        if academic_year_id:
            files = files.filter(academic_year_id=academic_year_id)
        
        serializer = StudentFileSerializer(files, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='add-file')
    def add_file(self, request, pk=None):
        student = self.get_object()
        serializer = StudentFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(student=student, created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def card(self, request, pk=None):
        student = self.get_object()
        from apps.core.models import AcademicYear
        
        academic_year_id = request.query_params.get('academic_year_id')
        if academic_year_id:
            card = student.cards.filter(academic_year_id=academic_year_id).first()
        else:
            current_year = AcademicYear.get_current()
            if current_year:
                card = student.cards.filter(academic_year=current_year).first()
            else:
                card = student.cards.order_by('-created_at').first()
        
        if card:
            return Response(StudentCardSerializer(card).data)
        return Response(
            {'detail': 'Carte non trouvée'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(detail=True, methods=['post'], url_path='generate-card')
    def generate_card(self, request, pk=None):
        student = self.get_object()
        from apps.core.models import AcademicYear
        import qrcode
        from io import BytesIO
        from django.core.files.base import ContentFile
        import json

        academic_year_id = request.data.get('academic_year_id')
        expiry_date = request.data.get('expiry_date')

        if academic_year_id:
            try:
                academic_year = AcademicYear.objects.get(id=academic_year_id)
            except AcademicYear.DoesNotExist:
                return Response(
                    {'detail': 'Année académique non trouvée'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            academic_year = AcademicYear.get_current()
            if not academic_year:
                return Response(
                    {'detail': 'Aucune année académique en cours'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        card, created = StudentCard.objects.get_or_create(
            student=student,
            academic_year=academic_year,
            defaults={
                'expiry_date': expiry_date or academic_year.end_date,
                'is_valid': True
            }
        )

        qr_data = json.dumps({
            'type': 'student_card',
            'card_number': card.card_number,
            'student_id': str(student.id),
            'matricule': student.matricule
        })
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        card.qr_code.save(f'{card.card_number}.png', ContentFile(buffer.getvalue()))

        return Response(StudentCardSerializer(card).data)

    @action(detail=True, methods=['get'], url_path='financial-summary')
    def financial_summary(self, request, pk=None):
        """Compute real financial totals from invoices, with FeeConfiguration as fallback."""
        from apps.finance.models import Invoice, Payment, FeeConfiguration
        from django.db.models import Sum

        student = self.get_object()
        invoices = Invoice.objects.filter(student=student, is_active=True)

        total_tuition  = float(invoices.aggregate(t=Sum('total'))['t']       or 0)
        total_paid     = float(invoices.aggregate(p=Sum('amount_paid'))['p'] or 0)
        total_pending  = float(
            Payment.objects.filter(
                invoice__student=student, status='PENDING', is_active=True
            ).aggregate(p=Sum('amount'))['p'] or 0
        )
        remaining = max(0.0, total_tuition - total_paid)

        # Look up FeeConfiguration for the student's active enrollment
        configured_tuition = float(student.tuition_fee or 0)
        configured_registration = float(student.registration_fee or 0)
        try:
            enrollment = student.enrollments.filter(
                is_active=True
            ).select_related('class_obj__level', 'academic_year').order_by('-created_at').first()
            if enrollment:
                level = enrollment.class_obj.level if enrollment.class_obj else None
                fee_config = FeeConfiguration.get_for_enrollment(
                    student.site, level, enrollment.academic_year
                )
                if fee_config:
                    configured_tuition = float(fee_config.tuition_fee)
                    configured_registration = float(fee_config.registration_fee)
        except Exception:
            pass

        return Response({
            'tuition_fee':              total_tuition or configured_tuition,
            'total_paid':               total_paid,
            'remaining_balance':        remaining,
            'total_pending':            total_pending,
            'registration_fee':         configured_registration,
            'registration_fee_paid':    student.registration_fee_paid,
            'configured_tuition_fee':   configured_tuition,
            'configured_registration_fee': configured_registration,
        })


class StudentFileViewSet(viewsets.ModelViewSet):
    queryset = StudentFile.objects.select_related('student', 'academic_year', 'created_by').all()
    serializer_class = StudentFileSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'file_type']
    filterset_fields = ['student', 'academic_year', 'file_type', 'is_active']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class StudentCardViewSet(viewsets.ModelViewSet):
    queryset = StudentCard.objects.select_related('student', 'academic_year').all()
    serializer_class = StudentCardSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['issue_date', 'expiry_date']
    filterset_fields = ['student', 'academic_year', 'is_valid', 'is_active']
