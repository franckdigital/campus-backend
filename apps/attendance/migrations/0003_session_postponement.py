import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='attendancesession',
            name='is_postponed',
            field=models.BooleanField(
                default=False,
                help_text='Cours ajourné — personne ne sera marqué absent',
            ),
        ),
        migrations.AddField(
            model_name='attendancesession',
            name='postponement_reason',
            field=models.TextField(blank=True, help_text="Raison de l'ajournement"),
        ),
        migrations.AddField(
            model_name='attendancesession',
            name='postponed_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='postponed_attendance_sessions',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='attendancesession',
            name='postponed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
