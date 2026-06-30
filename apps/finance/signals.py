import logging
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment

logger = logging.getLogger(__name__)


def _get_or_create_open_session(site, payment_method=None):
    """
    Return an open CashSession for the site.
    If none exists, auto-create one (opening_balance=0) on the best matching
    cash register (Mobile Money for online/CinetPay, Espèces otherwise).
    Returns None if no cash register is configured for the site.
    """
    from .models import CashRegister, CashSession
    from django.contrib.auth import get_user_model

    if not site:
        return None

    # Choose the most appropriate cash register
    code_upper = (getattr(payment_method, 'code', '') or '').upper()
    is_online = any(k in code_upper for k in ('MOBILE', 'CINETPAY', 'MTN', 'ORANGE', 'WAVE', 'FLOOZ', 'MOOV'))

    cash_register = None
    if is_online:
        from django.db.models import Q
        cash_register = (
            CashRegister.objects
            .filter(site=site, is_active=True)
            .filter(
                Q(code__iregex=r'mobile|mm|cinetpay|wave|momo') |
                Q(name__iregex=r'mobile|cinetpay|wave|momo')
            )
            .first()
        )
        logger.info(
            "_get_or_create_open_session: site=%s is_online=True → register=%s",
            site, cash_register.name if cash_register else 'NONE',
        )
    if not cash_register:
        # Fallback: first active register for this site
        cash_register = CashRegister.objects.filter(site=site, is_active=True).first()

    if not cash_register:
        return None

    # Return existing open session
    open_session = CashSession.objects.filter(
        cash_register=cash_register,
        status='OPEN',
        is_active=True,
    ).first()
    if open_session:
        return open_session

    # Auto-create a session — use first superuser as opener
    User = get_user_model()
    system_user = (
        User.objects.filter(is_superuser=True, is_active=True).first()
        or User.objects.filter(is_staff=True, is_active=True).first()
    )
    if not system_user:
        logger.warning("_get_or_create_open_session: no staff user found for auto-session")
        return None

    session = CashSession.objects.create(
        cash_register=cash_register,
        opened_by=system_user,
        opening_balance=Decimal('0'),
        notes='Session automatique (paiement reçu)',
    )
    cash_register.is_open = True
    cash_register.save(update_fields=['is_open'])

    logger.info(
        "Auto-created cash session %s on register '%s' for site '%s'",
        session.id, cash_register.name, site,
    )
    return session


@receiver(post_save, sender=Payment)
def on_payment_save(sender, instance, created, **kwargs):
    """
    When a payment reaches status=SUCCESS:
    - Push-notify student and parents
    - Auto-create a CashTransaction IN on the site's cash register
      (auto-opens a session if none is active)
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
        from .models import CashTransaction

        # Skip if a cash transaction already exists for this payment (idempotent)
        if CashTransaction.objects.filter(payment=instance).exists():
            return

        student = instance.invoice.student
        site = getattr(instance.invoice, 'site', None) or getattr(student, 'site', None)

        open_session = _get_or_create_open_session(site, payment_method=instance.payment_method)
        if not open_session:
            logger.warning(
                "on_payment_save: no cash register for site %s — skipping auto cash TX (payment %s)",
                site, instance.id,
            )
            return

        # Human-readable description
        inv = instance.invoice
        is_inscription = inv.items.filter(
            fee_type__code__iregex=r'inscri|reg'
        ).exists()
        fee_label = "Frais d'inscription" if is_inscription else "Frais de scolarité"
        student_name = student.user.full_name or str(student)
        description = f"{fee_label} — {student_name} (facture {inv.invoice_number})"

        ref_date = instance.created_at.strftime('%Y%m%d') if instance.created_at else ''
        reference = f"PAY-{ref_date}-{str(instance.id)[:8].upper()}"

        tx = CashTransaction.objects.create(
            session=open_session,
            payment=instance,
            transaction_type='IN',
            amount=instance.amount,
            description=description,
            reference=reference,
        )

        # Update running balance on the register
        open_session.cash_register.current_balance += instance.amount
        open_session.cash_register.save(update_fields=['current_balance'])

        logger.info(
            "Auto cash TX %s created: %s FCFA → session %s / register '%s' (payment %s)",
            tx.id, instance.amount, open_session.id,
            open_session.cash_register.name, instance.id,
        )

    except Exception as exc:
        logger.error(
            "Auto cash transaction failed for payment %s: %s",
            instance.id, exc, exc_info=True,
        )
