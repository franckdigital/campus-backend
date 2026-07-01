from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elearning', '0010_course_module'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='question_type',
            field=models.CharField(
                choices=[
                    ('QCU', 'Choix unique'),
                    ('QCM', 'Choix multiple'),
                    ('TRUEFALSE', 'Vrai ou Faux'),
                    ('TEXT', 'Texte libre'),
                    ('NUMERIC', 'Calcul / Numérique'),
                    ('MATCHING', 'Association'),
                    ('ORDERING', 'Glisser-déposer (ordre)'),
                ],
                default='QCU',
                max_length=20,
            ),
        ),
    ]
