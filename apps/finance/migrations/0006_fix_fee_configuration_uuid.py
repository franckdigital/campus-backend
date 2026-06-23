import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration 0005 created the fee_configurations table with BigAutoField (BIGINT)
    instead of UUIDField because it was generated before BaseModel was checked.
    This migration drops the bad table and recreates it with the correct UUID primary key.
    """

    dependencies = [
        ('academic', '0008_session_semester'),
        ('core', '0001_initial'),
        ('finance', '0005_fee_configuration'),
    ]

    operations = [
        # Drop the incorrectly-typed table (BIGINT id)
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS fee_configurations;',
            reverse_sql='',
        ),
        # Remove from Django state
        migrations.DeleteModel(name='FeeConfiguration'),
        # Recreate with correct UUID primary key (matching BaseModel)
        migrations.CreateModel(
            name='FeeConfiguration',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('registration_fee', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="Frais d'inscription")),
                ('tuition_fee', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Frais de scolarité')),
                ('label', models.CharField(blank=True, max_length=200, verbose_name='Libellé')),
                ('is_active', models.BooleanField(default=True)),
                ('academic_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fee_configurations', to='core.academicyear', verbose_name='Année académique')),
                ('level', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fee_configurations', to='academic.level', verbose_name='Niveau')),
                ('program', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fee_configurations', to='academic.program', verbose_name='Filière')),
                ('site', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fee_configurations', to='core.site', verbose_name='Site')),
            ],
            options={
                'verbose_name': 'Configuration des frais',
                'verbose_name_plural': 'Configurations des frais',
                'db_table': 'fee_configurations',
                'ordering': ['site', 'program', 'level'],
            },
        ),
    ]
