"""
Read-only diagnostic for a CinetPay Mobile Money payment that failed with
"Params you provides are invalid" (a literal CinetPay v1 error string, coming
straight from `data.get('description')` in CinetPayService.initiate_payment).

Prints the exact payload that was/would be sent to CinetPay for the invoice's
most recent transaction, plus the resolved CinetPayConfig (site-specific or
global fallback), so a mismatch (missing phone, blank notify_url, wrong
currency, etc.) is visible without guessing.

Usage:
    python manage.py diagnose_cinetpay_failure --invoice-number INV-ESCAM-CO-2026-00002
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Diagnose a failed CinetPay Mobile Money initiation for a given invoice."

    def add_arguments(self, parser):
        parser.add_argument('--invoice-number', required=True)

    def handle(self, *args, **options):
        from apps.finance.models import Invoice
        from apps.payments.models import CinetPayConfig
        from apps.payments.services import CinetPayService

        invoice = Invoice.objects.filter(invoice_number=options['invoice_number']).select_related(
            'student__user', 'site'
        ).first()
        if not invoice:
            raise CommandError(f"Aucune facture avec invoice_number={options['invoice_number']!r}.")

        self.stdout.write(self.style.MIGRATE_HEADING(f"\n=== Facture {invoice.invoice_number} ===\n"))
        self.stdout.write(f'  student={invoice.student} site={invoice.site}')
        self.stdout.write(f'  total={invoice.total} amount_paid={invoice.amount_paid} balance={invoice.balance} status={invoice.status}')

        student_user = invoice.student.user
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Champs client utilisés dans le payload CinetPay ===\n'))
        self.stdout.write(f'  email={student_user.email!r}')
        self.stdout.write(f'  phone={student_user.phone!r}')
        self.stdout.write(f'  first_name={student_user.first_name!r}')
        self.stdout.write(f'  last_name={student_user.last_name!r}')

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== CinetPayConfig résolue pour ce site ===\n'))
        config = CinetPayConfig.objects.filter(site=invoice.site, is_active=True).first()
        if config:
            self.stdout.write(f'  source=site-specific (site={invoice.site})')
            self.stdout.write(f'  account_key={config.account_key[:6]}... (len={len(config.account_key)})')
            self.stdout.write(f'  is_sandbox={config.is_sandbox}')
            self.stdout.write(f'  notify_url={config.notify_url!r}')
            self.stdout.write(f'  success_url={config.success_url!r}')
            self.stdout.write(f'  failed_url={config.failed_url!r}')
        else:
            from django.conf import settings
            self.stdout.write('  source=fallback (settings.CINETPAY_*, aucune CinetPayConfig active pour ce site)')
            self.stdout.write(f'  account_key={(settings.CINETPAY_ACCOUNT_KEY or "")[:6]}... (len={len(settings.CINETPAY_ACCOUNT_KEY or "")})')
            self.stdout.write(f'  notify_url={settings.CINETPAY_NOTIFY_URL!r}')
            self.stdout.write(f'  success_url={getattr(settings, "CINETPAY_SUCCESS_URL", "")!r}')
            self.stdout.write(f'  failed_url={getattr(settings, "CINETPAY_FAILED_URL", "")!r}')

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Dernières transactions CinetPay pour cette facture ===\n'))
        transactions = invoice.cinetpay_transactions.order_by('-initiated_at')[:5]
        if not transactions:
            self.stdout.write('  Aucune transaction CinetPay enregistrée pour cette facture.')
        for t in transactions:
            self.stdout.write(f'\n  - transaction_id={t.transaction_id} status={t.status} amount={t.amount} {t.currency}')
            self.stdout.write(f'    initiated_at={t.initiated_at}')
            self.stdout.write(f'    status_message={t.status_message!r}')
            self.stdout.write(f'    cinetpay_transaction_id={t.cinetpay_transaction_id!r}')

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Payload exact qui serait envoyé à POST /v1/payment ===\n'))
        service = CinetPayService(invoice.site)
        payload = {
            'currency': 'XOF',
            'merchant_transaction_id': '<généré à la création>',
            'amount': int(invoice.balance),
            'lang': 'fr',
            'designation': f"Paiement facture {invoice.invoice_number}",
            'client_email': student_user.email,
            'client_phone_number': student_user.phone or '',
            'client_first_name': (student_user.first_name or 'Client')[:255] or 'Client',
            'client_last_name': (student_user.last_name or 'CinetPay')[:255] or 'CinetPay',
            'direct_pay': False,
            'success_url': service.success_url or '(FRONTEND_URL)/payment/success',
            'failed_url': service.failed_url or '(FRONTEND_URL)/payment/cancel',
            'notify_url': service.notify_url,
        }
        for k, v in payload.items():
            flag = ''
            if k in ('client_email', 'client_phone_number', 'notify_url') and not v:
                flag = '  <-- VIDE'
            self.stdout.write(f'  {k}: {v!r}{flag}')
