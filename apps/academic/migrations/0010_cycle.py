import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0009_level_cycle'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cycle',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('order', models.PositiveIntegerField(default=1)),
            ],
            options={
                'verbose_name': 'Cycle',
                'verbose_name_plural': 'Cycles',
                'db_table': 'cycles',
                'ordering': ['order', 'name'],
            },
        ),
    ]
