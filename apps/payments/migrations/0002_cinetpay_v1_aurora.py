from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cinetpayconfig',
            old_name='api_key',
            new_name='account_key',
        ),
        migrations.RenameField(
            model_name='cinetpayconfig',
            old_name='secret_key',
            new_name='account_password',
        ),
        migrations.RenameField(
            model_name='cinetpayconfig',
            old_name='return_url',
            new_name='success_url',
        ),
        migrations.RenameField(
            model_name='cinetpayconfig',
            old_name='cancel_url',
            new_name='failed_url',
        ),
        migrations.AlterField(
            model_name='cinetpayconfig',
            name='cinetpay_site_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='cinetpaytransaction',
            name='notify_token',
            field=models.CharField(blank=True, default='', max_length=100),
            preserve_default=False,
        ),
    ]
