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
        
        service = CinetPayService(transaction.invoice.site)
        verification = service.verify_payment(transaction_id)
        
        return Response({
            'transaction': CinetPayTransactionSerializer(transaction).data,
            'verification': verification
        })
