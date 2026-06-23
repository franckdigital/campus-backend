from django.db import migrations


class Migration(migrations.Migration):
    """
    Fix: fee_configurations was created with COLLATE=utf8mb4_unicode_ci while
    referenced tables (core_site, academic_*) use MySQL 8.0's default
    utf8mb4_0900_ai_ci. JOINs between them raise:
      "Illegal mix of collations (utf8mb4_unicode_ci,IMPLICIT) and
       (utf8mb4_0900_ai_ci,IMPLICIT) for operation '='"
    This migration converts the entire table to utf8mb4_0900_ai_ci.
    """

    dependencies = [
        ('finance', '0006_fix_fee_configuration_uuid'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE `fee_configurations` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
            reverse_sql="ALTER TABLE `fee_configurations` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        ),
    ]
