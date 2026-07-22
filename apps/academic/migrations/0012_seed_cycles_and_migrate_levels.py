from django.db import migrations

# Matches the CYCLE_CHOICES this feature originally shipped with (see
# 0009_level_cycle / finance 0017_feeconfiguration_cycle) — preserved here so
# existing 'L1'/'L3'/... string values on Level/FeeConfiguration resolve to
# the same real Cycle row instead of being silently lost.
DEFAULT_CYCLES = [
    ('L1', 'Licence 1', 1), ('L2', 'Licence 2', 2), ('L3', 'Licence 3', 3),
    ('BTS1', 'BTS 1', 4), ('BTS2', 'BTS 2', 5),
    ('DUT1', 'DUT 1', 6), ('DUT2', 'DUT 2', 7),
    ('M1', 'Master 1', 8), ('M2', 'Master 2', 9),
]


def seed_and_migrate(apps, schema_editor):
    Cycle = apps.get_model('academic', 'Cycle')
    Level = apps.get_model('academic', 'Level')

    by_code = {}
    for code, name, order in DEFAULT_CYCLES:
        cycle, _ = Cycle.objects.get_or_create(code=code, defaults={'name': name, 'order': order})
        by_code[code] = cycle

    for level in Level.objects.exclude(cycle='').exclude(cycle__isnull=True):
        matching = by_code.get(level.cycle)
        if matching:
            level.cycle_fk = matching
            level.save(update_fields=['cycle_fk'])


def noop_reverse(apps, schema_editor):
    # Reversing would mean deleting Cycle rows a later migration may still
    # reference — not safe to auto-reverse, and not needed in practice.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0011_level_cycle_fk'),
    ]

    operations = [
        migrations.RunPython(seed_and_migrate, noop_reverse),
    ]
