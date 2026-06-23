import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Fix: migration 0005 created fee_configurations with BIGINT id instead of UUID.
    RunSQL handles the DB (drop + recreate with correct schema).
    SeparateDatabaseAndState ensures DeleteModel/CreateModel only update Django state
    without trying to DROP the already-dropped table.
    """

    dependencies = [
        ('academic', '0008_session_semester'),
        ('core', '0001_initial'),
        ('finance', '0005_fee_configuration'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # ── Database: raw SQL so IF EXISTS avoids errors ─────────────────
            database_operations=[
                migrations.RunSQL(
                    sql='DROP TABLE IF EXISTS `fee_configurations`;',
                    reverse_sql='',
                ),
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE `fee_configurations` (
                        `id`                char(32)        NOT NULL PRIMARY KEY,
                        `created_at`        datetime(6)     NOT NULL,
                        `updated_at`        datetime(6)     NOT NULL,
                        `registration_fee`  decimal(12,2)   NOT NULL DEFAULT '0.00',
                        `tuition_fee`       decimal(12,2)   NOT NULL DEFAULT '0.00',
                        `label`             varchar(200)    NOT NULL DEFAULT '',
                        `is_active`         tinyint(1)      NOT NULL DEFAULT 1,
                        `academic_year_id`  char(32)        DEFAULT NULL,
                        `level_id`          char(32)        DEFAULT NULL,
                        `program_id`        char(32)        DEFAULT NULL,
                        `site_id`           char(32)        DEFAULT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """,
                    reverse_sql='DROP TABLE IF EXISTS `fee_configurations`;',
                ),
            ],
            # ── State only: update Django's internal model registry ──────────
            state_operations=[
                migrations.DeleteModel(name='FeeConfiguration'),
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
            ],
        ),
    ]
