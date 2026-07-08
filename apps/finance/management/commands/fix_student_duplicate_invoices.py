"""
Collapse a student's duplicate invoices per fee category (INSCRIPTION /
SCOLARITE) back down to one canonical invoice each, with a single payment
set to a target amount — for cleaning up test students whose invoice history
got polluted by repeated CinetPay test payments (each on-the-fly payment
without an invoice_id creates a brand new Invoice via
CinetPayInitiateView._create_invoice_for_payment).

For each fee category: the oldest active invoice is kept as canonical (its
existing payments are wiped and replaced with a single one at the target
amount); every other active invoice in that category is deactivated
(is_active=False), not deleted, so nothing is destroyed — a diagnostic will
still show them if needed.

Read-only by default (dry-run); pass --yes to apply.

Usage:
    python manage.py fix_student_duplicate_invoices --email fatou.bamba@escam-test.ci \\
        --inscription-paid 50000 --scolarite-paid 100000
    python manage.py fix_student_duplicate_invoices --email fatou.bamba@escam-test.ci \\
        --inscription-paid 50000 --scolarite-paid 100000 --yes
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Collapse a student's duplicate invoices per fee category down to one, with a single target payment."

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--inscription-paid', type=int, default=None, help='Target amount_paid for the INSCRIPTION invoice')
        parser.add_argument('--scolarite-paid', type=int, default=None, help='Target amount_paid for the SCOLARITE invoice')
        parser.add_argument('--yes', action='store_true', help='Actually apply (default: dry-run)')

    def handle(self, *args, **options):
        from apps.students.models import Student
        from apps.finance.models import Invoice, Payment, PaymentMethod

        student = Student.objects.filter(user__email=options['email']).select_related('user').first()
        if not student:
            raise CommandError(f"Aucun etudiant avec l'email {options['email']!r}.")

        targets = {
            'INSCRIPTION': options['inscription_paid'],
            'SCOLARITE': options['scolarite_paid'],
        }

        invoices = list(
            Invoice.objects.filter(student=student, is_active=True)
            .exclude(status='CANCELLED')
            .prefetch_related('items__fee_type')
            .order_by('created_at')
        )

        by_category = {}
        for inv in invoices:
            item = inv.items.first()
            category = item.fee_type.code if item and item.fee_type_id else 'UNKNOWN'
            by_category.setdefault(category, []).append(inv)

        self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== {student} — factures actives par categorie ===\n'))
        for category, invs in by_category.items():
            self.stdout.write(f'  {category}: {len(invs)} facture(s)')
            for inv in invs:
                self.stdout.write(f'    - {inv.invoice_number} total={inv.total} amount_paid={inv.amount_paid} created_at={inv.created_at}')

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Plan ===\n'))
        plan = []
        for category, invs in by_category.items():
            target = targets.get(category)
            if target is None:
                self.stdout.write(f'  {category}: pas de --{category.lower()}-paid fourni, categorie ignoree.')
                continue
            canonical = invs[0]
            duplicates = invs[1:]
            self.stdout.write(f'  {category}: garder {canonical.invoice_number} (paiement unique = {target} F)')
            for d in duplicates:
                self.stdout.write(f'    -> desactiver {d.invoice_number} (doublon)')
            plan.append((category, canonical, duplicates, target))

        if not options['yes']:
            self.stdout.write(self.style.WARNING('\nDry-run — rien modifie. Relancez avec --yes pour appliquer.'))
            return

        pay_method, _ = PaymentMethod.objects.get_or_create(
            code='ESPECES', defaults={'name': 'Especes', 'is_online': False},
        )

        with transaction.atomic():
            for category, canonical, duplicates, target in plan:
                for d in duplicates:
                    d.is_active = False
                    d.save(update_fields=['is_active'])

                Payment.objects.filter(invoice=canonical, is_active=True).delete()
                Payment.objects.create(
                    payment_number=f"PAY-{student.matricule}-{category[:4]}-DEMO",
                    invoice=canonical, payment_method=pay_method,
                    amount=target, status='SUCCESS',
                    reference=f'RECU-{category[:4]}-DEMO', notes='Reset pour demo echeancier',
                )
                canonical.amount_paid = target
                canonical.calculate_totals()
                canonical.save()

        self.stdout.write(self.style.SUCCESS('\nOK. Etat final:'))
        for category, canonical, duplicates, target in plan:
            canonical.refresh_from_db()
            self.stdout.write(
                f'  {category}: {canonical.invoice_number} total={canonical.total} '
                f'amount_paid={canonical.amount_paid} balance={canonical.balance} status={canonical.status}'
            )
