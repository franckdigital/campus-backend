# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='registration_fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='student',
            name='registration_fee_paid',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='student',
            name='tuition_fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='student',
            name='total_paid',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='student',
            name='remaining_balance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
