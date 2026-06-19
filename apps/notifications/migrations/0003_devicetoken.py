import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_notificationtemplate_alter_notification_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceToken',
            fields=[
                ('id',         models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active',  models.BooleanField(default=True)),
                ('token',      models.CharField(max_length=512)),
                ('platform',   models.CharField(
                    choices=[('EXPO', 'Expo'), ('FCM', 'Firebase Android'), ('APNS', 'Apple iOS')],
                    default='EXPO', max_length=20
                )),
                ('last_used',  models.DateTimeField(auto_now=True)),
                ('user',       models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='device_tokens',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name':        'Token appareil',
                'verbose_name_plural': 'Tokens appareils',
                'db_table':            'device_tokens',
            },
        ),
        migrations.AddConstraint(
            model_name='devicetoken',
            constraint=models.UniqueConstraint(
                fields=['user', 'token'],
                name='unique_user_token',
            ),
        ),
    ]
