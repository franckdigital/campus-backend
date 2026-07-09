import re

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from .models import CinetPayConfig, CinetPayTransaction
from apps.finance.models import Payment, PaymentMethod


def _normalize_ci_phone(phone):
    """Strip formatting (spaces, +, country code) down to CinetPay's expected
    local format: a bare 10-digit number starting with 0 (Côte d'Ivoire moved
    to 10-digit mobile numbers in 2021 — 8-digit legacy-format numbers, or
    numbers with spaces/the +225 prefix left in, get rejected by CinetPay
    with "client phone number is not mobile" even though they display fine
    everywhere else in the app)."""
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('225') and len(digits) > 10:
        digits = digits[3:]
    if digits and not digits.startswith('0'):
        digits = '0' + digits
    return digits


class CinetPayService:
    """Service for the CinetPay v1 ("Aurora") API.

    Auth: POST /v1/oauth/login with {account_key, account_password} returns
    a bearer access_token (24h TTL) — cached per-config so we don't log in
    on every single payment call. Everything else is called with
    `Authorization: Bearer <token>`.

    NOTE: the exact response shape of a *successful* GET /v1/payment/{id}
    status check hasn't been confirmed against a real sandbox SUCCESS test
    number yet (only an INSUFFICIENT_BALANCE example was documented) — test
    against CinetPay's documented sandbox test numbers before fully trusting
    amount-level reconciliation.
    """

    BASE_URL = getattr(settings, 'CINETPAY_BASE_URL', 'https://api.cinetpay.net')

    def __init__(self, site=None):
        self._cache_suffix = 'default'
        if site:
            try:
                config = CinetPayConfig.objects.get(site=site, is_active=True)
                self.account_key = config.account_key
                self.account_password = config.account_password
                self.notify_url = config.notify_url
                self.success_url = config.success_url
                self.failed_url = config.failed_url
                self._cache_suffix = str(site.id)
            except CinetPayConfig.DoesNotExist:
                self._use_default_config()
        else:
            self._use_default_config()

    def _use_default_config(self):
        self.account_key = settings.CINETPAY_ACCOUNT_KEY
        self.account_password = settings.CINETPAY_ACCOUNT_PASSWORD
        self.notify_url = settings.CINETPAY_NOTIFY_URL
        self.success_url = getattr(settings, 'CINETPAY_SUCCESS_URL', '')
        self.failed_url = getattr(settings, 'CINETPAY_FAILED_URL', '')

    def _get_access_token(self):
        """Cached bearer token — POST /v1/oauth/login. Raises RuntimeError
        with CinetPay's own description on failure (e.g. INVALID_CREDENTIALS)."""
        cache_key = f'cinetpay_access_token_{self._cache_suffix}'
        token = cache.get(cache_key)
        if token:
            return token

        response = requests.post(
            f'{self.BASE_URL}/v1/oauth/login',
            json={'api_key': self.account_key, 'api_password': self.account_password},
            timeout=30,
        )
        data = response.json()
        if data.get('code') != 200 or not data.get('access_token'):
            raise RuntimeError(data.get('description') or data.get('status') or 'Authentification CinetPay échouée')

        token = data['access_token']
        # Refresh a bit before the documented 24h expiry rather than exactly at it.
        ttl = max(int(data.get('expires_in', 86400)) - 300, 60)
        cache.set(cache_key, token, ttl)
        return token

    def initiate_payment(self, transaction):
        """Initiate a payment with CinetPay."""

        # ── Sandbox local (test sans connexion CinetPay) ──────────────────
        if getattr(settings, 'CINETPAY_LOCAL_SANDBOX', False):
            # This mock page is served by THIS Django backend, not the
            # frontend SPA — settings.FRONTEND_URL points at the wrong host
            # (e.g. campus.numerix.digital instead of
            # api-campus.numerix.digital), which opens a blank page since
            # that server doesn't have this route at all. notify_url is
            # already guaranteed to point at this backend (CinetPay's real
            # webhook must reach it), so derive the origin from it instead.
            from urllib.parse import urlparse
            parsed = urlparse(self.notify_url) if self.notify_url else None
            backend_root = (
                f"{parsed.scheme}://{parsed.netloc}"
                if parsed and parsed.netloc
                else getattr(settings, 'FRONTEND_URL', 'https://api-campus.numerix.digital')
            )
            mock_url = (
                f"{backend_root}/api/v1/payments/cinetpay/sandbox-success/"
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

        try:
            token = self._get_access_token()
        except (RuntimeError, requests.RequestException) as e:
            transaction.status = 'FAILED'
            transaction.status_message = str(e)
            transaction.save()
            return {'success': False, 'error': str(e)}

        student_user = transaction.invoice.student.user
        payload = {
            'currency': transaction.currency,
            'merchant_transaction_id': transaction.transaction_id,
            'amount': int(transaction.amount),
            'lang': 'fr',
            'designation': f"Paiement facture {transaction.invoice.invoice_number}",
            'client_email': student_user.email,
            'client_phone_number': _normalize_ci_phone(student_user.phone),
            # CinetPay requires 2-255 chars for both — fall back to
            # placeholders rather than sending an empty/1-char name that
            # would get rejected outright.
            'client_first_name': (student_user.first_name or 'Client')[:255] or 'Client',
            'client_last_name': (student_user.last_name or 'CinetPay')[:255] or 'CinetPay',
            'direct_pay': False,
            'success_url': self.success_url or f"{settings.FRONTEND_URL}/payment/success",
            'failed_url': self.failed_url or f"{settings.FRONTEND_URL}/payment/cancel",
            'notify_url': self.notify_url,
        }

        try:
            response = requests.post(
                f'{self.BASE_URL}/v1/payment',
                json=payload,
                headers={'Authorization': f'Bearer {token}'},
                timeout=30,
            )
            data = response.json()

            if data.get('code') == 200 and data.get('payment_url'):
                transaction.payment_url = data['payment_url']
                transaction.cinetpay_transaction_id = data.get('transaction_id', '')
                transaction.notify_token = data.get('notify_token', '')
                transaction.save()
                return {
                    'success': True,
                    'payment_url': transaction.payment_url,
                    'transaction_id': transaction.transaction_id,
                }
            else:
                # v1 "Aurora" wraps the REAL outcome in details — the
                # top-level code/status only mean "the request was well
                # formed", not "the payment succeeded". details.errors (a
                # dict of field -> reason, e.g. client_phone_number) is the
                # actual cause and was silently dropped before this fix.
                details = data.get('details') or {}
                errors = details.get('errors')
                if errors:
                    message = '; '.join(f'{k}: {v}' for k, v in errors.items())
                else:
                    message = (
                        details.get('message') or data.get('description')
                        or data.get('message') or data.get('status')
                        or 'Erreur lors de l\'initialisation'
                    )
                transaction.status = 'FAILED'
                transaction.status_message = message
                transaction.save()
                return {'success': False, 'error': message}
        except requests.RequestException as e:
            transaction.status = 'FAILED'
            transaction.status_message = str(e)
            transaction.save()
            return {'success': False, 'error': str(e)}

    def verify_payment(self, transaction_id):
        """Check the canonical payment status — GET /v1/payment/{merchant_transaction_id}.
        `transaction_id` here is OUR merchant_transaction_id
        (CinetPayTransaction.transaction_id), the identifier we originally
        sent CinetPay, not CinetPay's own transaction_id."""
        try:
            token = self._get_access_token()
        except (RuntimeError, requests.RequestException) as e:
            return {'error': str(e)}

        try:
            response = requests.get(
                f'{self.BASE_URL}/v1/payment/{transaction_id}',
                headers={'Authorization': f'Bearer {token}'},
                timeout=30,
            )
            return response.json()
        except requests.RequestException as e:
            return {'error': str(e)}

    @staticmethod
    def finalize_success_payment(transaction, payment_method_code, payment_method_name, reference, notes):
        """Create the Payment and mark the transaction SUCCESS.

        Shared by the sandbox test flow, the demo fallback, and status-check
        reconciliation, so they can't drift out of sync with each other.
        Does NOT call invoice.add_payment(): the Payment post_save signal
        (apps.finance.signals.on_payment_save) already recomputes
        invoice.amount_paid from the sum of all SUCCESS payments on the
        invoice — calling add_payment() here on top of that double-counts
        every single Mobile Money payment.
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
        """If CinetPay's own status check confirms success but our local
        transaction is still pending — e.g. the notify_url webhook never
        reached us, got dropped, or was retried past our window — finalize
        it here. Same end effect as process_callback(), just triggered by
        polling (CinetPayStatusView / check_status) instead of the webhook.

        Only trusts `status == 'SUCCESS'` (one of the documented values:
        SUCCESS/FAILED/INITIATED/PENDING/INSUFFICIENT_BALANCE) — no
        amount-match guard here yet, since the exact field name for the
        paid amount on a SUCCESS response isn't confirmed from the docs.
        """
        if transaction.status == 'SUCCESS' or not isinstance(verification, dict):
            return transaction

        if verification.get('status') != 'SUCCESS':
            return transaction

        self.finalize_success_payment(
            transaction,
            payment_method_code='CINETPAY',
            payment_method_name='CinetPay Mobile Money',
            reference=transaction.transaction_id,
            notes='Paiement CinetPay — confirmé par vérification (callback jamais reçu)',
        )
        return transaction

    def process_callback(self, transaction):
        """Process CinetPay's notify_url webhook (IPN) for an already
        identified transaction.

        CinetPay's own documentation explicitly warns: a webhook can be
        called by anyone, so the status inside its payload must NEVER be
        trusted at face value. We only use the webhook to learn that
        *something* happened for this transaction, then always re-fetch the
        canonical status via GET /v1/payment/{merchant_transaction_id}
        before finalizing anything.
        """
        verification = self.verify_payment(transaction.transaction_id)
        self.reconcile_from_verification(transaction, verification)
        transaction.refresh_from_db()

        if transaction.status == 'SUCCESS':
            return {'success': True, 'transaction': transaction}

        if isinstance(verification, dict) and verification.get('status') == 'FAILED' and transaction.status != 'FAILED':
            transaction.status = 'FAILED'
            transaction.status_message = (
                verification.get('message') or verification.get('description') or 'Paiement échoué'
            )
            transaction.save(update_fields=['status', 'status_message', 'updated_at'])

        return {
            'success': False,
            'transaction': transaction,
            'error': transaction.status_message or 'Paiement non confirmé',
        }
