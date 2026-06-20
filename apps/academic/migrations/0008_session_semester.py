from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0007_teacher_experience'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='semester',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sessions',
                to='academic.semester',
            ),
        ),
    ]
