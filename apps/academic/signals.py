import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='academic.Enrollment')
def deactivate_other_enrollments(sender, instance, created, **kwargs):
    """A student should only ever have one CURRENT (status=ENROLLED,
    is_active=True) Enrollment at a time. Nothing previously closed out a
    student's old Enrollment when they were re-enrolled into a new
    programme/level/year (e.g. last year's BTS row stayed active forever
    after this year's Licence 1 row was created) — Enrollment has no
    Meta.ordering and a random uuid4 pk, so with two active rows,
    apps.finance.models.resolve_current_enrollment (and every barème/invoice
    resolution built on it: ensure_student_invoices, the SCOLARITE
    échéancier, financial_summary) had no reliable way to tell which one was
    actually current, and could silently price a student's invoices off a
    stale programme's barème. This makes "current" unambiguous by
    construction instead of relying on downstream tie-breaking.

    Uses .update() (not .save()) so this never re-triggers this same signal.
    """
    if instance.status != 'ENROLLED' or not instance.is_active:
        return
    from .models import Enrollment
    stale = Enrollment.objects.filter(
        student_id=instance.student_id, is_active=True
    ).exclude(pk=instance.pk)
    count = stale.count()
    if count:
        stale.update(is_active=False)
        logger.info(
            "Deactivated %d stale active enrollment(s) for student %s after enrollment %s became current",
            count, instance.student_id, instance.pk,
        )
