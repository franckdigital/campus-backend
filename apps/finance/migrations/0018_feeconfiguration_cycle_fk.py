import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds the new FK field alongside the legacy CharField (still named
    'cycle') so the data migration right after can read the old string
    values before they're removed."""

    dependencies = [
        ('finance', '0017_feeconfiguration_cycle'),
        ('academic', '0010_cycle'),
    ]

    operations = [
        migrations.AddField(
            model_name='feeconfiguration',
            name='cycle_fk',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='fee_configurations', to='academic.cycle',
                verbose_name='Cycle',
            ),
        ),
    ]
