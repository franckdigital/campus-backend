"""
Reset the scolarité invoice of an échéancier-reminder test student (see
seed_echeancier_students) back to a single partial payment, so the demo
reliably shows "Non à jour" and the reminder task actually fires — repeated
CinetPay test payments during earlier debugging pushed the paid amount above
the full échéancier total, which silently made the student look "à jour".

Read-only by default (dry-run); pass --yes to actually delete the existing
payments and recreate a single one at --amount.

Usage:
    python manage.py reset_echeancier_demo_payment --email fatou.bamba@escam-test.ci --amount 100000
    python manage.py reset_echeancier_demo_payment --email fatou.bamba@escam-test.ci --amount 100000 --yes
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Reset a test student's scolarité invoice to a single partial payment for the échéancier demo."

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--amount', type=int, required=True, help='New amount_paid on the scolarité invoice')
        parser.add_argument('--yes', action='store_true', help='Actually apply the change (default: dry-run)')

    def handle(self, *args, **options):
        from apps.students.models import Student
        from apps.finance.models import Invoice, Payment, PaymentMethod

        student = Student.objects.filter(user__email=options['email']).select_related('user').first()
        if not student:
            raise CommandError(f"Aucun etudiant avec l'email {options['email']!r}.")

        invoice = Invoice.objects.filter(
            student=student, is_active=True, notes__icontains='scolarite'
        ).exclude(status='CANCELLED').first()
        if not invoice:
            raise CommandError(f"Aucune facture de scolarite active trouvee pour {student}.")

        payments = Payment.objects.filter(invoice=invoice, is_active=True)
        new_amount = options['amount']

        self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== Facture {invoice.invoice_number} ({student}) ===\n'))
        self.stdout.write(f'  total={invoice.total} amount_paid actuel={invoice.amount_paid} balance={invoice.balance}')
        self.stdout.write(f'\n  Paiements existants ({payments.count()}):')
        for p in payments:
            self.stdout.write(f'    - {p.payment_number} | {p.amount} F | {p.status} | {p.reference}')

        self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== Action ===\n'))
        self.stdout.write(f'  Supprimer {payments.count()} paiement(s), recreer 1 paiement de {new_amount} F')

        if not options['yes']:
            self.stdout.write(self.style.WARNING('\nDry-run — rien modifie. Relancez avec --yes pour appliquer.'))
            return

        pay_method, _ = PaymentMethod.objects.get_or_create(
            code='ESPECES', defaults={'name': 'Especes', 'is_online': False},
        )

        with transaction.atomic():
            payments.delete()
            Payment.objects.create(
                payment_number=f"PAY-{student.matricule}-SCOL-DEMO",
                invoice=invoice, payment_method=pay_method,
                amount=new_amount, status='SUCCESS',
                reference='RECU-SCOL-DEMO', notes='Reset pour demo echeancier',
            )
            invoice.amount_paid = new_amount
            invoice.calculate_totals()
            invoice.save()

        invoice.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(
            f'\nOK. Facture {invoice.invoice_number}: total={invoice.total} '
            f'amount_paid={invoice.amount_paid} balance={invoice.balance} status={invoice.status}'
        ))
