import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Payment)
def on_payment_save(sender, instance, created, **kwargs):
    """When a payment is validated (status → SUCCESS):
    - Push-notify parents and student
    - Auto-create a CashTransaction IN on the site's open session
    """
    if instance.status != 'SUCCESS':
        return

    # ── Push notifications ────────────────────────────────────────────────
    try:
        from apps.notifications.push import push_to_user
        from apps.students.models import StudentParent

        student = instance.invoice.student
        amount = instance.amount
        inv_no = instance.invoice.invoice_number

        parents = StudentParent.objects.filter(
            student=student, receives_notifications=True
        ).select_related('parent__user')

        for sp in parents:
            push_to_user(
                sp.parent.user,
                title='✅ Paiement reçu',
                body=(
                    f'Un paiement de {amount} FCFA a été enregistré pour '
                    f'{student.user.full_name} (facture {inv_no}).'
                ),
                data={
                    'type':       'PAYMENT',
                    'payment_id': str(instance.id),
                    'student_id': str(student.id),
                },
                channel_id='payments',
            )

        push_to_user(
            student.user,
            title='✅ Paiement confirmé',
            body=f'Votre paiement de {amount} FCFA a été validé (facture {inv_no}).',
            data={'type': 'PAYMENT', 'payment_id': str(instance.id)},
            channel_id='payments',
        )

    except Exception as exc:
        logger.error("Payment push-notify failed: %s", exc)

    # ── Auto cash transaction ─────────────────────────────────────────────
    try:
        from .models import CashSession, CashTransaction

        # Skip if a cash transaction already exists for this payment
        if instance.cash_transactions.exists():
            return

        student = instance.invoice.student
        site = student.site
        if not site:
            return

        # Find the latest open session for this site
        open_session = (
            CashSession.objects
            .filter(
                cash_register__site=site,
                status='OPEN',
                is_active=True,
            )
            .select_related('cash_register')
            .order_by('-opened_at')
            .first()
        )
        if not open_session:
            logger.info(
                "on_payment_save: no open cash session for site %s — skipping auto cash TX (payment %s)",
                site, instance.id,
            )
            return

        # Build a human-readable description from the invoice
        from django.db.models import Q
        inv = instance.invoice
        inv_text = f"{inv.notes or ''} {inv.description or ''}".lower()
        is_inscription = 'inscription' in inv_text or inv.items.filter(
            Q(description__icontains='inscription') |
            Q(fee_type__name__icontains='inscription') |
            Q(fee_type__code__icontains='REGISTRATION')
        ).exists()
        fee_label = "Frais d'inscription" if is_inscription else "Frais de scolarité"
        student_name = student.user.get_full_name() or str(student)
        description = f"{fee_label} — {student_name} (facture {inv.invoice_number})"

        ref_date = instance.created_at.strftime('%Y%m%d') if instance.created_at else ''
        reference = f"PAY-{ref_date}-{str(instance.id)[:8].upper()}"

        CashTransaction.objects.create(
            session=open_session,
            payment=instance,
            transaction_type='IN',
            amount=instance.amount,
            description=description,
            reference=reference,
        )

        # Update cash register running balance
        open_session.cash_register.current_balance = (
            open_session.cash_register.current_balance + instance.amount
        )
        open_session.cash_register.save(update_fields=['current_balance'])

        logger.info(
            "Auto cash TX created: %s FCFA → session %s (payment %s)",
            instance.amount, open_session.id, instance.id,
        )

    except Exception as exc:
        logger.error("Auto cash transaction failed for payment %s: %s", instance.id, exc, exc_info=True)
