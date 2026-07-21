# Frais d'inscription and frais de scolarité are merged into a single
# "scolarité" concept. For every active INSCRIPTION FeeConfiguration
# (barème), fold its amount into the matching SCOLARITE row for the same
# scope (site/programme/niveau/année/modalité/affectation) and deactivate
# the INSCRIPTION row; if no SCOLARITE sibling exists yet, the INSCRIPTION
# row itself becomes the SCOLARITE barème for that scope instead of being
# deactivated. Existing INSCRIPTION-coded invoices/payments are left exactly
# as they are (accounting history) — they already count toward the tuition
# cumulative via apps.finance.models._tuition_amount_paid, which matches
# both fee_type codes.
#
# Once barèmes are merged, recompute every active student's is_enrolled flag
# from real invoice data under the new rule (cumulative SCOLARITE+INSCRIPTION
# amount_paid >= MIN_ENROLLMENT_PAYMENT), so nobody is silently "un-enrolled"
# just because they'd fully paid a separate inscription invoice under the
# old rule but hadn't reached the new merged threshold — and, symmetrically,
# so a student who already paid enough scolarité to clear the new threshold
# shows as enrolled immediately rather than waiting for their next payment.
from decimal import Decimal, InvalidOperation
from django.db import migrations
from django.db.models import Sum


def _min_enrollment_payment(apps):
    SystemConfig = apps.get_model('core', 'SystemConfig')
    row = SystemConfig.objects.filter(key='MIN_ENROLLMENT_PAYMENT', site__isnull=True).first()
    if row:
        try:
            return Decimal(str(row.value))
        except (InvalidOperation, TypeError):
            pass
    return Decimal('50000')


def merge_forward(apps, schema_editor):
    FeeConfiguration = apps.get_model('finance', 'FeeConfiguration')
    Student = apps.get_model('students', 'Student')
    Invoice = apps.get_model('finance', 'Invoice')

    for inscr in FeeConfiguration.objects.filter(fee_category='INSCRIPTION', is_active=True):
        sibling = FeeConfiguration.objects.filter(
            fee_category='SCOLARITE', site=inscr.site, program=inscr.program,
            level=inscr.level, academic_year=inscr.academic_year,
            modality=inscr.modality, affectation_status=inscr.affectation_status,
        ).first()
        if sibling:
            sibling.amount = sibling.amount + inscr.amount
            sibling.save(update_fields=['amount'])
            inscr.is_active = False
            inscr.save(update_fields=['is_active'])
        else:
            inscr.fee_category = 'SCOLARITE'
            inscr.save(update_fields=['fee_category'])

    threshold = _min_enrollment_payment(apps)
    for student in Student.objects.filter(is_active=True):
        paid = Invoice.objects.filter(
            student=student, is_active=True, items__fee_type__code__in=['SCOLARITE', 'INSCRIPTION'],
        ).exclude(status='CANCELLED').distinct().aggregate(s=Sum('amount_paid'))['s'] or 0
        is_enrolled = paid >= threshold
        if student.is_enrolled != is_enrolled:
            student.is_enrolled = is_enrolled
            student.save(update_fields=['is_enrolled'])


def merge_reverse(apps, schema_editor):
    """Best-effort: cannot un-fold amounts once summed into a shared
    SCOLARITE row (no record of the original split), so this only reverses
    the rows that were converted in place (no sibling existed)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0014_payment_declared_payment_date_payment_payer_phone_and_more'),
        ('students', '0008_rename_registration_fee_paid_is_enrolled'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(merge_forward, merge_reverse),
    ]
