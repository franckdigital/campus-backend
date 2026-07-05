# Step 3/3: the old combined fields are no longer read anywhere in the
# codebase (0012 already migrated every value into fee_category/amount rows)
# — safe to drop them now.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0012_split_registration_scolarite_rows'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='feeconfiguration',
            name='registration_fee',
        ),
        migrations.RemoveField(
            model_name='feeconfiguration',
            name='tuition_fee',
        ),
    ]
