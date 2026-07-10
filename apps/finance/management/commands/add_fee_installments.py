"""
Add échéancier tranches (FeeInstallment rows) to an existing SCOLARITE
FeeConfiguration, identified by its id. Idempotent: re-running with the
same --installment labels updates those rows instead of duplicating them.

Usage:
    python manage.py add_fee_installments --config-id <uuid> \\
        --installment "1ere tranche:2026-07-10:400000" \\
        --installment "2eme tranche:2026-11-10:400000"

Each --installment is "label:due_date:amount" (due_date as YYYY-MM-DD).
The command warns (but does not block) if the tranche amounts don't sum
to the FeeConfiguration's own amount.
"""
import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Add/update échéancier tranches (FeeInstallment) on a SCOLARITE FeeConfiguration"

    def add_arguments(self, parser):
        parser.add_argument('--config-id', required=True, help='FeeConfiguration id (uuid)')
        parser.add_argument(
            '--installment', action='append', dest='installments', required=True,
            help='Repeatable. Format: "label:YYYY-MM-DD:amount"',
        )

    def handle(self, *args, **options):
        from apps.finance.models import FeeConfiguration, FeeInstallment

        try:
            fee_config = FeeConfiguration.objects.get(pk=options['config_id'])
        except FeeConfiguration.DoesNotExist:
            raise CommandError(f"FeeConfiguration {options['config_id']} introuvable.")

        if fee_config.fee_category != 'SCOLARITE':
            raise CommandError(
                f"FeeConfiguration {fee_config.id} est de categorie "
                f"{fee_config.fee_category!r} — l'echeancier ne s'applique qu'a SCOLARITE."
            )

        rows = []
        for i, raw in enumerate(options['installments']):
            try:
                label, due_date_str, amount_str = raw.split(':', 2)
                due_date = datetime.date.fromisoformat(due_date_str.strip())
                amount = Decimal(amount_str.strip())
            except ValueError:
                raise CommandError(f'--installment invalide: {raw!r} (attendu "label:YYYY-MM-DD:amount")')
            rows.append((i, label.strip(), due_date, amount))

        total = sum(r[3] for r in rows)
        self.stdout.write(f"Bareme: {fee_config} (montant={fee_config.amount})")
        if total != fee_config.amount:
            self.stdout.write(self.style.WARNING(
                f"  Attention: somme des tranches ({total}) != montant du bareme ({fee_config.amount})"
            ))

        with transaction.atomic():
            for order, label, due_date, amount in rows:
                inst, created = FeeInstallment.objects.update_or_create(
                    fee_configuration=fee_config, label=label,
                    defaults={'due_date': due_date, 'amount': amount, 'order': order},
                )
                self.stdout.write(
                    f"  {'Cree' if created else 'Mis a jour'}: {inst.label} — "
                    f"{inst.due_date} — {inst.amount}"
                )

        self.stdout.write(self.style.SUCCESS(
            f"\n{len(rows)} echeance(s) sur le bareme {fee_config.id}."
        ))
