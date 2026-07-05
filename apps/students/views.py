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
    # profile/financial summary (fee-gated on everything else — see
    # apps.students.permissions.IsRegistrationFeePaidOrExempt).
    fee_gate_exempt_actions = ('me', 'financial_summary')

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
        """Compute real financial totals from invoices, with FeeConfiguration as fallback."""
        from apps.finance.models import Invoice, Payment, FeeConfiguration
        from django.db.models import Sum

        student = self.get_object()
        self._check_own_student_access(request, student)
        invoices = Invoice.objects.filter(student=student, is_active=True)

        total_tuition  = float(invoices.aggregate(t=Sum('total'))['t']       or 0)
        total_paid     = float(invoices.aggregate(p=Sum('amount_paid'))['p'] or 0)
        # Use sum of actual invoice balances for remaining (more accurate than computed)
        total_balance  = float(invoices.aggregate(b=Sum('balance'))['b']     or 0)

        # Separate tuition-only vs inscription totals using fee_type codes
        inscription_invoice_ids = list(
            invoices.filter(items__fee_type__code__iregex=r'inscri|reg')
            .distinct().values_list('id', flat=True)
        )
        inscription_qs = invoices.filter(id__in=inscription_invoice_ids)
        total_registration_invoiced = float(inscription_qs.aggregate(t=Sum('total'))['t'] or 0)
        total_tuition_only          = total_tuition - total_registration_invoiced

        # Registration paid = student flag OR inscription invoice fully paid (balance = 0)
        reg_balance = float(inscription_qs.aggregate(b=Sum('balance'))['b'] or 0) if inscription_invoice_ids else None
        dynamic_reg_paid = reg_balance is not None and reg_balance <= 0
        registration_fee_paid = student.registration_fee_paid or dynamic_reg_paid

        # Auto-sync the student flag so getMe() stays consistent
        if dynamic_reg_paid and not student.registration_fee_paid:
            Student.objects.filter(pk=student.pk).update(registration_fee_paid=True)

        total_pending  = float(
            Payment.objects.filter(
                invoice__student=student, status='PENDING', is_active=True
            ).aggregate(p=Sum('amount'))['p'] or 0
        )
        # Use configured amount as base when no invoices exist yet
        has_invoices = invoices.exists()

        # Look up FeeConfiguration — try enrollment level first, fall back to site-only
        import logging
        logger = logging.getLogger(__name__)
        configured_tuition = float(student.tuition_fee or 0)
        configured_registration = float(student.registration_fee or 0)
        try:
            # Use values_list to avoid cross-table JOINs (collation-safe)
            enrollment_row = student.enrollments.filter(
                is_active=True
            ).order_by('-created_at').values_list(
                'class_obj_id', 'academic_year_id'
            ).first()
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
            # Always attempt lookup — get_for_enrollment falls back to site-only when level=None
            fee_config = FeeConfiguration.get_for_enrollment(
                student.site, level, academic_year,
                modality=student.modality, affectation_status=student.affectation_status
            )
            if fee_config:
                configured_tuition = float(fee_config.tuition_fee)
                configured_registration = float(fee_config.registration_fee)
            else:
                level_id = str(level.id) if level else None
                year_id = str(academic_year.id) if academic_year else None
                logger.info(
                    'financial_summary: no fee config | site_id=%s | level_id=%s (%s) | year_id=%s (%s) | all_configs=%s',
                    student.site_id, level_id, level, year_id, academic_year,
                    list(FeeConfiguration.objects.filter(is_active=True).values('id', 'site_id', 'level_id', 'academic_year_id', 'registration_fee', 'tuition_fee'))
                )
        except Exception as e:
            logger.error('financial_summary: unexpected error: %s', e, exc_info=True)

        # Grand total (scolarité + inscription)
        effective_tuition = total_tuition if has_invoices else (configured_tuition + configured_registration)
        # Tuition only (scolarité, sans inscription)
        effective_tuition_only = total_tuition_only if has_invoices else configured_tuition
        # Remaining: use actual invoice balances when invoices exist (always accurate)
        remaining = total_balance if has_invoices else max(0.0, effective_tuition - total_paid)

        from apps.finance.models import compute_tuition_schedule_status
        schedule_status = compute_tuition_schedule_status(student)

        return Response({
            'tuition_fee':              effective_tuition,           # grand total all fees
            'tuition_fee_only':         effective_tuition_only,      # scolarité uniquement
            'total_paid':               total_paid,
            'remaining_balance':        remaining,
            'total_pending':            total_pending,
            'registration_fee':         configured_registration,
            'registration_fee_paid':    registration_fee_paid,       # computed from invoices + student flag
            'configured_tuition_fee':   configured_tuition,
            'configured_registration_fee': configured_registration,
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
        """Create inscription and/or scolarité invoices if they don't exist yet."""
        import logging
        from apps.finance.models import Invoice, InvoiceItem, FeeType, FeeConfiguration
        from apps.finance.serializers import InvoiceListSerializer
        from apps.core.models import AcademicYear
        from datetime import date, timedelta

        logger = logging.getLogger(__name__)
        student = self.get_object()

        try:
            # Use current year, fall back to most recent
            current_year = AcademicYear.get_current()
            if not current_year:
                current_year = AcademicYear.objects.filter(is_active=True).order_by('-start_date').first()
            if not current_year:
                current_year = AcademicYear.objects.order_by('-start_date').first()
            if not current_year:
                return Response(
                    {'detail': 'Aucune année académique trouvée. Veuillez en créer une dans l\'administration.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Site fallback
            site = student.site
            if not site:
                from apps.core.models import Site
                site = Site.objects.filter(is_active=True).first()
            if not site:
                return Response(
                    {'detail': 'Aucun site trouvé pour cet étudiant.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Resolve fee amounts: FeeConfiguration → Student fields
            enrollment_row = student.enrollments.filter(is_active=True).values_list(
                'class_obj_id', 'academic_year_id'
            ).first()
            level = None
            try:
                if enrollment_row and enrollment_row[0]:
                    from apps.academic.models import Class as AcademicClass
                    class_obj = AcademicClass.objects.select_related('level').get(pk=enrollment_row[0])
                    level = class_obj.level
            except Exception as e:
                logger.warning('prepare_invoices: cannot resolve level: %s', e)

            fee_config = FeeConfiguration.get_for_enrollment(
                site, level, current_year,
                modality=student.modality, affectation_status=student.affectation_status
            )
            tuition_amount = float(fee_config.tuition_fee if fee_config else (student.tuition_fee or 0))
            reg_amount = float(fee_config.registration_fee if fee_config else (student.registration_fee or 0))

            logger.info(
                'prepare_invoices: student=%s site=%s year=%s tuition=%.0f reg=%.0f fee_config=%s',
                student.matricule, site, current_year, tuition_amount, reg_amount, fee_config
            )

            due_date = (current_year.end_date if hasattr(current_year, 'end_date') and current_year.end_date
                        else date.today() + timedelta(days=90))

            scolarite_ft, _ = FeeType.objects.get_or_create(
                code='SCOLARITE',
                defaults={'name': 'Frais de scolarité', 'is_recurring': True, 'default_amount': tuition_amount}
            )
            inscription_ft, _ = FeeType.objects.get_or_create(
                code='INSCRIPTION',
                defaults={'name': "Frais d'inscription", 'is_recurring': False, 'default_amount': reg_amount}
            )

            created = 0

            # Scolarité invoice
            if tuition_amount > 0:
                tuition_exists = Invoice.objects.filter(
                    student=student, items__fee_type=scolarite_ft, is_active=True
                ).exists()
                if not tuition_exists:
                    inv = Invoice(student=student, site=site, academic_year=current_year,
                                  due_date=due_date, created_by=request.user)
                    inv.save()
                    InvoiceItem.objects.create(
                        invoice=inv, fee_type=scolarite_ft,
                        description=f'Frais de scolarité — {current_year.name}',
                        quantity=1, unit_price=int(tuition_amount)
                    )
                    inv.save()  # recalculate totals after items
                    # First save set status='PAID' (balance=0, no items) — fix it
                    if inv.balance > 0 and inv.status == 'PAID':
                        Invoice.objects.filter(pk=inv.pk).update(status='DRAFT')
                        inv.status = 'DRAFT'
                    created += 1
                    logger.info('prepare_invoices: created tuition invoice %s status=%s total=%s', inv.invoice_number, inv.status, inv.total)

            # Inscription invoice (only if not already paid)
            if reg_amount > 0 and not student.registration_fee_paid:
                reg_exists = Invoice.objects.filter(
                    student=student, items__fee_type=inscription_ft, is_active=True
                ).exists()
                if not reg_exists:
                    inv = Invoice(student=student, site=site, academic_year=current_year,
                                  due_date=due_date, created_by=request.user)
                    inv.save()
                    InvoiceItem.objects.create(
                        invoice=inv, fee_type=inscription_ft,
                        description=f"Frais d'inscription — {current_year.name}",
                        quantity=1, unit_price=int(reg_amount)
                    )
                    inv.save()  # recalculate totals after items
                    if inv.balance > 0 and inv.status == 'PAID':
                        Invoice.objects.filter(pk=inv.pk).update(status='DRAFT')
                        inv.status = 'DRAFT'
                    created += 1
                    logger.info('prepare_invoices: created registration invoice %s status=%s total=%s', inv.invoice_number, inv.status, inv.total)

            all_invoices = Invoice.objects.filter(
                student=student, is_active=True
            ).prefetch_related('items__fee_type', 'payments')
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
