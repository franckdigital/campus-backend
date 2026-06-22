from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0002_add_financial_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='photo',
            field=models.TextField(blank=True, null=True),
        ),
    ]
