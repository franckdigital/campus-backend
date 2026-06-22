from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0003_photo_textfield'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parent',
            name='relationship',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('FATHER',      'Père'),
                    ('MOTHER',      'Mère'),
                    ('GUARDIAN',    'Tuteur légal'),
                    ('UNCLE',       'Oncle'),
                    ('AUNT',        'Tante'),
                    ('GRANDPARENT', 'Grand-parent'),
                    ('SIBLING',     'Frère / Sœur'),
                    ('OTHER',       'Autre'),
                ],
                default='GUARDIAN',
            ),
        ),
    ]
