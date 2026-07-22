from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0019_migrate_feeconfiguration_cycle_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='feeconfiguration',
            name='cycle',
        ),
        migrations.RenameField(
            model_name='feeconfiguration',
            old_name='cycle_fk',
            new_name='cycle',
        ),
    ]
