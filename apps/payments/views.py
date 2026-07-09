import logging

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import CinetPayConfig, CinetPayTransaction

logger = logging.getLogger(__name__)
from .serializers import (
    CinetPayConfigSerializer, CinetPayTransactionSerializer,
    CinetPayInitiateSerializer
)
from .services import CinetPayService
from apps.finance.models import Invoice


class CinetPayConfigViewSet(viewsets.ModelViewSet):
    queryset = CinetPayConfig.objects.select_related('site').all()
    serializer_class = CinetPayConfigSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['site', 'is_active', 'is_sandbox']


class CinetPayTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CinetPayTransaction.objects.select_related(
        'invoice__student__user', 'payment', 'initiated_by'
    ).all()
    serializer_class = CinetPayTransactionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['initiated_at', 'amount', 'status']
    filterset_fields = ['invoice', 'status', 'is_active']
    # A student needs to see/poll their own payment transactions even before
    # the registration fee is paid — this is the payment flow itself (see
    # apps.students.permissions). get_queryset below makes that safe.
    fee_gate_exempt = True

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.user_type == 'STUDENT':
            # A student may only ever see their own transactions.
            return qs.filter(invoice__student__user=self.request.user)
        return qs

    @action(detail=True, methods=['get'])
    def check_status(self, request, pk=None):
        transaction = self.get_object()
        service = CinetPayService(transaction.invoice.site)
        result = service.verify_payment(transaction.transaction_id)
        # Self-heal: if CinetPay confirms success but our webhook never
        # arrived, reconcile now instead of leaving the transaction stuck.
        service.reconcile_from_verification(transaction, result)
        return Response(result)


class CinetPayInitiateView(APIView):
    # Starting a Mobile Money payment is exactly how an unpaid student pays
    # their registration fee in the first place — must stay reachable.
    fee_gate_exempt = True

    def post(self, request):
        serializer = CinetPayInitiateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                'CinetPayInitiate 400 (validation): user=%s errors=%s payload=%s',
                request.user, serializer.errors, request.data,
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        invoice_id = data.get('invoice_id')
        student_id = data.get('student_id')

        if not invoice_id and not student_id:
            logger.warning(
                'CinetPayInitiate 400 (invoice_id/student_id manquants): user=%s payload=%s',
                request.user, request.data,
            )
            return Response(
                {'detail': 'invoice_id ou student_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if invoice_id:
            try:
                invoice = Invoice.objects.get(id=invoice_id)
            except Invoice.DoesNotExist:
                return Response(
                    {'detail': 'Facture non trouvée'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if invoice.status in ['PAID', 'CANCELLED']:
                logger.warning(
                    'CinetPayInitiate 400 (facture non payable): user=%s invoice=%s status=%s',
                    request.user, invoice.invoice_number, invoice.status,
                )
                return Response(
                    {'detail': 'Cette facture ne peut pas être payée'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            amount = data.get('amount', invoice.balance)
            if amount <= 0:
                logger.warning(
                    'CinetPayInitiate 400 (montant <= 0): user=%s invoice=%s amount=%s balance=%s',
                    request.user, invoice.invoice_number, amount, invoice.balance,
                )
                return Response(
                    {'detail': 'Le montant doit être supérieur à 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # No invoice yet — create one on the fly so a Mobile Money payment
            # always lands somewhere instead of being silently unattached.
            invoice, error = self._create_invoice_for_payment(request, student_id, data)
            if error:
                return error
            amount = invoice.balance

        transaction = CinetPayTransaction.objects.create(
            invoice=invoice,
            amount=amount,
            initiated_by=request.user
        )
        
        service = CinetPayService(invoice.site)
        result = service.initiate_payment(transaction)
        
        if result['success']:
            return Response({
                'transaction_id': transaction.transaction_id,
                'payment_url': result['payment_url'],
                'amount': str(transaction.amount),
                'currency': transaction.currency
            }, status=status.HTTP_201_CREATED)
        else:
            logger.warning(
                'CinetPayInitiate 400 (echec appel CinetPay): user=%s invoice=%s amount=%s '
                'transaction=%s error=%s',
                request.user, invoice.invoice_number, amount,
                transaction.transaction_id, result['error'],
            )
            # Include transaction_id so the mobile can use demo-pay even when DNS fails
            return Response(
                {'detail': result['error'], 'transaction_id': transaction.transaction_id},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _create_invoice_for_payment(self, request, student_id, data):
        """Create an Invoice + InvoiceItem for a Mobile Money payment that
        wasn't initiated against an existing invoice. Returns (invoice, None)
        on success, or (None, Response) on failure."""
        from datetime import timedelta
        from apps.students.models import Student
        from apps.finance.models import FeeType, InvoiceItem
        from apps.core.models import AcademicYear
        from django.utils import timezone as tz

        amount = data.get('amount')
        if not amount or amount <= 0:
            logger.warning(
                'CinetPayInitiate 400 (montant manquant, creation facture a la volee): '
                'user=%s student_id=%s payload=%s',
                request.user, student_id, request.data,
            )
            return None, Response(
                {'detail': 'Le montant est requis et doit être supérieur à 0'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return None, Response({'detail': 'Étudiant non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        if not student.site_id:
            return None, Response({'detail': "Site de l'étudiant introuvable"}, status=status.HTTP_400_BAD_REQUEST)

        academic_year = AcademicYear.get_current()
        if not academic_year:
            return None, Response(
                {'detail': 'Aucune année académique en cours'},
                status=status.HTTP_400_BAD_REQUEST
            )

        fee_type_code = (data.get('fee_type_code') or 'TUITION').upper()
        fee_type, _ = FeeType.objects.get_or_create(
            code=fee_type_code,
            defaults={
                'name': 'Frais de scolarité' if fee_type_code == 'TUITION' else fee_type_code.title(),
                'default_amount': amount,
            }
        )

        description = data.get('description') or 'Paiement Mobile Money'
        invoice = Invoice.objects.create(
            student=student,
            site=student.site,
            academic_year=academic_year,
            due_date=tz.now().date() + timedelta(days=30),
            notes=description,
            created_by=request.user if request.user.is_authenticated else None,
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            fee_type=fee_type,
            description=description,
            quantity=1,
            unit_price=amount,
        )
        invoice.refresh_from_db()  # pick up the item just created
        invoice.save()  # recompute subtotal/total/balance now that the item exists

        # calculate_totals() ran once already at Invoice.objects.create() time,
        # when there were no items yet — a 0/0 balance made it set status
        # 'PAID'. That doesn't get corrected by the recompute above unless one
        # of its other branches fires, which they won't for a fresh unpaid
        # invoice (amount_paid=0, not overdue) — so fix it explicitly.
        if invoice.status == 'PAID' and invoice.balance > 0:
            invoice.status = 'PENDING'
            invoice.save(update_fields=['status'])

        return invoice, None


class CinetPayCallbackView(APIView):
    """Handles CinetPay's notify_url webhook (IPN).

    Per CinetPay's own docs, a webhook can be called by anyone — the status
    in its payload is only ever used here to identify which transaction to
    check; process_callback() always re-verifies the canonical status via
    GET /v1/payment/{merchant_transaction_id} before finalizing anything.
    We don't know the exact payload shape/field names CinetPay's v1 webhook
    sends, so we look for either identifier in the body or the query
    string rather than validating a fixed schema.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = {**request.query_params.dict(), **request.data}
        transaction_id = data.get('merchant_transaction_id') or data.get('transaction_id')
        if not transaction_id:
            return Response(
                {'detail': 'Identifiant de transaction manquant'},
                status=status.HTTP_400_BAD_REQUEST
            )

        transaction = (
            CinetPayTransaction.objects.filter(transaction_id=transaction_id).first()
            or CinetPayTransaction.objects.filter(cinetpay_transaction_id=transaction_id).first()
        )
        if not transaction:
            return Response(
                {'detail': 'Transaction non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )

        service = CinetPayService(transaction.invoice.site)
        result = service.process_callback(transaction)

        if result['success']:
            return Response({'status': 'success'})
        else:
            return Response(
                {'detail': result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )


class CinetPayStatusView(APIView):
    # Polling payment status is part of the payment flow itself.
    fee_gate_exempt = True

    def get(self, request, transaction_id):
        try:
            transaction = CinetPayTransaction.objects.get(transaction_id=transaction_id)
        except CinetPayTransaction.DoesNotExist:
            return Response(
                {'detail': 'Transaction non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Sandbox local : transaction déjà marquée SUCCESS par sandbox-success
        if transaction.status == 'SUCCESS':
            return Response({
                'transaction': CinetPayTransactionSerializer(transaction).data,
            })

        service = CinetPayService(transaction.invoice.site)
        verification = service.verify_payment(transaction_id)
        # Self-heal: if CinetPay confirms success but our webhook never
        # arrived, reconcile now instead of leaving the transaction stuck.
        service.reconcile_from_verification(transaction, verification)
        transaction.refresh_from_db()

        return Response({
            'transaction': CinetPayTransactionSerializer(transaction).data,
            'verification': verification
        })


class CinetPaySandboxSuccessView(APIView):
    """
    Vue de test sandbox : simule un paiement réussi sans passer par CinetPay.
    Activée uniquement quand CINETPAY_LOCAL_SANDBOX=True.
    Ouverte dans le navigateur in-app → valide la transaction → retourne une page HTML.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.conf import settings
        from django.http import HttpResponse

        if not getattr(settings, 'CINETPAY_LOCAL_SANDBOX', False):
            return HttpResponse('Sandbox désactivé.', status=403)

        transaction_id = request.GET.get('transaction_id', '')
        try:
            transaction = CinetPayTransaction.objects.select_related(
                'invoice__student__user'
            ).get(transaction_id=transaction_id)
        except CinetPayTransaction.DoesNotExist:
            return HttpResponse('Transaction introuvable.', status=404)

        if transaction.status != 'SUCCESS':
            CinetPayService.finalize_success_payment(
                transaction,
                payment_method_code='CINETPAY',
                payment_method_name='CinetPay Mobile Money',
                reference=transaction.transaction_id,
                notes='Paiement sandbox (test)',
            )

        student = transaction.invoice.student.user
        html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paiement test réussi</title>
<style>
  body{{font-family:sans-serif;display:flex;align-items:center;justify-content:center;
        min-height:100vh;margin:0;background:#F0FDF4;}}
  .card{{background:#fff;border-radius:16px;padding:40px;text-align:center;
         box-shadow:0 4px 24px rgba(0,0,0,.08);max-width:360px;width:90%;}}
  .icon{{font-size:56px;margin-bottom:16px;}}
  h1{{color:#065F46;margin:0 0 8px;font-size:22px;}}
  p{{color:#6B7280;margin:0 0 6px;font-size:14px;}}
  .amount{{color:#059669;font-size:28px;font-weight:800;margin:16px 0;}}
  .badge{{display:inline-block;background:#D1FAE5;color:#065F46;
           border-radius:20px;padding:4px 14px;font-size:12px;font-weight:700;}}
  .back-btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;
             margin-top:24px;width:100%;padding:14px 20px;border:none;border-radius:12px;
             background:#059669;color:#fff;font-size:15px;font-weight:700;cursor:pointer;}}
  .back-btn:active{{background:#047857;}}
  .hint{{margin-top:12px;font-size:12px;color:#9CA3AF;}}
</style>
</head>
<body>
<div class="card">
  <div class="icon">✅</div>
  <h1>Paiement test réussi</h1>
  <p>{student.first_name} {student.last_name}</p>
  <div class="amount">{int(transaction.amount):,} F CFA</div>
  <div class="badge">SANDBOX — Test uniquement</div>
  <button class="back-btn" onclick="window.close(); window.history.back();">
    ← Retour à l'application
  </button>
  <p class="hint">Si rien ne se passe, fermez simplement cette fenêtre.</p>
</div>
</body>
</html>"""
        return HttpResponse(html)


class CinetPayDemoPayView(APIView):
    """
    Endpoint de paiement démo (authentifié).
    Utilisé quand CinetPay est inaccessible : crée un vrai Payment en base
    à partir d'une transaction déjà initiée (status=FAILED).
    Sécurisé : vérifie que la transaction appartient à l'utilisateur connecté.
    """
    # NOTE: this explicit permission_classes already replaces
    # DEFAULT_PERMISSION_CLASSES entirely (DRF doesn't merge the two), so
    # IsRegistrationFeePaidOrExempt never runs here regardless — fee_gate_exempt
    # is set anyway for documentation, in case that override is ever removed.
    fee_gate_exempt = True
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        transaction_id = request.data.get('transaction_id', '').strip()
        if not transaction_id:
            return Response({'detail': 'transaction_id requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transaction = CinetPayTransaction.objects.select_related(
                'invoice__student__user'
            ).get(transaction_id=transaction_id)
        except CinetPayTransaction.DoesNotExist:
            return Response({'detail': 'Transaction introuvable'}, status=status.HTTP_404_NOT_FOUND)

        # Sécurité : l'étudiant propriétaire, un parent qui lui est rattaché,
        # ou un admin/staff peuvent valider — un parent payant depuis l'app
        # mobile n'est pas l'utilisateur de l'étudiant, donc s'arrêter au seul
        # user_id du student bloquait à tort tous les paiements faits par un
        # parent (y compris le repli "Mode test" quand CinetPay est injoignable).
        user = request.user
        student = transaction.invoice.student
        is_owner  = student.user_id == user.id
        is_staff  = user.user_type in ('ADMIN', 'STAFF')
        is_parent = False
        if not (is_owner or is_staff) and user.user_type == 'PARENT':
            from apps.students.models import StudentParent
            is_parent = StudentParent.objects.filter(student=student, parent__user=user).exists()
        if not (is_owner or is_staff or is_parent):
            return Response({'detail': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)

        if transaction.status == 'SUCCESS':
            return Response({
                'success': True,
                'already_paid': True,
                'amount': str(transaction.amount),
                'invoice_number': transaction.invoice.invoice_number,
            })

        CinetPayService.finalize_success_payment(
            transaction,
            payment_method_code='CINETPAY_DEMO',
            payment_method_name='CinetPay (Test)',
            reference=f"DEMO-{transaction.transaction_id}",
            notes='Paiement test (CinetPay temporairement inaccessible)',
        )

        return Response({
            'success': True,
            'already_paid': False,
            'amount': str(transaction.amount),
            'invoice_number': transaction.invoice.invoice_number,
        })
