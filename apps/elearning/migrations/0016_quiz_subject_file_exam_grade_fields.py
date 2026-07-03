from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('elearning', '0015_course_video_url'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Quiz.subject_file
        migrations.AddField(
            model_name='quiz',
            name='subject_file',
            field=models.FileField(blank=True, null=True, upload_to='quiz_subjects/'),
        ),
        # SecureExam.subject_file + max_score
        migrations.AddField(
            model_name='secureexam',
            name='subject_file',
            field=models.FileField(blank=True, null=True, upload_to='exam_subjects/'),
        ),
        migrations.AddField(
            model_name='secureexam',
            name='max_score',
            field=models.DecimalField(decimal_places=2, default=20, max_digits=5),
        ),
        # ExamSession correction fields
        migrations.AddField(
            model_name='examsession',
            name='score',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='examsession',
            name='feedback',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='examsession',
            name='corrected_file',
            field=models.FileField(blank=True, null=True, upload_to='exam_corrections/'),
        ),
        migrations.AddField(
            model_name='examsession',
            name='corrected_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='graded_exam_sessions',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='examsession',
            name='corrected_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
