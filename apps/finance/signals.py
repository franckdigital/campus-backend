import logging
from decimal import Decimal
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment

logger = logging.getLogger(__name__)


def _get_or_create_open_session(site, payment_method=None):
    """
    Return an open CashSession for the site.
    For online/Mobile Money payments: always use the dedicated Mobile Money register,
    auto-creating it if missing. Never fall back to the cash register for online payments.
    For cash payments: use the first active register.
    """
    from .models import CashRegister, CashSession
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    if not site:
        return None

    code_upper = (getattr(payment_method, 'code', '') or '').upper()
    is_online = any(k in code_upper for k in ('MOBILE', 'CINETPAY', 'MTN', 'ORANGE', 'WAVE', 'FLOOZ', 'MOOV'))

    User = get_user_model()
    system_user = (
        User.objects.filter(is_superuser=True, is_active=True).first()
        or User.objects.filter(is_staff=True, is_active=True).first()
    )

    if is_online:
        # Find existing Mobile Money register
        cash_register = (
            CashRegister.objects
            .filter(site=site, is_active=True)
            .filter(
                Q(code__iregex=r'mobile|mm|cinetpay|wave|momo') |
                Q(name__iregex=r'mobile|cinetpay|wave|momo')
            )
            .first()
        )
        # Auto-create the Mobile Money register if it doesn't exist — makes it permanent
        if not cash_register:
            cash_register = CashRegister.objects.create(
                site=site,
                name='Caisse Mobile Money',
                code='MOBILE_MONEY',
                is_active=True,
                current_balance=Decimal('0'),
            )
            logger.info(
                "Auto-created Mobile Money cash register for site '%s'", site,
            )
    else:
        cash_register = CashRegister.objects.filter(site=site, is_active=True).exclude(
            Q(code__iregex=r'mobile|mm|cinetpay|wave|momo') |
            Q(name__iregex=r'mobile|cinetpay|wave|momo')
        ).first() or CashRegister.objects.filter(site=site, is_active=True).first()

    if not cash_register:
        logger.warning("_get_or_create_open_session: no cash register found for site %s", site)
        return None

    logger.info(
        "_get_or_create_open_session: site=%s is_online=%s → register='%s'",
        site, is_online, cash_register.name,
    )

    # Return existing open session
    open_session = CashSession.objects.filter(
        cash_register=cash_register,
        status='OPEN',
        is_active=True,
    ).first()
    if open_session:
        return open_session

    # No open session: auto-create one carrying forward the current balance
    if not system_user:
        logger.warning("_get_or_create_open_session: no staff user found for auto-session")
        return None

    session = CashSession.objects.create(
        cash_register=cash_register,
        opened_by=system_user,
        opening_balance=cash_register.current_balance,
        notes='Session automatique (paiement reçu)',
    )
    cash_register.is_open = True
    cash_register.save(update_fields=['is_open'])

    logger.info(
        "Auto-created cash session %s on register '%s' for site '%s' (balance=%s)",
        session.id, cash_register.name, site, cash_register.current_balance,
    )
    return session


def _auto_create_cash_transaction(instance):
    """Best-effort cash-register bookkeeping side effect. Must never be able
    to skip the invoice amount_paid sync in on_payment_save — this used to
    live inline in that function with early `return`s that, on no-open-session
    or already-has-a-cash-tx, exited the WHOLE signal handler and silently
    skipped the invoice sync below it. Extracted into its own function so its
    `return`s only ever exit this helper.
    """
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


@receiver(post_save, sender=Payment)
def on_payment_save(sender, instance, created, **kwargs):
    """
    When a payment reaches status=SUCCESS:
    - Sync the invoice's amount_paid/balance/status from all SUCCESS payments
    - Push-notify student and parents
    - Auto-create a CashTransaction IN on the site's cash register
      (auto-opens a session if none is active)
    """
    if instance.status != 'SUCCESS':
        return

    # ── Sync invoice amount_paid from all SUCCESS payments (source of truth
    # for every total/balance shown across admin, student web and mobile) —
    # this must run unconditionally, independent of the best-effort steps
    # below, so a failure/skip in cash-register bookkeeping or notifications
    # can never leave the invoice's totals stale. ──────────────────────────
    try:
        invoice = instance.invoice
        invoice.refresh_from_db()
        total_success = (
            Payment.objects.filter(invoice=invoice, status='SUCCESS')
            .aggregate(total=Sum('amount'))['total'] or Decimal('0')
        )
        if invoice.amount_paid != total_success:
            invoice.amount_paid = total_success
            invoice.calculate_totals()
            invoice.save(update_fields=['amount_paid', 'balance', 'status', 'subtotal', 'total'])
            logger.info(
                "Invoice %s amount_paid synced to %s FCFA (was %s)",
                invoice.invoice_number, total_success, invoice.amount_paid,
            )
    except Exception as exc:
        logger.error(
            "Invoice sync failed for payment %s: %s", instance.id, exc, exc_info=True,
        )

    # ── Notifications (in-app + push) ────────────────────────────────────
    try:
        from apps.notifications.services import notify_payment_validated
        notify_payment_validated(instance)
    except Exception as exc:
        logger.error("Payment notify failed for payment %s: %s", instance.id, exc)

    # ── Auto cash transaction ─────────────────────────────────────────────
    try:
        _auto_create_cash_transaction(instance)
    except Exception as exc:
        logger.error(
            "Auto cash transaction failed for payment %s: %s",
            instance.id, exc, exc_info=True,
        )
