from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import CinetPayConfig, CinetPayTransaction
from .serializers import (
    CinetPayConfigSerializer, CinetPayTransactionSerializer,
    CinetPayInitiateSerializer, CinetPayCallbackSerializer
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

    @action(detail=True, methods=['get'])
    def check_status(self, request, pk=None):
        transaction = self.get_object()
        service = CinetPayService(transaction.invoice.site)
        result = service.verify_payment(transaction.transaction_id)
        return Response(result)


class CinetPayInitiateView(APIView):
    def post(self, request):
        serializer = CinetPayInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        try:
            invoice = Invoice.objects.get(id=data['invoice_id'])
        except Invoice.DoesNotExist:
            return Response(
                {'detail': 'Facture non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if invoice.status in ['PAID', 'CANCELLED']:
            return Response(
                {'detail': 'Cette facture ne peut pas être payée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        amount = data.get('amount', invoice.balance)
        if amount <= 0:
            return Response(
                {'detail': 'Le montant doit être supérieur à 0'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
            return Response(
                {'detail': result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )


class CinetPayCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = CinetPayCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        transaction_id = data.get('cpm_trans_id')
        try:
            transaction = CinetPayTransaction.objects.get(transaction_id=transaction_id)
        except CinetPayTransaction.DoesNotExist:
            return Response(
                {'detail': 'Transaction non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        service = CinetPayService(transaction.invoice.site)
        
        signature = data.get('signature', '')
        if signature and not service.verify_signature(data, signature):
            return Response(
                {'detail': 'Signature invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = service.process_callback(data)
        
        if result['success']:
            return Response({'status': 'success'})
        else:
            return Response(
                {'detail': result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )


class CinetPayStatusView(APIView):
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
        from apps.finance.models import Payment, PaymentMethod
        from django.utils import timezone

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
            # Créer le Payment et valider la facture
            cinetpay_method, _ = PaymentMethod.objects.get_or_create(
                code='CINETPAY',
                defaults={'name': 'CinetPay Mobile Money', 'is_online': True}
            )
            payment = Payment.objects.create(
                invoice=transaction.invoice,
                payment_method=cinetpay_method,
                amount=transaction.amount,
                status='SUCCESS',
                reference=transaction.transaction_id,
                notes='Paiement sandbox (test)',
                validated_at=timezone.now()
            )
            transaction.status = 'SUCCESS'
            transaction.payment = payment
            transaction.completed_at = timezone.now()
            transaction.save()
            transaction.invoice.add_payment(transaction.amount)

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
</style>
</head>
<body>
<div class="card">
  <div class="icon">✅</div>
  <h1>Paiement test réussi</h1>
  <p>{student.first_name} {student.last_name}</p>
  <div class="amount">{int(transaction.amount):,} F CFA</div>
  <div class="badge">SANDBOX — Test uniquement</div>
  <p style="margin-top:20px;font-size:12px;color:#9CA3AF;">
    Fermez cette fenêtre pour retourner à l'application.
  </p>
</div>
</body>
</html>"""
        return HttpResponse(html)
