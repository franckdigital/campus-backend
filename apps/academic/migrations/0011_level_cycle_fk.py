import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds the new FK field alongside the legacy CharField (still named
    'cycle') so the data migration right after can read the old string
    values before they're removed. Field attributes match the final
    academic.models.Level.cycle definition exactly, so no further AlterField
    is needed once 0013 renames it into place."""

    dependencies = [
        ('academic', '0010_cycle'),
    ]

    operations = [
        migrations.AddField(
            model_name='level',
            name='cycle_fk',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='levels', to='academic.cycle',
                verbose_name='Cycle',
                help_text="Regroupement transversal (ex: Licence 3) utilisé pour configurer un barème valable pour toutes les filières de ce cycle.",
            ),
        ),
    ]
