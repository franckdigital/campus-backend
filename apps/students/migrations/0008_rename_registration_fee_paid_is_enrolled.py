# Frais d'inscription and frais de scolarité are merged into a single
# "scolarité" concept — a student is "inscrit" once they've paid a
# configurable minimum toward the cumulative tuition total (see
# apps.finance.models.get_min_enrollment_payment) instead of settling a
# separate inscription invoice in full. Renaming the flag rather than adding
# a new one so every existing call site (permission, signals, serializers)
# is forced to be reviewed against the new semantics.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0007_student_echeance_override'),
    ]

    operations = [
        migrations.RenameField(
            model_name='student',
            old_name='registration_fee_paid',
            new_name='is_enrolled',
        ),
        migrations.AlterField(
            model_name='student',
            name='is_enrolled',
            field=models.BooleanField(
                default=False,
                help_text="Inscrit = a payé au moins le seuil minimum (voir SystemConfig "
                          "MIN_ENROLLMENT_PAYMENT) du total de ses frais de scolarité.",
            ),
        ),
    ]
