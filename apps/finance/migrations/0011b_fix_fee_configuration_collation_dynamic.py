# Fix: migration 0007 hardcoded fee_configurations to COLLATE=utf8mb4_0900_ai_ci,
# assuming that's MySQL 8's default — but the actual default collation depends
# on how the database/schema itself was created (CREATE DATABASE ... COLLATE ...,
# or the server's collation-server setting), which varies by environment. On a
# database whose real default is e.g. utf8mb4_general_ci (every OTHER table here
# uses it, since none of their CreateModel migrations specify an explicit
# COLLATE), a hardcoded 0900_ai_ci makes fee_configurations the ONE table that
# disagrees, and any query joining/comparing it against another table (as the
# data migration in 0012 does implicitly via FK columns) fails with MySQL error
# 1267 "Illegal mix of collations". This migration reads whatever collation an
# already-existing, never-explicitly-overridden table (`sites`) actually has and
# converts fee_configurations (and fee_installments, added the same way by
# 0010) to match it — instead of guessing a fixed value.
from django.db import migrations


def fix_collation(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT TABLE_COLLATION FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'sites'"
        )
        row = cursor.fetchone()
        target_collation = row[0] if row else 'utf8mb4_0900_ai_ci'

        for table in ('fee_configurations', 'fee_installments'):
            cursor.execute(
                "SELECT TABLE_COLLATION FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
                [table],
            )
            current = cursor.fetchone()
            if current and current[0] != target_collation:
                cursor.execute(
                    f"ALTER TABLE `{table}` CONVERT TO CHARACTER SET utf8mb4 "
                    f"COLLATE {target_collation};"
                )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0011_feeconfiguration_add_category_fields'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_collation, noop_reverse),
    ]
