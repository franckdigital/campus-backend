"""
Manually correct the unit_price of a single invoice line item and recompute
the parent invoice's totals/balance/status accordingly.

Exists because `_create_or_reprice` (apps.finance.models.ensure_student_invoices)
deliberately never touches an already-PAID/CANCELLED invoice — a barème that
was wrong at the time an invoice was created and paid (e.g. because of the
enrollment-resolution bug fixed alongside this command) can never self-heal
automatically. This is the explicit, audited way to correct one after the
fact — editing InvoiceItem.unit_price directly in Django admin would NOT be
enough on its own, since the parent Invoice's cached total/balance/status
only recompute when the Invoice itself is saved (see Invoice.calculate_totals).

Usage (dry-run by default — always run without --confirm first):
    python manage.py fix_invoice_item_price --invoice INV-ESCAM-CO-2026-00025 --new-price 300000
    python manage.py fix_invoice_item_price --invoice INV-ESCAM-CO-2026-00025 --new-price 300000 --confirm
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Correct one invoice item's unit_price and recompute the invoice's totals/status."

    def add_arguments(self, parser):
        parser.add_argument('--invoice', required=True, help='Invoice number, e.g. INV-ESCAM-CO-2026-00025')
        parser.add_argument('--fee-type', default=None, help="Fee type code to target if the invoice has more than one item (e.g. SCOLARITE, INSCRIPTION). Omit if the invoice has a single item.")
        parser.add_argument('--new-price', required=True, type=str, help='Correct unit price in FCFA, e.g. 300000')
        parser.add_argument('--confirm', action='store_true', help='Actually apply the change (default is a dry-run preview).')

    def handle(self, *args, **options):
        from decimal import Decimal, InvalidOperation
        from apps.finance.models import Invoice

        try:
            invoice = Invoice.objects.select_related('student__user').prefetch_related('items__fee_type').get(
                invoice_number=options['invoice']
            )
        except Invoice.DoesNotExist:
            raise CommandError(f"Aucune facture avec le numéro {options['invoice']!r}.")

        items = list(invoice.items.all())
        if not items:
            raise CommandError('Cette facture ne contient aucune ligne.')

        if options['fee_type']:
            items = [i for i in items if i.fee_type and i.fee_type.code.upper() == options['fee_type'].upper()]
            if not items:
                raise CommandError(f"Aucune ligne avec fee_type={options['fee_type']!r} sur cette facture.")
        if len(items) > 1:
            codes = ', '.join(i.fee_type.code for i in items if i.fee_type)
            raise CommandError(
                f"Cette facture a plusieurs lignes ({codes}) — précisez --fee-type pour choisir laquelle corriger."
            )
        item = items[0]

        try:
            new_price = Decimal(str(options['new_price'])).quantize(Decimal('1'))
        except InvalidOperation:
            raise CommandError(f"--new-price invalide : {options['new_price']!r}")

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== fix_invoice_item_price — {invoice.invoice_number} ({invoice.student.user.full_name}) ===\n"
        ))
        self.stdout.write(f"  Ligne             : {item.description!r} (fee_type={item.fee_type.code if item.fee_type else '—'})")
        self.stdout.write(f"  unit_price actuel : {item.unit_price} FCFA")
        self.stdout.write(f"  unit_price cible  : {new_price} FCFA")
        self.stdout.write(f"  Facture — total actuel: {invoice.total} | payé: {invoice.amount_paid} | solde: {invoice.balance} | statut: {invoice.status}")

        if item.unit_price == new_price:
            self.stdout.write(self.style.WARNING('\nunit_price est déjà égal à la valeur cible — rien à faire.'))
            return

        projected_total = invoice.subtotal - item.total + (item.quantity * new_price) - invoice.discount + invoice.tax
        projected_balance = projected_total - invoice.amount_paid
        self.stdout.write(f"\n  Facture — total projeté: {projected_total} | solde projeté: {projected_balance}")

        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                "\nAucune modification appliquée (dry-run). Relancez avec --confirm pour appliquer réellement."
            ))
            return

        item.unit_price = new_price
        item.save(update_fields=['unit_price', 'total'])
        invoice.refresh_from_db()
        invoice.save()  # recomputes subtotal/total/balance/status via calculate_totals()

        self.stdout.write(self.style.SUCCESS(
            f"\n-> Corrigé. Nouveau total: {invoice.total} | payé: {invoice.amount_paid} | "
            f"solde: {invoice.balance} | statut: {invoice.status}"
        ))
