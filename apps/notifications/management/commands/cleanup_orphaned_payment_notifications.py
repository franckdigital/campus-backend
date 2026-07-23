from django.core.management.base import BaseCommand

from apps.notifications.models import Notification
from apps.finance.models import Payment


class Command(BaseCommand):
    help = (
        "One-time cleanup for a bug where deleting/correcting a validated Payment "
        "never retracted the 'Paiement confirmé' notification it had already sent "
        "(fixed going forward in PaymentViewSet.perform_update/perform_destroy). "
        "Finds PAYMENT notifications whose referenced payment no longer exists or "
        "is no longer SUCCESS, and removes them."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Actually delete the orphaned notifications (default is dry-run).',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        qs = Notification.objects.filter(
            notification_type='PAYMENT'
        ).exclude(data__payment_id__isnull=True)

        orphaned = []
        for n in qs:
            payment_id = n.data.get('payment_id')
            if not payment_id:
                continue
            payment = Payment.objects.filter(id=payment_id).first()
            if payment is None or payment.status != 'SUCCESS':
                orphaned.append(n)

        if not orphaned:
            self.stdout.write(self.style.SUCCESS('Aucune notification de paiement orpheline trouvée.'))
            return

        for n in orphaned:
            state = 'introuvable' if not Payment.objects.filter(id=n.data.get('payment_id')).exists() else 'non SUCCESS'
            self.stdout.write(
                f"- {n.recipient.full_name if n.recipient else '?'} <{n.recipient.email if n.recipient else '?'}> "
                f"— \"{n.title}\" ({n.created_at:%Y-%m-%d %H:%M}) — paiement {state}"
            )

        if apply:
            count = len(orphaned)
            Notification.objects.filter(id__in=[n.id for n in orphaned]).delete()
            self.stdout.write(self.style.SUCCESS(f'{count} notification(s) orpheline(s) supprimée(s).'))
        else:
            self.stdout.write(self.style.WARNING(
                f'{len(orphaned)} notification(s) orpheline(s) trouvée(s) — relancez avec --apply pour les supprimer.'
            ))
