import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Payment)
def on_payment_save(sender, instance, created, **kwargs):
    """Push-notify parents when a payment is validated (status → SUCCESS)."""
    if instance.status != 'SUCCESS':
        return
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
            )

        # Also push to the student
        push_to_user(
            student.user,
            title='✅ Paiement confirmé',
            body=f'Votre paiement de {amount} FCFA a été validé (facture {inv_no}).',
            data={'type': 'PAYMENT', 'payment_id': str(instance.id)},
        )

    except Exception as exc:
        logger.error("Payment push-notify failed: %s", exc)
