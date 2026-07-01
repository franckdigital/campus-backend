import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elearning', '0011_question_truefalse'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignment',
            name='quiz',
            field=models.OneToOneField(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assignment',
                to='elearning.quiz',
            ),
        ),
        migrations.AddField(
            model_name='assignment',
            name='course',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='course_assignments',
                to='elearning.course',
            ),
        ),
        migrations.AddField(
            model_name='assignment',
            name='virtual_classroom',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='classroom_assignments',
                to='elearning.virtualclassroom',
            ),
        ),
    ]
