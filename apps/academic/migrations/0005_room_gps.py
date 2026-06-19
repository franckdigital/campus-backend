from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academic', '0004_add_level_subject'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='gps_latitude',
            field=models.DecimalField(
                blank=True, decimal_places=7, max_digits=10, null=True,
                help_text='Latitude WGS84 du centre de la salle',
            ),
        ),
        migrations.AddField(
            model_name='room',
            name='gps_longitude',
            field=models.DecimalField(
                blank=True, decimal_places=7, max_digits=10, null=True,
                help_text='Longitude WGS84 du centre de la salle',
            ),
        ),
        migrations.AddField(
            model_name='room',
            name='gps_radius_meters',
            field=models.PositiveIntegerField(
                default=50,
                help_text='Rayon en mètres autorisé pour le pointage',
            ),
        ),
    ]
