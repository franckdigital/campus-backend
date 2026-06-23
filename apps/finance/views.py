from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db.models import Sum

from .models import (
    FeeType, Invoice, InvoiceItem, PaymentMethod, Payment,
    CashRegister, CashSession, CashTransaction, BankAccount, Expense,
    FeeConfiguration
)
from .serializers import (
    FeeTypeSerializer, InvoiceSerializer, InvoiceListSerializer,
    InvoiceCreateSerializer, InvoiceItemSerializer,
    PaymentMethodSerializer, PaymentSerializer,
    CashRegisterSerializer, CashSessionSerializer, CashSessionListSerializer,
    CashTransactionSerializer, CashPaymentSerializer,
    BankAccountSerializer, ExpenseSerializer,
    FeeConfigurationSerializer
)


class FeeTypeViewSet(viewsets.ModelViewSet):
    queryset = FeeType.objects.all()
    serializer_class = FeeTypeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'code']
    filterset_fields = ['is_active', 'is_recurring']


class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'code']
    filterset_fields = ['is_active', 'is_online']


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related(
        'student__user', 'site', 'academic_year', 'created_by'
    ).prefetch_related('items', 'payments').all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['invoice_number', 'student__matricule', 'student__user__first_name']
    ordering_fields = ['issue_date', 'due_date', 'total', 'status']
    filterset_fields = ['student', 'site', 'academic_year', 'status', 'is_active']

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        if self.action == 'create':
            return InvoiceCreateSerializer
        return InvoiceSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def _create_enrollment_for_invoice(self, invoice):
        """
        Create enrollment for student when registration fee invoice is created.
        This method is called when an invoice item with registration fee is added.
        """
        from apps.academic.models import Enrollment, Class
        
        # Check if student already has enrollment for this academic year
        existing = Enrollment.objects.filter(
            student=invoice.student,
            academic_year=invoice.academic_year
        ).exists()
        
        if existing:
            return  # Already has enrollment
        
        # Find a class for the student
        # Option 1: Get from latest enrollment
        latest = invoice.student.enrollments.select_related('class_obj').order_by('-created_at').first()
        
        if latest:
            class_obj = latest.class_obj
        else:
            # Option 2: Get any active class from the same site
            class_obj = Class.objects.filter(
                site=invoice.site,
                academic_year=invoice.academic_year,
                is_active=True
            ).first()
        
        # Create enrollment if we found a class
        if class_obj:
            Enrollment.objects.create(
                student=invoice.student,
                class_obj=class_obj,
                academic_year=invoice.academic_year,
                status='ENROLLED',
                is_active=True
            )

    @action(detail=True, methods=['post'], url_path='add-item')
    def add_item(self, request, pk=None):
        invoice = self.get_object()
        serializer = InvoiceItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save(invoice=invoice)
        invoice.refresh_from_db()  # Refresh to get updated items relation
        invoice.save()  # This will trigger calculate_totals with the new item
        
        # Check if this is a registration fee and create enrollment
        if item.fee_type and 'inscription' in item.fee_type.code.lower():
            self._create_enrollment_for_invoice(invoice)
        
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status == 'DRAFT':
            invoice.status = 'SENT'
            invoice.save()
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status not in ['PAID', 'CANCELLED']:
            invoice.status = 'CANCELLED'
            invoice.save()
        return Response(InvoiceSerializer(invoice).data)
    
    @action(detail=True, methods=['get'], url_path='pdf',
            permission_classes=[], authentication_classes=[])
    def generate_pdf(self, request, pk=None):
        from django.http import HttpResponse
        from rest_framework.response import Response as DRFResponse
        import html as html_mod
        import logging
        logger = logging.getLogger(__name__)

        # Auth via ?token= query param or Authorization header
        user = None
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
                return DRFResponse({'detail': 'Token invalide ou expire'}, status=401)
        if not user or not getattr(user, 'is_authenticated', False):
            return DRFResponse({'detail': 'Non autorise'}, status=401)

        try:
            invoice = Invoice.objects.select_related(
                'student__user', 'site', 'academic_year'
            ).prefetch_related('items').get(pk=pk)
        except Invoice.DoesNotExist:
            return DRFResponse({'detail': 'Facture introuvable'}, status=404)

        try:
            from .pdf_utils import generate_invoice_html
            html = generate_invoice_html(invoice)
            return HttpResponse(html, content_type='text/html; charset=utf-8')
        except Exception as exc:
            logger.exception('Erreur generation facture HTML: %s', exc)
            return HttpResponse(
                f'<html><body style="font-family:sans-serif;padding:40px">'
                f'<h2 style="color:red">Erreur generation facture</h2>'
                f'<pre>{html_mod.escape(str(exc))}</pre>'
                f'</body></html>',
                content_type='text/html; charset=utf-8',
                status=500,
            )


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related(
        'invoice__student__user', 'payment_method', 'received_by', 'validated_by'
    ).all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['payment_number', 'reference', 'invoice__invoice_number']
    ordering_fields = ['payment_date', 'amount', 'status']
    filterset_fields = ['invoice', 'payment_method', 'status', 'is_active']

    def perform_create(self, serializer):
        payment = serializer.save(received_by=self.request.user)
        if payment.status == 'SUCCESS':
            payment.invoice.add_payment(payment.amount)
            self._maybe_create_cash_transaction(payment)

    def _maybe_create_cash_transaction(self, payment):
        """
        Si le mode de paiement est espèces et qu'une session de caisse est ouverte
        pour le site de la facture, enregistre automatiquement la transaction.
        """
        try:
            method = payment.payment_method
            if not method:
                return
            # Seuls les paiements en espèces physiques alimentent la caisse
            cash_codes = {'CASH', 'ESPECES', 'ESPECE', 'LIQUID', 'LIQUIDE'}
            if method.code.upper() not in cash_codes:
                return

            site = payment.invoice.site if payment.invoice else None

            # Cherche d'abord une session sur le site de la facture,
            # puis sur n'importe quel site si aucune n'est trouvée
            open_session = None
            if site:
                open_session = CashSession.objects.filter(
                    cash_register__site=site,
                    status='OPEN',
                    is_active=True,
                ).select_related('cash_register').first()
            if not open_session:
                open_session = CashSession.objects.filter(
                    status='OPEN',
                    is_active=True,
                ).select_related('cash_register').first()
            if not open_session:
                return  # pas de session ouverte → on ne force rien

            # Éviter les doublons si un CashTransaction lié à ce paiement existe déjà
            if CashTransaction.objects.filter(payment=payment).exists():
                return

            student_name = ''
            try:
                u = payment.invoice.student.user
                student_name = getattr(u, 'full_name', None) or u.get_full_name() or ''
            except Exception:
                pass

            CashTransaction.objects.create(
                session=open_session,
                payment=payment,
                transaction_type='IN',
                amount=payment.amount,
                description=f"Paiement {payment.invoice.invoice_number}"
                            + (f" – {student_name}" if student_name else ""),
                reference=payment.payment_number,
                recorded_by=self.request.user,
                is_active=True,
            )
        except Exception:
            pass  # ne jamais bloquer l'enregistrement du paiement

    def perform_update(self, serializer):
        from decimal import Decimal
        # Get the current payment from DB before any changes
        payment_id = self.get_object().pk
        old_payment = Payment.objects.get(pk=payment_id)
        old_amount = Decimal(str(old_payment.amount)) if old_payment.status == 'SUCCESS' else Decimal('0')
        
        # Save the updated payment
        payment = serializer.save()
        new_amount = Decimal(str(payment.amount)) if payment.status == 'SUCCESS' else Decimal('0')
        
        # Recalculate invoice totals based on difference
        if old_amount != new_amount:
            difference = new_amount - old_amount
            invoice = payment.invoice
            invoice.amount_paid = max(Decimal('0'), Decimal(str(invoice.amount_paid)) + difference)
            invoice.balance = Decimal(str(invoice.total)) - invoice.amount_paid
            if invoice.balance <= 0:
                invoice.status = 'PAID'
            elif invoice.amount_paid > 0:
                invoice.status = 'PARTIAL'
            invoice.save()

    def perform_destroy(self, instance):
        from decimal import Decimal
        invoice = instance.invoice
        # If payment was SUCCESS, subtract from invoice totals
        if instance.status == 'SUCCESS':
            invoice.amount_paid = max(Decimal('0'), Decimal(str(invoice.amount_paid)) - Decimal(str(instance.amount)))
            invoice.balance = Decimal(str(invoice.total)) - invoice.amount_paid
            if invoice.balance <= 0:
                invoice.status = 'PAID'
            elif invoice.amount_paid > 0:
                invoice.status = 'PARTIAL'
            else:
                invoice.status = 'PENDING'
            invoice.save()
        instance.delete()

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        payment = self.get_object()
        if payment.validate(request.user):
            # H2: Paiement validé → parents (multi-channel)
            try:
                from apps.notifications.services import notify_payment_validated
                notify_payment_validated(payment)
            except Exception:
                pass
            try:
                from apps.core.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='PAYMENT',
                    model_name='Payment',
                    object_id=str(payment.id),
                    object_repr=str(payment),
                    changes={
                        'amount': str(payment.amount),
                        'invoice': payment.invoice.invoice_number,
                        'student': payment.invoice.student.user.full_name if payment.invoice.student.user else '',
                        'status': 'validated',
                    },
                )
            except Exception:
                pass
            # F1: auto journal entry for validated payment
            try:
                from apps.accounting.models import AccountingAccount, JournalEntry, JournalLine
                site = payment.invoice.site
                revenue_account = AccountingAccount.objects.filter(
                    site=site, account_type='REVENUE', is_active=True
                ).first()
                asset_account = AccountingAccount.objects.filter(
                    site=site, account_type='ASSET', code__startswith='5', is_active=True
                ).first()
                if revenue_account and asset_account:
                    student_name = payment.invoice.student.user.full_name
                    entry = JournalEntry.objects.create(
                        site=site,
                        entry_date=payment.payment_date.date(),
                        description=f'Paiement: {payment.invoice.invoice_number}',
                        reference=payment.payment_number,
                        status='DRAFT',
                        created_by=request.user,
                        payment=payment,
                    )
                    JournalLine.objects.create(
                        journal_entry=entry, account=asset_account,
                        debit_amount=payment.amount, credit_amount=0,
                        description=f'Règlement {student_name}',
                    )
                    JournalLine.objects.create(
                        journal_entry=entry, account=revenue_account,
                        debit_amount=0, credit_amount=payment.amount,
                        description=f'Règlement {student_name}',
                    )
                    # Auto-post since the entry is balanced and derived from a validated payment
                    entry.post(request.user)
            except Exception:
                pass
            return Response(PaymentSerializer(payment).data)
        return Response(
            {'detail': 'Impossible de valider ce paiement'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['get'], url_path='receipt',
            permission_classes=[], authentication_classes=[])
    def receipt(self, request, pk=None):
        """Generate a PDF receipt for a payment."""
        from django.http import HttpResponse
        from rest_framework.response import Response as DRFResponse
        import html as html_mod
        import logging
        logger = logging.getLogger(__name__)

        # Auth via ?token= query param or Authorization header
        user = None
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
                return DRFResponse({'detail': 'Token invalide ou expire'}, status=401)
        if not user or not getattr(user, 'is_authenticated', False):
            return DRFResponse({'detail': 'Non autorise'}, status=401)

        payment = self.get_object()

        try:
            from .pdf_utils import generate_receipt_html
            html = generate_receipt_html(payment)
            return HttpResponse(html, content_type='text/html; charset=utf-8')
        except Exception as exc:
            logger.exception('Erreur generation recu HTML: %s', exc)
            return HttpResponse(
                f'<html><body style="font-family:sans-serif;padding:40px">'
                f'<h2 style="color:red">Erreur generation recu</h2>'
                f'<pre>{html_mod.escape(str(exc))}</pre>'
                f'</body></html>',
                content_type='text/html; charset=utf-8',
                status=500,
            )


class CashPaymentView(APIView):
    def post(self, request):
        serializer = CashPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        try:
            invoice = Invoice.objects.get(id=data['invoice_id'])
        except Invoice.DoesNotExist:
            return Response(
                {'detail': 'Facture non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            cash_session = CashSession.objects.get(
                id=data['cash_session_id'],
                status='OPEN'
            )
        except CashSession.DoesNotExist:
            return Response(
                {'detail': 'Session de caisse non trouvée ou fermée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        cash_method = PaymentMethod.objects.filter(code='CASH').first()
        if not cash_method:
            cash_method = PaymentMethod.objects.create(
                name='Espèces',
                code='CASH',
                is_online=False
            )
        
        payment = Payment.objects.create(
            invoice=invoice,
            payment_method=cash_method,
            amount=data['amount'],
            status='SUCCESS',
            reference=data.get('reference', ''),
            notes=data.get('notes', ''),
            received_by=request.user,
            validated_by=request.user,
            validated_at=timezone.now()
        )
        
        CashTransaction.objects.create(
            session=cash_session,
            payment=payment,
            transaction_type='IN',
            amount=data['amount'],
            description=f"Paiement facture {invoice.invoice_number}",
            reference=payment.payment_number,
            recorded_by=request.user
        )
        
        invoice.add_payment(data['amount'])

        # H2: Versement caisse → finance + compta (multi-channel)
        try:
            from apps.notifications.services import notify_cash_deposit
            notify_cash_deposit(transaction)
        except Exception:
            pass

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class CashRegisterViewSet(viewsets.ModelViewSet):
    queryset = CashRegister.objects.select_related('site').all()
    serializer_class = CashRegisterSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'code']
    filterset_fields = ['site', 'is_open', 'is_active']


class CashTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = CashTransactionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['session', 'transaction_type', 'is_active']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = CashTransaction.objects.select_related(
            'session', 'session__cash_register', 'payment', 'recorded_by'
        ).filter(is_active=True)
        site = self.request.query_params.get('site')
        if site:
            qs = qs.filter(session__cash_register__site_id=site)
        month = self.request.query_params.get('month')  # YYYY-MM
        year = self.request.query_params.get('year')    # YYYY
        if month:
            try:
                y, m = month.split('-')
                qs = qs.filter(created_at__year=int(y), created_at__month=int(m))
            except (ValueError, AttributeError):
                pass
        elif year:
            try:
                qs = qs.filter(created_at__year=int(year))
            except (ValueError, AttributeError):
                pass
        return qs

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user, is_active=True)


class CashSessionViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['opened_at', 'closed_at']
    filterset_fields = ['cash_register', 'status', 'is_active']

    def get_queryset(self):
        qs = CashSession.objects.select_related(
            'cash_register', 'opened_by', 'closed_by'
        ).prefetch_related('transactions').all()
        site = self.request.query_params.get('site')
        if site:
            qs = qs.filter(cash_register__site_id=site)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return CashSessionListSerializer
        return CashSessionSerializer

    def perform_create(self, serializer):
        cash_register = serializer.validated_data['cash_register']
        cash_register.is_open = True
        cash_register.save()
        serializer.save(opened_by=self.request.user)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        session = self.get_object()
        closing_balance = request.data.get('closing_balance')
        notes = request.data.get('notes', '')
        
        if closing_balance is None:
            return Response(
                {'detail': 'Le solde de clôture est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from decimal import Decimal
        session.close(request.user, Decimal(str(closing_balance)), notes)
        return Response(CashSessionSerializer(session).data)


class CashSessionOpenView(APIView):
    def post(self, request):
        cash_register_id = request.data.get('cash_register_id')
        opening_balance = request.data.get('opening_balance', 0)
        
        try:
            cash_register = CashRegister.objects.get(id=cash_register_id)
        except CashRegister.DoesNotExist:
            return Response(
                {'detail': 'Caisse non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if cash_register.is_open:
            existing_session = CashSession.objects.filter(
                cash_register=cash_register,
                status='OPEN'
            ).first()
            if existing_session:
                return Response(
                    {'detail': 'Une session est déjà ouverte', 'session': CashSessionSerializer(existing_session).data},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        from decimal import Decimal
        session = CashSession.objects.create(
            cash_register=cash_register,
            opened_by=request.user,
            opening_balance=Decimal(str(opening_balance))
        )
        
        cash_register.is_open = True
        cash_register.save()
        
        return Response(CashSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class BankAccountViewSet(viewsets.ModelViewSet):
    queryset = BankAccount.objects.select_related('site').all()
    serializer_class = BankAccountSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'bank_name', 'account_number']
    filterset_fields = ['site', 'account_type', 'is_active']
    ordering_fields = ['name', 'created_at']


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['label', 'description']
    filterset_fields = ['site', 'category', 'status', 'payment_method', 'bank_account']
    ordering_fields = ['date', 'amount', 'created_at']

    def get_queryset(self):
        qs = Expense.objects.select_related(
            'site', 'payment_method', 'bank_account', 'approved_by'
        ).all()
        month = self.request.query_params.get('month')  # YYYY-MM
        year = self.request.query_params.get('year')    # YYYY
        if month:
            try:
                y, m = month.split('-')
                qs = qs.filter(date__year=int(y), date__month=int(m))
            except (ValueError, AttributeError):
                pass
        elif year:
            try:
                qs = qs.filter(date__year=int(year))
            except (ValueError, AttributeError):
                pass
        return qs

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        expense = self.get_object()
        if expense.status != 'PENDING':
            return Response(
                {'detail': 'Seules les dépenses en attente peuvent être approuvées'},
                status=status.HTTP_400_BAD_REQUEST
            )
        expense.status = 'APPROVED'
        expense.approved_by = request.user
        expense.save()
        # F1: auto journal entry for approved expense
        try:
            from apps.accounting.models import AccountingAccount, JournalEntry, JournalLine
            site = expense.site
            if site:
                expense_account = AccountingAccount.objects.filter(
                    site=site, account_type='EXPENSE', is_active=True
                ).first()
                asset_account = AccountingAccount.objects.filter(
                    site=site, account_type='ASSET', code__startswith='5', is_active=True
                ).first()
                if expense_account and asset_account:
                    entry = JournalEntry.objects.create(
                        site=site,
                        entry_date=expense.date,
                        description=f'Dépense: {expense.label}',
                        reference=str(expense.id),
                        status='DRAFT',
                        created_by=request.user,
                    )
                    JournalLine.objects.create(
                        journal_entry=entry, account=expense_account,
                        debit_amount=expense.amount, credit_amount=0,
                        description=expense.label,
                    )
                    JournalLine.objects.create(
                        journal_entry=entry, account=asset_account,
                        debit_amount=0, credit_amount=expense.amount,
                        description=expense.label,
                    )
                    # Auto-post since the entry is balanced and derived from an approved expense
                    entry.post(request.user)
        except Exception:
            pass
        return Response(ExpenseSerializer(expense).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        expense = self.get_object()
        if expense.status != 'PENDING':
            return Response(
                {'detail': 'Seules les dépenses en attente peuvent être rejetées'},
                status=status.HTTP_400_BAD_REQUEST
            )
        expense.status = 'CANCELLED'
        expense.save()
        return Response(ExpenseSerializer(expense).data)

    @action(detail=True, methods=['post'], url_path='mark-paid')
    def mark_paid(self, request, pk=None):
        expense = self.get_object()
        if expense.status != 'APPROVED':
            return Response(
                {'detail': 'Seules les dépenses approuvées peuvent être marquées payées'},
                status=status.HTTP_400_BAD_REQUEST
            )
        expense.status = 'PAID'
        expense.save()
        return Response(ExpenseSerializer(expense).data)


class CashReportView(APIView):
    def get(self, request):
        site_id = request.query_params.get('site_id')
        date_str = request.query_params.get('date')
        
        from datetime import datetime
        if date_str:
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            report_date = timezone.now().date()
        
        from datetime import datetime as dt, timedelta
        day_start = timezone.make_aware(dt.combine(report_date, dt.min.time()))
        day_end = day_start + timedelta(days=1)
        sessions = CashSession.objects.filter(
            opened_at__gte=day_start, opened_at__lt=day_end
        ).select_related('cash_register', 'opened_by', 'closed_by')
        
        if site_id:
            sessions = sessions.filter(cash_register__site_id=site_id)
        
        total_in = CashTransaction.objects.filter(
            session__in=sessions,
            transaction_type='IN',
            is_active=True
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_out = CashTransaction.objects.filter(
            session__in=sessions,
            transaction_type='OUT',
            is_active=True
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            'date': report_date,
            'sessions': CashSessionListSerializer(sessions, many=True).data,
            'total_cash_in': total_in,
            'total_cash_out': total_out,
            'net': total_in - total_out
        })


class FeeConfigurationViewSet(viewsets.ModelViewSet):
    queryset = FeeConfiguration.objects.all()
    serializer_class = FeeConfigurationSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['label']
    ordering_fields = ['created_at', 'label']

    def get_queryset(self):
        qs = FeeConfiguration.objects.select_related(
            'site', 'program', 'level', 'academic_year'
        )
        p = self.request.query_params
        if p.get('site'):
            qs = qs.filter(site_id=p['site'].replace('-', ''))
        if p.get('program'):
            qs = qs.filter(program_id=p['program'].replace('-', ''))
        if p.get('level'):
            qs = qs.filter(level_id=p['level'].replace('-', ''))
        if p.get('academic_year'):
            qs = qs.filter(academic_year_id=p['academic_year'].replace('-', ''))
        if p.get('is_active') is not None and p.get('is_active') != '':
            qs = qs.filter(is_active=p['is_active'].lower() in ('true', '1', 'yes'))
        return qs
