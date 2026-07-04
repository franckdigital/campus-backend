import requests
import hashlib
import hmac
from django.conf import settings
from django.utils import timezone
from .models import CinetPayConfig, CinetPayTransaction
from apps.finance.models import Payment, PaymentMethod


class CinetPayService:
    """Service for CinetPay API integration."""
    
    BASE_URL = getattr(settings, 'CINETPAY_BASE_URL', 'https://api-checkout.cinetpay.net/v2')
    
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

        # ── Sandbox local (test sans connexion CinetPay) ──────────────────
        if getattr(settings, 'CINETPAY_LOCAL_SANDBOX', False):
            frontend = getattr(settings, 'FRONTEND_URL', 'https://api-campus.numerix.digital')
            mock_url = (
                f"{frontend}/api/v1/payments/cinetpay/sandbox-success/"
                f"?transaction_id={transaction.transaction_id}"
            )
            transaction.payment_url = mock_url
            transaction.cinetpay_transaction_id = f"SANDBOX-{transaction.transaction_id}"
            transaction.save()
            return {
                'success': True,
                'payment_url': mock_url,
                'transaction_id': transaction.transaction_id,
            }
        # ─────────────────────────────────────────────────────────────────

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

    @staticmethod
    def finalize_success_payment(transaction, payment_method_code, payment_method_name, reference, notes):
        """Create the Payment and mark the transaction SUCCESS.

        Shared by the webhook callback, the sandbox test flow, the demo
        fallback, and status-check reconciliation, so they can't drift out of
        sync with each other. Does NOT call invoice.add_payment(): the
        Payment post_save signal (apps.finance.signals.on_payment_save)
        already recomputes invoice.amount_paid from the sum of all SUCCESS
        payments on the invoice — calling add_payment() here on top of that
        double-counts every single Mobile Money payment.
        """
        method, _ = PaymentMethod.objects.get_or_create(
            code=payment_method_code,
            defaults={'name': payment_method_name, 'is_online': True}
        )
        payment = Payment.objects.create(
            invoice=transaction.invoice,
            payment_method=method,
            amount=transaction.amount,
            status='SUCCESS',
            reference=reference,
            notes=notes,
            validated_at=timezone.now(),
        )
        transaction.status = 'SUCCESS'
        transaction.payment = payment
        transaction.completed_at = timezone.now()
        transaction.save()
        return payment

    def reconcile_from_verification(self, transaction, verification):
        """If CinetPay's own /payment/check confirms success but our local
        transaction is still pending — e.g. the IPN webhook never reached us,
        got dropped, or was retried past our window — finalize it here. Same
        end effect as process_callback(), just triggered by polling
        (CinetPayStatusView / check_status) instead of the webhook, so a
        payment CinetPay actually captured doesn't sit invisible forever.

        NOTE: this checks CinetPay's *v2 check API* response shape
        ({"code": "00", "data": {"status": "ACCEPTED", "amount": ...}}), which
        uses different field names than the webhook's cpm_* payload. Verify
        this against a real CinetPay test transaction before fully trusting
        it in production — adjust the field names below if they don't match.
        """
        if transaction.status == 'SUCCESS' or not isinstance(verification, dict):
            return transaction

        payload = verification.get('data') or {}
        is_success = (
            verification.get('code') == '00'
            and str(payload.get('status', '')).upper() == 'ACCEPTED'
        )
        if not is_success:
            return transaction

        try:
            verified_amount = int(float(payload.get('amount', transaction.amount)))
        except (TypeError, ValueError):
            verified_amount = None

        if verified_amount is not None and verified_amount != int(transaction.amount):
            # Amount mismatch — don't auto-trust it, leave for manual review.
            return transaction

        self.finalize_success_payment(
            transaction,
            payment_method_code='CINETPAY',
            payment_method_name='CinetPay Mobile Money',
            reference=transaction.transaction_id,
            notes='Paiement CinetPay — confirmé par vérification (callback jamais reçu)',
        )
        return transaction

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
            transaction.payment_method = data.get('payment_method', '')
            transaction.operator_id = data.get('operator_id', '')
            transaction.save(update_fields=['callback_data', 'payment_method', 'operator_id'])

            self.finalize_success_payment(
                transaction,
                payment_method_code='CINETPAY',
                payment_method_name='CinetPay Mobile Money',
                reference=transaction.transaction_id,
                notes=f"Paiement CinetPay - {data.get('payment_method', 'Mobile Money')}",
            )
            return {'success': True, 'transaction': transaction}
        else:
            transaction.status = 'FAILED'
            transaction.status_message = data.get('cpm_error_message', 'Payment failed')
            transaction.save()
            return {'success': False, 'error': transaction.status_message}
