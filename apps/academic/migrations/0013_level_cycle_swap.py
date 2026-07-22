from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0012_seed_cycles_and_migrate_levels'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='level',
            name='cycle',
        ),
        migrations.RenameField(
            model_name='level',
            old_name='cycle_fk',
            new_name='cycle',
        ),
    ]
