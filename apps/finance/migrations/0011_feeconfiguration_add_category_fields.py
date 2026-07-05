# Step 1/3 of splitting FeeConfiguration into separate INSCRIPTION/SCOLARITE
# rows: add the new fields alongside the old ones (registration_fee/tuition_fee
# stay in place so the data migration in 0012 can still read them).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0010_feeinstallment'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='feeconfiguration',
            options={'ordering': ['site', 'program', 'level', 'fee_category'], 'verbose_name': 'Configuration des frais', 'verbose_name_plural': 'Configurations des frais'},
        ),
        migrations.AddField(
            model_name='feeconfiguration',
            name='fee_category',
            field=models.CharField(choices=[('INSCRIPTION', 'Inscription'), ('SCOLARITE', 'Scolarité')], default='SCOLARITE', max_length=20, verbose_name='Catégorie'),
        ),
        migrations.AddField(
            model_name='feeconfiguration',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Montant'),
        ),
    ]
