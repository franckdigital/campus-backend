from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
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
    # A student whose registration fee is unpaid may still check their own
    # profile/financial summary, and MUST be able to call prepare_invoices —
    # that's the action that generates their very first invoices (including
    # the registration one), so gating it behind "registration already paid"
    # would make it impossible to ever pay in the first place. Fee-gated on
    # everything else — see apps.students.permissions.IsEnrolledOrExempt.
    fee_gate_exempt_actions = ('me', 'financial_summary', 'prepare_invoices', 'echeancier')

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

    @staticmethod
    def _check_own_student_access(request, student):
        """financial_summary/dossier expose a student's private data by pk with
        no other filtering — restrict to admin/staff, the student themselves,
        or a parent actually linked to that student (not just any parent)."""
        user = request.user
        if user.user_type in ('ADMIN', 'STAFF'):
            return
        if user.user_type == 'STUDENT' and student.user_id == user.id:
            return
        if user.user_type == 'PARENT':
            if StudentParent.objects.filter(student=student, parent__user=user).exists():
                return
        raise PermissionDenied("Vous n'êtes pas autorisé à consulter ces informations.")

    @action(detail=True, methods=['get'])
    def dossier(self, request, pk=None):
        student = self.get_object()
        self._check_own_student_access(request, student)
        serializer = StudentDossierSerializer(student)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='kpi-analysis')
    def kpi_analysis(self, request, pk=None):
        student = self.get_object()
        self._check_own_student_access(request, student)

        from apps.academic.models import Semester
        from apps.analytics.services import get_or_generate_analysis

        semester = None
        semester_id = request.query_params.get('semester')
        if semester_id:
            semester = Semester.objects.filter(id=semester_id).first()

        # Only admin/staff can trigger a paid LLM regeneration — parents and
        # students always get whatever is already cached.
        refresh = (
            request.query_params.get('refresh') == 'true'
            and request.user.user_type in ('ADMIN', 'STAFF')
        )

        data = get_or_generate_analysis(student, semester=semester, refresh=refresh)
        return Response(data)

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

    @action(detail=True, methods=['get'], url_path='enrollments')
    def enrollments(self, request, pk=None):
        from apps.academic.models import Enrollment
        from apps.academic.serializers import EnrollmentSerializer
        student = self.get_object()
        qs = student.enrollments.filter(
            is_active=True
        ).select_related('class_obj__level__program', 'academic_year')
        return Response(EnrollmentSerializer(qs, many=True).data)

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
        """Compute real financial totals from invoices, with FeeConfiguration as fallback.

        Frais d'inscription and frais de scolarité used to be tracked as two
        separate totals here; they're merged into a single "scolarité" total
        now — a student is "inscrit" once their cumulative tuition paid
        crosses the configurable minimum (get_min_enrollment_payment), not
        once a separate inscription invoice is settled in full.
        """
        from apps.finance.models import (
            Invoice, Payment, FeeConfiguration, resolve_current_enrollment,
            compute_tuition_schedule_status, sync_enrollment_status,
            get_min_enrollment_payment,
        )
        from django.db.models import Sum

        student = self.get_object()
        self._check_own_student_access(request, student)
        invoices = Invoice.objects.filter(student=student, is_active=True)

        total_tuition  = float(invoices.aggregate(t=Sum('total'))['t']       or 0)
        total_paid     = float(invoices.aggregate(p=Sum('amount_paid'))['p'] or 0)
        total_balance  = float(invoices.aggregate(b=Sum('balance'))['b']     or 0)

        total_pending  = float(
            Payment.objects.filter(
                invoice__student=student, status='PENDING', is_active=True
            ).aggregate(p=Sum('amount'))['p'] or 0
        )
        has_invoices = invoices.exists()

        # Look up FeeConfiguration — try enrollment level first, fall back to site-only
        import logging
        logger = logging.getLogger(__name__)
        configured_tuition = float(student.tuition_fee or 0)
        tuition_config = None
        try:
            # Same resolver as ensure_student_invoices/_resolve_fee_config_for_student
            # (apps.finance.models) — status=ENROLLED + most-recent, so this can never
            # again disagree with which barème actually priced the student's invoices.
            enrollment_row = resolve_current_enrollment(student)
            level = None
            academic_year = None
            if enrollment_row:
                class_obj_id, academic_year_id = enrollment_row
                if class_obj_id:
                    from apps.academic.models import Class as AcademicClass, AcademicYear
                    try:
                        class_obj = AcademicClass.objects.select_related('level').get(pk=class_obj_id)
                        level = class_obj.level
                    except Exception as e:
                        logger.warning('financial_summary: cannot load class %s: %s', class_obj_id, e)
                if academic_year_id:
                    from apps.core.models import AcademicYear
                    try:
                        academic_year = AcademicYear.objects.get(pk=academic_year_id)
                    except Exception as e:
                        logger.warning('financial_summary: cannot load academic_year %s: %s', academic_year_id, e)
            # Always attempt lookup — get_for_enrollment falls back to site-only when level=None.
            tuition_config = FeeConfiguration.get_for_enrollment(
                student.site, level, 'SCOLARITE', academic_year,
                modality=student.modality, affectation_status=student.affectation_status
            )
            if tuition_config:
                configured_tuition = float(tuition_config.amount)
            elif not has_invoices:
                level_id = str(level.id) if level else None
                year_id = str(academic_year.id) if academic_year else None
                logger.info(
                    'financial_summary: no fee config | site_id=%s | level_id=%s (%s) | year_id=%s (%s) | all_configs=%s',
                    student.site_id, level_id, level, year_id, academic_year,
                    list(FeeConfiguration.objects.filter(is_active=True).values('id', 'site_id', 'level_id', 'academic_year_id', 'fee_category', 'amount'))
                )
        except Exception as e:
            logger.error('financial_summary: unexpected error: %s', e, exc_info=True)

        # Prefer the real invoiced total once billed; fall back to the live
        # barème guess only when nothing has been invoiced yet.
        effective_tuition = total_tuition if has_invoices else configured_tuition
        remaining = total_balance if has_invoices else configured_tuition

        schedule_status = compute_tuition_schedule_status(student)
        is_enrolled = sync_enrollment_status(student)

        # Human-readable name of whichever barème actually priced this student
        # — shown read-only in the student form/dossier so an admin can see
        # e.g. "Barème Licence 3" was applied via cycle, not just a number.
        tuition_config_label = None
        if tuition_config:
            tuition_config_label = tuition_config.label or (
                f"Cycle : {tuition_config.get_cycle_display()}" if tuition_config.cycle
                else tuition_config.level.name if tuition_config.level
                else tuition_config.program.name if tuition_config.program
                else 'Barème général'
            )

        return Response({
            'tuition_fee':              effective_tuition,
            'total_paid':               total_paid,
            'remaining_balance':        remaining,
            'total_pending':            total_pending,
            'is_enrolled':              is_enrolled,                 # computed from invoices, self-healing
            'min_enrollment_payment':   float(get_min_enrollment_payment()),
            'configured_tuition_fee':   configured_tuition,
            'tuition_config_label':     tuition_config_label,
            'has_invoices':             has_invoices,
            'has_payment_schedule':     schedule_status['has_schedule'],
            'tuition_up_to_date':       schedule_status['is_up_to_date'],
            'echeance_override':        schedule_status['echeance_override'],
            'cumulative_due':           float(schedule_status['cumulative_due']),
            'cumulative_paid':          float(schedule_status['cumulative_paid']),
        })

    @action(detail=True, methods=['get'], url_path='echeancier')
    def echeancier(self, request, pk=None):
        """Per-installment breakdown of this student's échéancier de scolarité
        — powers the schedule table shown in the admin dossier's Paiements tab."""
        from apps.finance.models import get_student_installment_schedule

        student = self.get_object()
        self._check_own_student_access(request, student)
        schedule = get_student_installment_schedule(student)

        return Response({
            'has_schedule': schedule['has_schedule'],
            'total': float(schedule['total']),
            'cumulative_paid': float(schedule['cumulative_paid']),
            'echeance_override': bool(student.echeance_override),
            'installments': [
                {
                    'id': row['id'],
                    'label': row['label'],
                    'due_date': row['due_date'],
                    'amount': float(row['amount']),
                    'cumulative_due': float(row['cumulative_due']),
                    'status': row['status'],
                }
                for row in schedule['installments']
            ],
        })

    @action(detail=True, methods=['post'], url_path='prepare-invoices')
    def prepare_invoices(self, request, pk=None):
        """Create the student's scolarité invoice if it doesn't exist yet.

        Delegates to apps.finance.models.ensure_student_invoices, which is
        also called automatically by the Enrollment/Student post_save signals
        (apps.finance.signals) — this action stays for an explicit "Préparer
        mon dossier" click and to surface real errors (missing academic year
        / site) instead of the signals' best-effort silent skip.
        """
        import logging
        from apps.core.models import AcademicYear, Site
        from apps.finance.models import ensure_student_invoices
        from apps.finance.serializers import InvoiceListSerializer

        logger = logging.getLogger(__name__)
        student = self.get_object()

        try:
            current_year = (
                AcademicYear.get_current()
                or AcademicYear.objects.filter(is_active=True).order_by('-start_date').first()
                or AcademicYear.objects.order_by('-start_date').first()
            )
            if not current_year:
                return Response(
                    {'detail': 'Aucune année académique trouvée. Veuillez en créer une dans l\'administration.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not student.site and not Site.objects.filter(is_active=True).exists():
                return Response(
                    {'detail': 'Aucun site trouvé pour cet étudiant.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            created, all_invoices = ensure_student_invoices(student, created_by=request.user)
            serializer = InvoiceListSerializer(all_invoices, many=True)
            return Response({'created': created, 'invoices': serializer.data})

        except Exception as e:
            logger.error('prepare_invoices: unexpected error for student %s: %s', pk, e, exc_info=True)
            return Response(
                {'detail': f'Erreur serveur : {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
