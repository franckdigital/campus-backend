from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elearning', '0016_quiz_subject_file_exam_grade_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='examsession',
            name='submission_file',
            field=models.FileField(blank=True, null=True, upload_to='exam_submissions/'),
        ),
        migrations.AddField(
            model_name='examsession',
            name='submission_note',
            field=models.TextField(blank=True),
        ),
    ]
