from django.db import migrations


def migrate_cycle_data(apps, schema_editor):
    Cycle = apps.get_model('academic', 'Cycle')
    FeeConfiguration = apps.get_model('finance', 'FeeConfiguration')

    by_code = {c.code: c for c in Cycle.objects.all()}
    for fee_config in FeeConfiguration.objects.exclude(cycle='').exclude(cycle__isnull=True):
        matching = by_code.get(fee_config.cycle)
        if matching:
            fee_config.cycle_fk = matching
            fee_config.save(update_fields=['cycle_fk'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0018_feeconfiguration_cycle_fk'),
        # Ensures the default Cycle rows (L1, L3, ...) already exist by the
        # time this reads FeeConfiguration.cycle string values.
        ('academic', '0012_seed_cycles_and_migrate_levels'),
    ]

    operations = [
        migrations.RunPython(migrate_cycle_data, noop_reverse),
    ]
