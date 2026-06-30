import requests
import hashlib
import hmac
from django.conf import settings
from django.utils import timezone
from .models import CinetPayConfig, CinetPayTransaction
from apps.finance.models import Payment, PaymentMethod


class CinetPayService:
    """Service for CinetPay API integration."""
    
    BASE_URL = 'https://api-checkout.cinetpay.net/v2'
    
    def __init__(self, site=None):
        if site:
            try:
                config = CinetPayConfig.objects.get(site=site, is_active=True)
                self.api_key = config.api_key
                self.site_id = config.cinetpay_site_id
                self.secret_key = config.secret_key
                self.notify_url = config.notify_url
                self.return_url = config.return_url
                self.cancel_url = config.cancel_url
            except CinetPayConfig.DoesNotExist:
                self._use_default_config()
        else:
            self._use_default_config()
    
    def _use_default_config(self):
        self.api_key = settings.CINETPAY_API_KEY
        self.site_id = settings.CINETPAY_SITE_ID
        self.secret_key = settings.CINETPAY_SECRET_KEY
        self.notify_url = settings.CINETPAY_NOTIFY_URL
        self.return_url = getattr(settings, 'CINETPAY_RETURN_URL', '')
        self.cancel_url = getattr(settings, 'CINETPAY_CANCEL_URL', '')
    
    def initiate_payment(self, transaction):
        """Initiate a payment with CinetPay."""
        url = f"{self.BASE_URL}/payment"
        
        payload = {
            'apikey': self.api_key,
            'site_id': self.site_id,
            'transaction_id': transaction.transaction_id,
            'amount': int(transaction.amount),
            'currency': transaction.currency,
            'description': f"Paiement facture {transaction.invoice.invoice_number}",
            'notify_url': self.notify_url,
            'return_url': self.return_url or f"{settings.FRONTEND_URL}/payment/success",
            'cancel_url': self.cancel_url or f"{settings.FRONTEND_URL}/payment/cancel",
            'channels': 'ALL',
            'metadata': str(transaction.invoice.id),
            'customer_name': transaction.invoice.student.user.full_name,
            'customer_email': transaction.invoice.student.user.email,
            'customer_phone_number': transaction.invoice.student.user.phone or '',
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            data = response.json()
            
            if data.get('code') == '201':
                transaction.payment_url = data['data']['payment_url']
                transaction.cinetpay_transaction_id = data['data'].get('payment_token', '')
                transaction.save()
                return {
                    'success': True,
                    'payment_url': transaction.payment_url,
                    'transaction_id': transaction.transaction_id
                }
            else:
                transaction.status = 'FAILED'
                transaction.status_message = data.get('message', 'Erreur inconnue')
                transaction.save()
                return {
                    'success': False,
                    'error': data.get('message', 'Erreur lors de l\'initialisation')
                }
        except requests.RequestException as e:
            transaction.status = 'FAILED'
            transaction.status_message = str(e)
            transaction.save()
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_payment(self, transaction_id):
        """Verify a payment status with CinetPay."""
        url = f"{self.BASE_URL}/payment/check"
        
        payload = {
            'apikey': self.api_key,
            'site_id': self.site_id,
            'transaction_id': transaction_id,
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            data = response.json()
            return data
        except requests.RequestException as e:
            return {'error': str(e)}
    
    def verify_signature(self, data, signature):
        """Verify CinetPay callback signature."""
        to_sign = f"{self.site_id}{data.get('cpm_trans_id', '')}{data.get('cpm_trans_date', '')}{data.get('cpm_amount', '')}{self.secret_key}"
        computed_signature = hashlib.sha256(to_sign.encode()).hexdigest()
        return hmac.compare_digest(computed_signature, signature)
    
    def process_callback(self, data):
        """Process CinetPay callback."""
        transaction_id = data.get('cpm_trans_id')
        
        try:
            transaction = CinetPayTransaction.objects.get(transaction_id=transaction_id)
        except CinetPayTransaction.DoesNotExist:
            return {'success': False, 'error': 'Transaction not found'}
        
        transaction.callback_data = data
        
        cpm_result = data.get('cpm_result', '')
        cpm_amount = data.get('cpm_amount', 0)
        
        if cpm_result == '00' and int(cpm_amount) == int(transaction.amount):
            transaction.status = 'SUCCESS'
            transaction.completed_at = timezone.now()
            transaction.payment_method = data.get('payment_method', '')
            transaction.operator_id = data.get('operator_id', '')
            
            cinetpay_method = PaymentMethod.objects.filter(code='CINETPAY').first()
            if not cinetpay_method:
                cinetpay_method = PaymentMethod.objects.create(
                    name='CinetPay Mobile Money',
                    code='CINETPAY',
                    is_online=True,
                    requires_verification=True
                )
            
            payment = Payment.objects.create(
                invoice=transaction.invoice,
                payment_method=cinetpay_method,
                amount=transaction.amount,
                status='SUCCESS',
                reference=transaction.transaction_id,
                notes=f"Paiement CinetPay - {data.get('payment_method', 'Mobile Money')}",
                validated_at=timezone.now()
            )
            
            transaction.payment = payment
            transaction.save()
            
            transaction.invoice.add_payment(transaction.amount)
            
            return {'success': True, 'transaction': transaction}
        else:
            transaction.status = 'FAILED'
            transaction.status_message = data.get('cpm_error_message', 'Payment failed')
            transaction.save()
            return {'success': False, 'error': transaction.status_message}
