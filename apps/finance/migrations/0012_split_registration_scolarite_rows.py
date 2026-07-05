# Step 2/3: data migration. Every existing FeeConfiguration row (which had
# BOTH registration_fee and tuition_fee on the same row) becomes the
# SCOLARITE row (amount = old tuition_fee), and — when it had a non-zero
# registration_fee — a sibling INSCRIPTION row is created cloning the same
# site/programme/niveau/année/modalité/affectation scope with
# amount = old registration_fee. Échéancier installments (FeeInstallment)
# already point at the original row's id, which keeps being the SCOLARITE
# row, so no FK rewiring is needed there.
from django.db import migrations


def split_rows_forward(apps, schema_editor):
    FeeConfiguration = apps.get_model('finance', 'FeeConfiguration')

    for cfg in FeeConfiguration.objects.all():
        cfg.fee_category = 'SCOLARITE'
        cfg.amount = cfg.tuition_fee
        cfg.save(update_fields=['fee_category', 'amount'])

        if cfg.registration_fee and cfg.registration_fee > 0:
            FeeConfiguration.objects.create(
                site=cfg.site,
                program=cfg.program,
                level=cfg.level,
                academic_year=cfg.academic_year,
                modality=cfg.modality,
                affectation_status=cfg.affectation_status,
                fee_category='INSCRIPTION',
                amount=cfg.registration_fee,
                label=cfg.label,
                is_active=cfg.is_active,
            )


def split_rows_reverse(apps, schema_editor):
    """Fold each INSCRIPTION row's amount back into its SCOLARITE sibling's
    registration_fee, then delete the INSCRIPTION row — reconstructs the
    pre-split shape closely enough to unblock a rollback."""
    FeeConfiguration = apps.get_model('finance', 'FeeConfiguration')

    for inscr in FeeConfiguration.objects.filter(fee_category='INSCRIPTION'):
        sibling = FeeConfiguration.objects.filter(
            fee_category='SCOLARITE', site=inscr.site, program=inscr.program,
            level=inscr.level, academic_year=inscr.academic_year,
            modality=inscr.modality, affectation_status=inscr.affectation_status,
        ).first()
        if sibling:
            sibling.registration_fee = inscr.amount
            sibling.save(update_fields=['registration_fee'])
        inscr.delete()

    for cfg in FeeConfiguration.objects.filter(fee_category='SCOLARITE'):
        cfg.tuition_fee = cfg.amount
        cfg.save(update_fields=['tuition_fee'])


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0011_feeconfiguration_add_category_fields'),
    ]

    operations = [
        migrations.RunPython(split_rows_forward, split_rows_reverse),
    ]
