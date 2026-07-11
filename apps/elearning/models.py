from django.db import models
from django.conf import settings
from apps.core.models import BaseModel
from apps.academic.models import Class, Subject, Session, TeacherProfile
from apps.students.models import Student


class ZoomMeeting(BaseModel):
    """Zoom meeting linked to a session."""
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='zoom_meetings'
    )
    meeting_id = models.CharField(max_length=100)
    topic = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    duration = models.PositiveIntegerField(default=60)
    join_url = models.URLField()
    start_url = models.URLField(blank=True)
    password = models.CharField(max_length=50, blank=True)
    
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='hosted_meetings'
    )
    
    is_recorded = models.BooleanField(default=False)
    recording_url = models.URLField(blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_zoom_meetings'
    )

    class Meta:
        db_table = 'zoom_meetings'
        verbose_name = 'Réunion Zoom'
        verbose_name_plural = 'Réunions Zoom'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.topic} - {self.start_time}"


class Chapter(BaseModel):
    """Group of lessons within a subject/class — one step of the learning path
    (Programme → UE → Chapitre → Leçon).
    """
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='chapters'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='chapters'
    )

    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        db_table = 'chapters'
        verbose_name = 'Chapitre'
        verbose_name_plural = 'Chapitres'
        ordering = ['class_obj', 'subject', 'order']

    def __str__(self):
        return f"{self.class_obj.code} - {self.subject.code} - {self.title}"

    def _siblings(self):
        return Chapter.objects.filter(
            class_obj=self.class_obj, subject=self.subject, is_active=True
        ).order_by('order')

    def is_completed_by(self, student, completed_ids=None):
        lessons = self.lessons.filter(is_active=True, is_published=True)
        if not lessons.exists():
            return True
        return all(l.is_completed_by(student, completed_ids) for l in lessons)

    def is_unlocked_for(self, student, completed_ids=None):
        prev = self._siblings().filter(order__lt=self.order).last()
        if not prev:
            return True
        return prev.is_completed_by(student, completed_ids)


class Lesson(BaseModel):
    """Lesson/Course content."""
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content = models.TextField(blank=True)

    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lessons'
    )
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lessons'
    )

    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    # Verrouillage intelligent — conditions de complétion
    min_watch_percent = models.PositiveSmallIntegerField(default=100)
    min_duration_seconds = models.PositiveIntegerField(default=0)
    requires_assignment = models.BooleanField(default=False)
    requires_quiz = models.BooleanField(default=False)

    zoom_meeting = models.ForeignKey(
        ZoomMeeting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lessons'
    )

    class Meta:
        db_table = 'lessons'
        verbose_name = 'Leçon'
        verbose_name_plural = 'Leçons'
        ordering = ['class_obj', 'subject', 'order']

    def __str__(self):
        return f"{self.class_obj.code} - {self.subject.code} - {self.title}"

    def publish(self):
        from django.utils import timezone
        self.is_published = True
        self.published_at = timezone.now()
        self.save()

    def _siblings(self):
        if self.chapter_id:
            return self.chapter.lessons.filter(is_active=True, is_published=True).order_by('order')
        return Lesson.objects.filter(
            class_obj=self.class_obj, subject=self.subject, chapter__isnull=True,
            is_active=True, is_published=True
        ).order_by('order')

    def is_completed_by(self, student, completed_ids=None):
        # completed_ids, when provided, is a pre-fetched set of this student's
        # completed lesson IDs (one query for a whole list) — used to avoid a
        # progress_records query per lesson when serializing a list of lessons.
        if completed_ids is not None:
            return self.id in completed_ids
        progress = self.progress_records.filter(student=student).first()
        return bool(progress and progress.is_completed)

    def is_unlocked_for(self, student, completed_ids=None):
        if self.chapter_id and not self.chapter.is_unlocked_for(student, completed_ids):
            return False
        prev = self._siblings().filter(order__lt=self.order).last()
        if not prev:
            return True
        return prev.is_completed_by(student, completed_ids)


class LessonAttachment(BaseModel):
    """Content block of a lesson (course builder).

    Originally a flat file attachment; extended to a typed, ordered
    content block so a lesson can be built as a drag&drop sequence of
    video/text/pdf/html/image/audio/iframe/youtube/vimeo/file blocks.
    """
    BLOCK_TYPE_CHOICES = [
        ('FILE', 'Fichier'),
        ('VIDEO', 'Vidéo'),
        ('AUDIO', 'Audio'),
        ('IMAGE', 'Image'),
        ('PDF', 'PDF'),
        ('TEXT', 'Texte'),
        ('HTML', 'HTML'),
        ('IFRAME', 'Iframe'),
        ('YOUTUBE', 'YouTube'),
        ('VIMEO', 'Vimeo'),
    ]

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    title = models.CharField(max_length=255)
    block_type = models.CharField(max_length=20, choices=BLOCK_TYPE_CHOICES, default='FILE')
    order = models.PositiveIntegerField(default=0)

    file = models.FileField(upload_to='lessons/attachments/', blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.PositiveIntegerField(default=0)

    content = models.TextField(blank=True)  # TEXT / HTML body
    url = models.URLField(blank=True)       # YOUTUBE / VIMEO / IFRAME link

    class Meta:
        db_table = 'lesson_attachments'
        verbose_name = 'Bloc de contenu de leçon'
        verbose_name_plural = 'Blocs de contenu de leçons'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            self.file_type = self.file.name.split('.')[-1].lower()
        super().save(*args, **kwargs)


class LessonProgress(BaseModel):
    """Tracks a student's progress/completion on a lesson (parcours pédagogique)."""
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='lesson_progress'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='progress_records'
    )

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    watch_percent = models.PositiveSmallIntegerField(default=0)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'lesson_progress'
        verbose_name = 'Progression de leçon'
        verbose_name_plural = 'Progressions de leçons'
        unique_together = ['student', 'lesson']

    def __str__(self):
        return f"{self.student.matricule} - {self.lesson.title} - {self.watch_percent}%"

    def evaluate_completion(self):
        """Re-check completion gates and flip is_completed/completed_at accordingly."""
        from django.utils import timezone

        lesson = self.lesson
        ok_watch = self.watch_percent >= lesson.min_watch_percent
        ok_time = self.time_spent_seconds >= lesson.min_duration_seconds
        ok_assignment = True
        if lesson.requires_assignment:
            ok_assignment = lesson.assignments.filter(
                is_active=True,
                submissions__student=self.student
            ).exists()
        ok_quiz = True
        if lesson.requires_quiz:
            ok_quiz = QuizAttempt.objects.filter(
                quiz__lesson=lesson, student=self.student, is_passed=True
            ).exists()

        completed = ok_watch and ok_time and ok_assignment and ok_quiz
        if completed and not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
        elif not completed and self.is_completed:
            self.is_completed = False
            self.completed_at = None
        self.save()
        return self.is_completed


class Quiz(BaseModel):
    """Quiz intelligent — QCM/QCU/texte libre/calcul/association/glisser-déposer."""
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='quizzes')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quizzes')
    lesson = models.ForeignKey(
        Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='quizzes'
    )

    time_limit_minutes = models.PositiveIntegerField(default=0)   # 0 = pas de limite
    max_attempts = models.PositiveIntegerField(default=0)          # 0 = illimité
    pass_score_percent = models.PositiveSmallIntegerField(default=50)
    shuffle_questions = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    subject_file = models.FileField(upload_to='quiz_subjects/', blank=True, null=True)

    class Meta:
        db_table = 'quizzes'
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quiz'
        ordering = ['class_obj', 'subject', 'title']

    def __str__(self):
        return self.title

    @property
    def max_score(self):
        from decimal import Decimal
        return self.questions.filter(is_active=True).aggregate(
            total=models.Sum('points')
        )['total'] or Decimal('0')


class Question(BaseModel):
    QUESTION_TYPE_CHOICES = [
        ('QCU', 'Choix unique'),
        ('QCM', 'Choix multiple'),
        ('TRUEFALSE', 'Vrai ou Faux'),
        ('TEXT', 'Texte libre'),
        ('NUMERIC', 'Calcul / Numérique'),
        ('MATCHING', 'Association'),
        ('ORDERING', 'Glisser-déposer (ordre)'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='QCU')
    text = models.TextField()
    image = models.ImageField(upload_to='quiz/questions/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    points = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    explanation = models.TextField(blank=True)

    # NUMERIC
    numeric_answer = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    numeric_tolerance = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    # TEXT — optionnel : si renseigné, correction auto par correspondance exacte (insensible à la casse)
    text_answer = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'quiz_questions'
        verbose_name = 'Question de quiz'
        verbose_name_plural = 'Questions de quiz'
        ordering = ['quiz', 'order']

    def __str__(self):
        return f"{self.quiz.title} - Q{self.order}"


class Choice(BaseModel):
    """QCU/QCM: option (is_correct).
    MATCHING: élément gauche (text) + sa paire correcte (match_text).
    ORDERING: élément (text) + sa position correcte (order).
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    match_text = models.CharField(max_length=500, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'quiz_choices'
        verbose_name = 'Choix de question'
        verbose_name_plural = 'Choix de questions'
        ordering = ['question', 'order']

    def __str__(self):
        return f"{self.question_id} - {self.text}"


class QuizAttempt(BaseModel):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_attempts')

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_passed = models.BooleanField(default=False)
    is_graded = models.BooleanField(default=False)  # False tant qu'une réponse TEXT attend une correction manuelle

    class Meta:
        db_table = 'quiz_attempts'
        verbose_name = 'Tentative de quiz'
        verbose_name_plural = 'Tentatives de quiz'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.matricule} - {self.quiz.title} - {self.percent}%"

    def finalize(self):
        """Aggregate answers into score/percent/is_passed/is_graded."""
        from decimal import Decimal
        from django.utils import timezone

        answers = self.answers.select_related('question').all()
        self.score = sum((a.points_earned for a in answers), Decimal('0'))
        self.max_score = self.quiz.max_score
        self.percent = (self.score / self.max_score * 100) if self.max_score > 0 else Decimal('0')
        self.is_graded = not answers.filter(is_correct__isnull=True).exists()
        self.is_passed = self.is_graded and self.percent >= self.quiz.pass_score_percent
        self.submitted_at = self.submitted_at or timezone.now()
        self.save()
        return self


class AttemptAnswer(BaseModel):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')

    selected_choices = models.ManyToManyField(Choice, blank=True, related_name='selected_in_answers')
    text_response = models.TextField(blank=True)
    numeric_response = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    ordering_response = models.JSONField(default=list, blank=True)   # [choice_id, ...] dans l'ordre soumis
    matching_response = models.JSONField(default=dict, blank=True)   # {choice_id: texte soumis}

    is_correct = models.BooleanField(null=True, blank=True)  # null = en attente de correction manuelle (TEXT)
    points_earned = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    manual_feedback = models.TextField(blank=True)

    class Meta:
        db_table = 'quiz_attempt_answers'
        verbose_name = 'Réponse de tentative'
        verbose_name_plural = 'Réponses de tentatives'
        unique_together = ['attempt', 'question']

    def __str__(self):
        return f"{self.attempt_id} - Q{self.question_id}"

    def grade(self):
        """Auto-grade based on question type. TEXT without a reference answer stays pending (is_correct=None)."""
        from decimal import Decimal

        q = self.question
        points = Decimal(str(q.points))

        if q.question_type == 'QCU':
            correct_ids = set(q.choices.filter(is_correct=True).values_list('id', flat=True))
            selected_ids = set(self.selected_choices.values_list('id', flat=True))
            self.is_correct = selected_ids == correct_ids and len(selected_ids) == 1
            self.points_earned = points if self.is_correct else Decimal('0')

        elif q.question_type == 'QCM':
            correct_ids = set(q.choices.filter(is_correct=True).values_list('id', flat=True))
            selected_ids = set(self.selected_choices.values_list('id', flat=True))
            self.is_correct = selected_ids == correct_ids
            self.points_earned = points if self.is_correct else Decimal('0')

        elif q.question_type == 'NUMERIC':
            if self.numeric_response is not None and q.numeric_answer is not None:
                diff = abs(self.numeric_response - q.numeric_answer)
                self.is_correct = diff <= q.numeric_tolerance
            else:
                self.is_correct = False
            self.points_earned = points if self.is_correct else Decimal('0')

        elif q.question_type == 'TEXT':
            if q.text_answer.strip():
                self.is_correct = self.text_response.strip().lower() == q.text_answer.strip().lower()
                self.points_earned = points if self.is_correct else Decimal('0')
            else:
                self.is_correct = None  # correction manuelle requise
                self.points_earned = Decimal('0')

        elif q.question_type == 'MATCHING':
            pairs = list(q.choices.filter(is_active=True))
            total = len(pairs) or 1
            correct_count = sum(
                1 for c in pairs
                if (self.matching_response or {}).get(str(c.id), '').strip().lower() == (c.match_text or '').strip().lower()
            )
            self.is_correct = correct_count == total
            self.points_earned = (points * correct_count / total).quantize(Decimal('0.01'))

        elif q.question_type == 'ORDERING':
            correct_order = list(q.choices.filter(is_active=True).order_by('order').values_list('id', flat=True))
            submitted = [str(cid) for cid in (self.ordering_response or [])]
            total = len(correct_order) or 1
            correct_count = sum(
                1 for i, cid in enumerate(correct_order)
                if i < len(submitted) and submitted[i] == str(cid)
            )
            self.is_correct = correct_count == total
            self.points_earned = (points * correct_count / total).quantize(Decimal('0.01'))

        elif q.question_type == 'TRUEFALSE':
            correct_ids = set(q.choices.filter(is_correct=True).values_list('id', flat=True))
            selected_ids = set(self.selected_choices.values_list('id', flat=True))
            self.is_correct = selected_ids == correct_ids and len(selected_ids) == 1
            self.points_earned = points if self.is_correct else Decimal('0')

        self.save()
        return self.is_correct


class Assignment(BaseModel):
    """Assignment/Homework."""
    STATUS_CHOICES = [
        ('DRAFT', 'Brouillon'),
        ('PUBLISHED', 'Publié'),
        ('CLOSED', 'Fermé'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    instructions = models.TextField(blank=True)
    
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assignments'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments'
    )
    
    due_date = models.DateTimeField()
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    published_at = models.DateTimeField(null=True, blank=True)
    
    allow_late_submission = models.BooleanField(default=False)
    late_penalty_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    attachment = models.FileField(upload_to='assignments/', blank=True, null=True)

    # Composition en ligne : quiz lié pour exercices auto-corrigés
    quiz = models.OneToOneField(
        'Quiz', on_delete=models.SET_NULL, null=True, blank=True, related_name='assignment'
    )
    # Liens contextuels optionnels
    course = models.ForeignKey(
        'Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='course_assignments'
    )
    virtual_classroom = models.ForeignKey(
        'VirtualClassroom', on_delete=models.SET_NULL, null=True, blank=True, related_name='classroom_assignments'
    )

    class Meta:
        db_table = 'assignments'
        verbose_name = 'Devoir'
        verbose_name_plural = 'Devoirs'
        ordering = ['-due_date']

    def __str__(self):
        return f"{self.class_obj.code} - {self.title}"

    def publish(self):
        from django.utils import timezone
        self.status = 'PUBLISHED'
        self.published_at = timezone.now()
        self.save()

    @property
    def submission_count(self):
        # len() on the prefetched cache instead of .count(), which would
        # always issue a fresh COUNT query even when submissions were
        # already prefetched by the ViewSet.
        return len(self.submissions.all())


class AssignmentSubmission(BaseModel):
    """Student submission for an assignment."""
    STATUS_CHOICES = [
        ('SUBMITTED', 'Soumis'),
        ('LATE', 'En retard'),
        ('GRADED', 'Noté'),
        ('RETURNED', 'Rendu'),
    ]

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='submissions/', blank=True, null=True)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    is_late = models.BooleanField(default=False)

    class Meta:
        db_table = 'assignment_submissions'
        verbose_name = 'Soumission de devoir'
        verbose_name_plural = 'Soumissions de devoirs'
        unique_together = ['assignment', 'student']
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.assignment.title} - {self.student.matricule}"

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if not self.pk:
            if timezone.now() > self.assignment.due_date:
                self.is_late = True
                self.status = 'LATE'
        super().save(*args, **kwargs)


class AssignmentCorrection(BaseModel):
    """Correction for a submission."""
    submission = models.OneToOneField(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name='correction'
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    feedback = models.TextField(blank=True)
    corrected_file = models.FileField(upload_to='corrections/', blank=True, null=True)

    corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='corrections'
    )
    corrected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'assignment_corrections'
        verbose_name = 'Correction de devoir'
        verbose_name_plural = 'Corrections de devoirs'

    def __str__(self):
        return f"{self.submission} - {self.score}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.submission.status = 'GRADED'
        self.submission.save()


# ─────────────────────────────────────────────────────────────────────────────
# LOT 14 — Bibliothèque numérique
# ─────────────────────────────────────────────────────────────────────────────

class LibraryDocument(BaseModel):
    DOC_TYPE_CHOICES = [
        ('BOOK', 'Livre'),
        ('ARTICLE', 'Article'),
        ('JOURNAL', 'Revue'),
        ('THESIS', 'Thèse'),
        ('MEMOIR', 'Mémoire'),
        ('REPORT', 'Rapport'),
        ('ARCHIVE', 'Archive'),
        ('COURSE', 'Support de cours'),
        ('OTHER', 'Autre'),
    ]

    title = models.CharField(max_length=500)
    authors = models.CharField(max_length=500, blank=True)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, default='BOOK')
    year = models.PositiveIntegerField(null=True, blank=True)
    isbn = models.CharField(max_length=30, blank=True)
    doi = models.CharField(max_length=200, blank=True)
    abstract = models.TextField(blank=True)
    publisher = models.CharField(max_length=200, blank=True)
    language = models.CharField(max_length=10, default='fr')
    pages = models.PositiveIntegerField(null=True, blank=True)
    keywords = models.CharField(max_length=500, blank=True)

    cover_image = models.ImageField(upload_to='library/covers/', blank=True, null=True)
    file = models.FileField(upload_to='library/documents/', blank=True, null=True)
    external_url = models.URLField(blank=True)

    subjects = models.ManyToManyField(Subject, blank=True, related_name='library_documents')

    site = models.ForeignKey(
        'core.Site', on_delete=models.CASCADE, null=True, blank=True,
        related_name='library_documents',
        help_text="Site auquel ce document est rattaché. Laisser vide pour le rendre visible sur tous les sites."
    )

    is_downloadable = models.BooleanField(default=True)
    is_online_readable = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)

    download_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='elearning_uploaded_documents'
    )

    class Meta:
        db_table = 'library_documents'
        verbose_name = 'Document de bibliothèque'
        verbose_name_plural = 'Documents de bibliothèque'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class DocumentFavorite(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='doc_favorites')
    document = models.ForeignKey(LibraryDocument, on_delete=models.CASCADE, related_name='favorites')

    class Meta:
        db_table = 'library_document_favorites'
        verbose_name = 'Favori document'
        unique_together = ['student', 'document']

    def __str__(self):
        return f"{self.student.matricule} ♥ {self.document.title}"


class ReadingProgress(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='reading_progress')
    document = models.ForeignKey(LibraryDocument, on_delete=models.CASCADE, related_name='reading_progress')
    current_page = models.PositiveIntegerField(default=1)
    last_read_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'library_reading_progress'
        verbose_name = 'Progression de lecture'
        unique_together = ['student', 'document']

    def __str__(self):
        return f"{self.student.matricule} - {self.document.title} p.{self.current_page}"


# ─────────────────────────────────────────────────────────────────────────────
# LOT 12 — Examens sécurisés
# ─────────────────────────────────────────────────────────────────────────────

class SecureExam(BaseModel):
    EXAM_TYPE_CHOICES = [
        ('MID', 'Partiel'),
        ('FINAL', 'Examen final'),
        ('SUPP', 'Rattrapage'),
        ('TP', 'TP noté'),
        ('CONCOURS', 'Concours'),
    ]

    title = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True)

    class_obj = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True, related_name='secure_exams')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='secure_exams')
    quiz = models.OneToOneField(
        Quiz, on_delete=models.SET_NULL, null=True, blank=True, related_name='secure_exam'
    )

    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, default='FINAL')
    duration_minutes = models.PositiveIntegerField(default=60)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(default=1)

    # Paramètres de sécurité
    fullscreen_required = models.BooleanField(default=True)
    webcam_required = models.BooleanField(default=False)
    block_copy_paste = models.BooleanField(default=True)
    max_tab_switches = models.PositiveIntegerField(default=1)
    require_student_photo = models.BooleanField(default=False)
    ai_proctoring = models.BooleanField(default=False)

    is_published = models.BooleanField(default=False)
    pass_score_percent = models.PositiveSmallIntegerField(default=50)
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    subject_file = models.FileField(upload_to='exam_subjects/', blank=True, null=True)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    pdf_extra_duration = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'secure_exams'
        verbose_name = 'Examen sécurisé'
        verbose_name_plural = 'Examens sécurisés'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.class_obj.code} - {self.subject.code} - {self.title}"

    def is_available(self):
        from django.utils import timezone
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return self.is_published


class ExamSession(BaseModel):
    STATUS_CHOICES = [
        ('STARTED', 'En cours'),
        ('SUBMITTED', 'Soumis'),
        ('ABANDONED', 'Abandonné'),
        ('FLAGGED', 'Signalé'),
    ]

    exam = models.ForeignKey(SecureExam, on_delete=models.CASCADE, related_name='sessions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_sessions')
    quiz_attempt = models.OneToOneField(
        QuizAttempt, on_delete=models.SET_NULL, null=True, blank=True, related_name='exam_session'
    )

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='STARTED')
    time_remaining_seconds = models.PositiveIntegerField(null=True, blank=True)

    # Anti-triche counters
    tab_switch_count = models.PositiveIntegerField(default=0)
    fullscreen_exit_count = models.PositiveIntegerField(default=0)
    copy_attempt_count = models.PositiveIntegerField(default=0)
    focus_lost_count = models.PositiveIntegerField(default=0)
    # Number of times the client-side webcam proctoring has blocked the
    # student mid-exam over a sustained suspicious signal (object held up,
    # gaze away from screen, second person in frame...). The first block is a
    # timed 5-minute suspension the student resumes from; a second one is
    # treated as a repeat offense and ends the exam outright (see
    # SecureExamViewSet.log_event, which reads this back to tell the frontend
    # which of the two responses applies).
    fraud_block_count = models.PositiveIntegerField(default=0)

    is_flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True)
    events_log = models.JSONField(default=list)

    # Correction du prof
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    corrected_file = models.FileField(upload_to='exam_corrections/', blank=True, null=True)
    corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='graded_exam_sessions',
    )
    corrected_at = models.DateTimeField(null=True, blank=True)

    # Copie soumise par l'étudiant (travail scanné / réponses PDF)
    submission_file = models.FileField(upload_to='exam_submissions/', blank=True, null=True)
    submission_note = models.TextField(blank=True)

    class Meta:
        db_table = 'exam_sessions'
        verbose_name = 'Session d\'examen'
        verbose_name_plural = 'Sessions d\'examen'
        unique_together = ['exam', 'student']
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.matricule} - {self.exam.title}"

    def log_event(self, event_type, details=None):
        from django.utils import timezone
        self.events_log.append({
            'type': event_type,
            'at': timezone.now().isoformat(),
            'details': details or {},
        })
        if event_type == 'TAB_SWITCH':
            self.tab_switch_count += 1
        elif event_type == 'FULLSCREEN_EXIT':
            self.fullscreen_exit_count += 1
        elif event_type in ('COPY_ATTEMPT', 'PASTE_ATTEMPT'):
            self.copy_attempt_count += 1
        elif event_type == 'FOCUS_LOST':
            self.focus_lost_count += 1
        elif event_type == 'AI_FLAG':
            # Webcam-based anomaly (no face / phone visible / multiple faces).
            # Flag for teacher review but don't auto-close the session like the
            # tab-switch threshold does — a single vision-model reading can be
            # a false positive (bad lighting, glancing away), so a human should
            # make the final call here rather than ending the exam outright.
            self.is_flagged = True
            tag = f"Webcam: {details or 'Anomalie détectée'}"
            if not self.flag_reason:
                self.flag_reason = tag
            elif tag not in self.flag_reason:
                self.flag_reason = f"{self.flag_reason} · {tag}"
        elif event_type == 'WEBCAM_LOST':
            # Camera stopped working after the student already passed the
            # pre-flight check on the intro screen (unplugged, disabled,
            # crashed...). Flag for review rather than auto-close: could be a
            # genuine hardware hiccup, but the teacher should know monitoring
            # was interrupted before grading the attempt.
            self.is_flagged = True
            tag = f"Webcam: {details or 'Caméra perdue pendant l\'examen'}"
            if not self.flag_reason:
                self.flag_reason = tag
            elif tag not in self.flag_reason:
                self.flag_reason = f"{self.flag_reason} · {tag}"
        elif event_type == 'FRAUD_BLOCK':
            # Unlike a single AI_FLAG reading, this only fires client-side
            # after a suspicious signal is *sustained* across several
            # consecutive detection ticks (see ExamPage.jsx) — the frontend
            # has already suspended the student behind a blocking modal by
            # the time this is logged. First offense (count reaches 1) is a
            # timed suspension the student resumes from on their own; a
            # second one is a repeat offense the frontend ends the exam over
            # — this method just keeps the authoritative count so a page
            # refresh mid-block can't be used to reset it back to zero.
            self.fraud_block_count += 1
            self.is_flagged = True
            tag = f"Fraude webcam (blocage n°{self.fraud_block_count}): {details or 'Comportement suspect prolongé'}"
            if not self.flag_reason:
                self.flag_reason = tag
            elif tag not in self.flag_reason:
                self.flag_reason = f"{self.flag_reason} · {tag}"

        # Tab switches and fullscreen exits are both "left the secured exam
        # environment" events, and the frontend's client-side lock treats
        # them as contributing to the same limit — mirror that here so the
        # session actually gets flagged/closed server-side to match, instead
        # of only the fullscreen-exit counter silently incrementing forever.
        max_sw = self.exam.max_tab_switches
        if max_sw and (self.tab_switch_count > max_sw or self.fullscreen_exit_count > max_sw):
            self.is_flagged = True
            reasons = []
            if self.tab_switch_count > max_sw:
                reasons.append(f"changements d'onglet ({self.tab_switch_count}/{max_sw})")
            if self.fullscreen_exit_count > max_sw:
                reasons.append(f"sorties du plein écran ({self.fullscreen_exit_count}/{max_sw})")
            self.flag_reason = "Trop de " + " et de ".join(reasons)
            # Actually close the session — being flagged shouldn't leave it stuck
            # in STARTED, which would let the student keep answering or retake it.
            if self.status == 'STARTED':
                self.status = 'FLAGGED'
                self.submitted_at = self.submitted_at or timezone.now()
        self.save()

    def check_webcam_integrity(self):
        """Flag a submitted session when the webcam was mandatory but produced
        zero snapshots and no WEBCAM_LOST event was ever logged either — i.e.
        monitoring silently never ran (camera never actually started, uploads
        kept failing...) rather than a genuine, observed hardware drop. Without
        this, the admin correction screen only shows an informational note and
        the session looks indistinguishable from a normal, unflagged exam.
        """
        if not self.exam.webcam_required or self.snapshots.exists():
            return
        if any(e.get('type') == 'WEBCAM_LOST' for e in self.events_log):
            return
        tag = "Webcam: aucune capture reçue alors que la webcam était obligatoire"
        if self.flag_reason and tag in self.flag_reason:
            return
        self.is_flagged = True
        self.flag_reason = f"{self.flag_reason} · {tag}" if self.flag_reason else tag
        self.save(update_fields=['is_flagged', 'flag_reason'])

    def resolve_percent(self):
        """Best-effort 0-100 grade percent for this session, whichever
        source has actually been graded — a manually-entered `score` (the
        file-upload exam path, scaled against `exam.max_score`) or the
        linked `QuizAttempt`'s already-computed `percent` (the quiz-based
        exam path, which never writes back onto `ExamSession.score`).
        Returns None when nothing has been graded yet, so callers (e.g. a
        ranking) can exclude the session rather than showing a bogus 0%.
        """
        if self.score is not None:
            max_score = float(self.exam.max_score or 0)
            if max_score <= 0:
                return None
            return float(self.score) / max_score * 100
        attempt = self.quiz_attempt
        if attempt and attempt.is_graded:
            return float(attempt.percent)
        return None


# Fixed mention scale (independent of exam.pass_score_percent, which only
# gates the separate pass/fail badge) — ordered highest threshold first so
# the first match wins; anything below the lowest threshold is "Insuffisant".
MENTION_THRESHOLDS = [
    (90, 'Excellent'),
    (80, 'Très bien'),
    (70, 'Bien'),
    (60, 'Assez bien'),
    (50, 'Passable'),
]


def mention_for_percent(percent):
    for threshold, label in MENTION_THRESHOLDS:
        if percent >= threshold:
            return label
    return 'Insuffisant'


class ExamSnapshot(BaseModel):
    """Webcam snapshot taken during a secure exam session for proctoring."""
    session    = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='snapshots')
    image      = models.ImageField(upload_to='exam_snapshots/')
    taken_at   = models.DateTimeField(auto_now_add=True)
    face_detected    = models.BooleanField(null=True, blank=True)
    phone_detected   = models.BooleanField(default=False)
    ai_analysis      = models.TextField(blank=True)

    class Meta:
        db_table = 'exam_snapshots'
        verbose_name = 'Capture webcam'
        verbose_name_plural = 'Captures webcam'
        ordering = ['-taken_at']

    def __str__(self):
        return f"Snapshot {self.session.student.matricule} @ {self.taken_at}"


# ─────────────────────────────────────────────────────────────────────────────
# LOT 13 — Laboratoires virtuels
# ─────────────────────────────────────────────────────────────────────────────

class VirtualLab(BaseModel):
    LAB_TYPE_CHOICES = [
        ('INFO', 'Informatique'),
        ('PHYSICS', 'Physique'),
        ('CHEMISTRY', 'Chimie'),
        ('NETWORK', 'Réseaux'),
        ('CLOUD', 'Cloud'),
        ('ELECTRONICS', 'Électronique'),
        ('AI', 'Intelligence Artificielle'),
        ('PROGRAMMING', 'Programmation'),
        ('DOCKER', 'Docker'),
        ('LINUX', 'Linux'),
        ('VM', 'Machines virtuelles'),
        ('MATH', 'Mathématiques'),
        ('BIO', 'Biologie'),
        ('OTHER', 'Autre'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    objectives = models.TextField(blank=True)

    lab_type = models.CharField(max_length=20, choices=LAB_TYPE_CHOICES, default='INFO')

    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='virtual_labs')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='virtual_labs')
    lesson = models.ForeignKey(
        Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='virtual_labs'
    )

    access_url = models.URLField(blank=True)
    embed_url = models.URLField(blank=True)
    thumbnail = models.ImageField(upload_to='labs/thumbnails/', blank=True, null=True)

    duration_minutes = models.PositiveIntegerField(default=120)
    due_date = models.DateTimeField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(default=3)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=20)

    is_published = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'virtual_labs'
        verbose_name = 'Laboratoire virtuel'
        verbose_name_plural = 'Laboratoires virtuels'
        ordering = ['class_obj', 'subject', 'order']

    def __str__(self):
        return f"{self.class_obj.code} - {self.title}"


class LabSubmission(BaseModel):
    STATUS_CHOICES = [
        ('STARTED', 'En cours'),
        ('SUBMITTED', 'Soumis'),
        ('GRADED', 'Corrigé'),
    ]

    lab = models.ForeignKey(VirtualLab, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='lab_submissions')

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='STARTED')

    report_text = models.TextField(blank=True)
    report_file = models.FileField(upload_to='labs/reports/', blank=True, null=True)
    screenshot = models.ImageField(upload_to='labs/screenshots/', blank=True, null=True)

    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_labs'
    )
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lab_submissions'
        verbose_name = 'Soumission de labo'
        verbose_name_plural = 'Soumissions de labo'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.matricule} - {self.lab.title}"


# ─────────────────────────────────────────────────────────────────────────────
# LOTS 15/16/17 — IA pédagogique / IA Enseignant / Correction automatique
# ─────────────────────────────────────────────────────────────────────────────

class AIConversation(BaseModel):
    CONV_TYPE_CHOICES = [
        ('TUTOR', 'Tutorat étudiant'),
        ('TEACHER', 'Assistant enseignant'),
        ('CONTENT', 'Génération de contenu'),
        ('QUIZ_GEN', 'Génération de quiz'),
        ('GRADING', 'Correction automatique'),
        ('SUMMARY', 'Résumé de cours'),
        ('FLASHCARD', 'Génération de flashcards'),
        ('PLAN', 'Plan de révision'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_conversations'
    )
    conv_type = models.CharField(max_length=20, choices=CONV_TYPE_CHOICES, default='TUTOR')
    title = models.CharField(max_length=255, blank=True)

    subject = models.ForeignKey(
        Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_conversations'
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_conversations'
    )

    class Meta:
        db_table = 'ai_conversations'
        verbose_name = 'Conversation IA'
        verbose_name_plural = 'Conversations IA'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.email} - {self.get_conv_type_display()} - {self.title or self.id}"


class AIMessage(BaseModel):
    ROLE_CHOICES = [
        ('user', 'Utilisateur'),
        ('assistant', 'IA'),
    ]

    conversation = models.ForeignKey(
        AIConversation, on_delete=models.CASCADE, related_name='messages'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    tokens_used = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'ai_messages'
        verbose_name = 'Message IA'
        verbose_name_plural = 'Messages IA'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.conversation_id} [{self.role}] {self.content[:60]}"


# =============================================================================
# LOT 9 — VIDÉOTHÈQUE : streaming adaptatif, DRM, sous-titres, reprise auto
# =============================================================================

import secrets
from django.utils import timezone as tz


class VideoLibrary(BaseModel):
    SOURCE_CHOICES = [
        ('FILE',     'Fichier uploadé (MP4)'),
        ('HLS',      'Flux HLS adaptatif (m3u8)'),
        ('YOUTUBE',  'YouTube embed'),
        ('VIMEO',    'Vimeo embed'),
        ('EXTERNAL', 'Lien externe'),
    ]

    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    thumbnail   = models.ImageField(upload_to='videos/thumbnails/', blank=True, null=True)

    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='FILE')
    video_file  = models.FileField(upload_to='videos/files/', blank=True, null=True)
    source_url  = models.URLField(blank=True)

    duration_seconds = models.PositiveIntegerField(default=0)
    tags             = models.CharField(max_length=500, blank=True)

    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='videos')
    subject   = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='videos')
    lesson    = models.ForeignKey(
        'Lesson', on_delete=models.SET_NULL, null=True, blank=True, related_name='videos'
    )

    is_downloadable      = models.BooleanField(default=False)
    token_lifetime_hours = models.PositiveIntegerField(default=4)
    watermark_enabled    = models.BooleanField(default=True)
    watermark_template   = models.CharField(
        max_length=100, default='{student_name} — {matricule}'
    )
    disable_right_click  = models.BooleanField(default=True)

    is_published = models.BooleanField(default=False)
    order        = models.PositiveIntegerField(default=0)
    view_count   = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'video_library'
        verbose_name = 'Vidéo'
        verbose_name_plural = 'Vidéothèque'
        ordering = ['order', 'title']

    def __str__(self):
        return self.title

    def generate_download_token(self, student):
        token_obj, created = VideoDownloadToken.objects.get_or_create(
            student=student, video=self,
            defaults={
                'token': secrets.token_urlsafe(48),
                'expires_at': tz.now() + tz.timedelta(hours=self.token_lifetime_hours)
            }
        )
        if not created and token_obj.expires_at < tz.now():
            token_obj.token = secrets.token_urlsafe(48)
            token_obj.expires_at = tz.now() + tz.timedelta(hours=self.token_lifetime_hours)
            token_obj.is_used = False
            token_obj.save()
        return token_obj


class VideoSubtitle(BaseModel):
    video          = models.ForeignKey(VideoLibrary, on_delete=models.CASCADE, related_name='subtitles')
    language_code  = models.CharField(max_length=10, default='fr')
    language_label = models.CharField(max_length=50, default='Français')
    file           = models.FileField(upload_to='videos/subtitles/')

    class Meta:
        db_table = 'video_subtitles'
        verbose_name = 'Sous-titre'
        verbose_name_plural = 'Sous-titres'
        unique_together = ['video', 'language_code']

    def __str__(self):
        return f"{self.video.title} — {self.language_label}"


class VideoProgress(BaseModel):
    student               = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='video_progress')
    video                 = models.ForeignKey(VideoLibrary, on_delete=models.CASCADE, related_name='progress_records')
    position_seconds      = models.PositiveIntegerField(default=0)
    total_watched_seconds = models.PositiveIntegerField(default=0)
    last_watched_at       = models.DateTimeField(auto_now=True)
    is_completed          = models.BooleanField(default=False)

    class Meta:
        db_table = 'video_progress'
        verbose_name = 'Progression vidéo'
        verbose_name_plural = 'Progressions vidéo'
        unique_together = ['student', 'video']

    def __str__(self):
        return f"{self.student.matricule} -> {self.video.title} @ {self.position_seconds}s"


class VideoDownloadToken(BaseModel):
    student    = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='download_tokens')
    video      = models.ForeignKey(VideoLibrary, on_delete=models.CASCADE, related_name='download_tokens')
    token      = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()
    is_used    = models.BooleanField(default=False)

    class Meta:
        db_table = 'video_download_tokens'
        verbose_name = 'Token téléchargement'
        verbose_name_plural = 'Tokens téléchargement'

    def is_valid(self):
        return not self.is_used and self.expires_at > tz.now()


# =============================================================================
# LOT 8 — CLASSES VIRTUELLES MULTI-PROVIDER + OUTILS COLLABORATIFS
# =============================================================================

class VirtualClassroom(BaseModel):
    PROVIDER_CHOICES = [
        ('ZOOM',  'Zoom'),
        ('MEET',  'Google Meet'),
        ('TEAMS', 'Microsoft Teams'),
        ('JITSI', 'Jitsi Meet (intégré)'),
        ('BBB',   'BigBlueButton'),
        ('OTHER', 'Autre'),
    ]

    title    = models.CharField(max_length=255)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='JITSI')

    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='virtual_classrooms')
    subject   = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='virtual_classrooms')
    lesson    = models.ForeignKey(
        'Lesson', on_delete=models.SET_NULL, null=True, blank=True, related_name='virtual_classrooms'
    )

    start_time       = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)

    join_url        = models.URLField(blank=True)
    host_url        = models.URLField(blank=True)
    meeting_id      = models.CharField(max_length=200, blank=True)
    password        = models.CharField(max_length=100, blank=True)
    jitsi_room_name = models.CharField(max_length=200, blank=True)

    enable_recording  = models.BooleanField(default=False)
    recording_url     = models.URLField(blank=True)
    enable_whiteboard = models.BooleanField(default=True)
    enable_polls      = models.BooleanField(default=True)
    enable_chat       = models.BooleanField(default=True)
    enable_hand_raise = models.BooleanField(default=True)
    breakout_rooms    = models.PositiveIntegerField(default=0)

    transcript_text = models.TextField(blank=True)
    ai_summary      = models.TextField(blank=True)

    is_ended = models.BooleanField(default=False)
    ended_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='created_classrooms'
    )

    class Meta:
        db_table = 'virtual_classrooms'
        verbose_name = 'Classe virtuelle'
        verbose_name_plural = 'Classes virtuelles'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.title} ({self.get_provider_display()})"

    def get_jitsi_url(self):
        room = self.jitsi_room_name or f"campus-{self.id}"
        return f"https://meet.jit.si/{room}"


# ── Découpage automatique en segments (pour contournement limite 60 min) ──────

class MeetingSegment(BaseModel):
    """Un créneau/segment d'une classe virtuelle (max 60 min par segment)."""
    SEGMENT_STATUS = [
        ('PLANIFIEE',  'Planifiée'),
        ('EN_ATTENTE', 'En attente'),
        ('EN_COURS',   'En cours'),
        ('TERMINEE',   'Terminée'),
        ('ANNULEE',    'Annulée'),
    ]

    virtual_class  = models.ForeignKey(
        VirtualClassroom, on_delete=models.CASCADE, related_name='segments'
    )
    sequence       = models.PositiveIntegerField()          # 1, 2, 3 …
    meeting_url    = models.URLField(blank=True)
    meeting_id     = models.CharField(max_length=200, blank=True)
    start_time     = models.DateTimeField()
    end_time       = models.DateTimeField()
    status         = models.CharField(max_length=20, choices=SEGMENT_STATUS, default='PLANIFIEE')

    started_at     = models.DateTimeField(null=True, blank=True)
    ended_at       = models.DateTimeField(null=True, blank=True)
    notes          = models.TextField(blank=True)

    class Meta:
        db_table = 'meeting_segments'
        verbose_name = 'Segment de réunion'
        verbose_name_plural = 'Segments de réunion'
        ordering = ['sequence']
        unique_together = ['virtual_class', 'sequence']

    def __str__(self):
        return f"{self.virtual_class.title} — Segment {self.sequence} ({self.status})"

    @property
    def duration_minutes(self):
        return int((self.end_time - self.start_time).total_seconds() / 60)


class SessionParticipant(BaseModel):
    """Présence d'un étudiant sur un segment de réunion."""
    segment             = models.ForeignKey(MeetingSegment, on_delete=models.CASCADE, related_name='participants')
    student             = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='session_participations')
    joined_at           = models.DateTimeField(null=True, blank=True)
    left_at             = models.DateTimeField(null=True, blank=True)
    attendance_duration = models.PositiveIntegerField(default=0)  # secondes

    class Meta:
        db_table = 'session_participants'
        verbose_name = 'Participant'
        verbose_name_plural = 'Participants'
        unique_together = ['segment', 'student']

    def __str__(self):
        return f"{self.student.matricule} @ Segment {self.segment.sequence}"

    def calculate_duration(self):
        if self.joined_at and self.left_at:
            self.attendance_duration = int((self.left_at - self.joined_at).total_seconds())
            self.save(update_fields=['attendance_duration'])


class SessionLog(BaseModel):
    """Journal des événements liés aux classes virtuelles (audit)."""
    LOG_TYPES = [
        ('CREATED',       'Réunion créée'),
        ('STARTED',       'Réunion démarrée'),
        ('ENDED',         'Réunion terminée'),
        ('NOTIF_10MIN',   'Notification 10 min'),
        ('NOTIF_5MIN',    'Notification 5 min'),
        ('NOTIF_1MIN',    'Notification 1 min'),
        ('NOTIF_NEXT',    'Notification session suivante'),
        ('JOINED',        'Participant rejoint'),
        ('LEFT',          'Participant parti'),
        ('TRANSITION',    'Transition de session'),
        ('INCIDENT',      'Incident'),
    ]
    virtual_class = models.ForeignKey(
        VirtualClassroom, on_delete=models.CASCADE, related_name='logs'
    )
    segment       = models.ForeignKey(
        MeetingSegment, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs'
    )
    log_type      = models.CharField(max_length=20, choices=LOG_TYPES)
    actor         = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    detail        = models.TextField(blank=True)

    class Meta:
        db_table = 'session_logs'
        verbose_name = 'Journal de session'
        verbose_name_plural = 'Journaux de session'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.virtual_class.title} — {self.log_type}"


class ClassroomPoll(BaseModel):
    classroom    = models.ForeignKey(VirtualClassroom, on_delete=models.CASCADE, related_name='polls')
    question     = models.CharField(max_length=500)
    options      = models.JSONField(default=list)
    is_active    = models.BooleanField(default=True)
    show_results = models.BooleanField(default=False)

    class Meta:
        db_table = 'classroom_polls'
        verbose_name = 'Sondage'
        verbose_name_plural = 'Sondages'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.classroom.title} — {self.question[:60]}"

    def results(self):
        responses = self.responses.all()
        return {opt: responses.filter(selected_option=i).count() for i, opt in enumerate(self.options)}


class PollResponse(BaseModel):
    poll            = models.ForeignKey(ClassroomPoll, on_delete=models.CASCADE, related_name='responses')
    student         = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='poll_responses')
    selected_option = models.PositiveIntegerField()

    class Meta:
        db_table = 'poll_responses'
        verbose_name = 'Réponse sondage'
        verbose_name_plural = 'Réponses sondages'
        unique_together = ['poll', 'student']

    def __str__(self):
        return f"{self.student.matricule} -> {self.poll.question[:40]}"


class ClassroomChatMessage(BaseModel):
    classroom = models.ForeignKey(VirtualClassroom, on_delete=models.CASCADE, related_name='chat_messages')
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='classroom_messages')
    message   = models.TextField()
    is_pinned = models.BooleanField(default=False)

    class Meta:
        db_table = 'classroom_chat_messages'
        verbose_name = 'Message chat'
        verbose_name_plural = 'Messages chat'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.email}: {self.message[:60]}"


class HandRaise(BaseModel):
    classroom  = models.ForeignKey(VirtualClassroom, on_delete=models.CASCADE, related_name='hand_raises')
    student    = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='hand_raises')
    raised_at  = models.DateTimeField(auto_now_add=True)
    lowered_at = models.DateTimeField(null=True, blank=True)
    is_raised  = models.BooleanField(default=True)

    class Meta:
        db_table = 'hand_raises'
        verbose_name = 'Lever la main'
        verbose_name_plural = 'Levers de main'
        unique_together = ['classroom', 'student']

    def __str__(self):
        status = 'levée' if self.is_raised else 'baissée'
        return f"{self.student.matricule} ({status})"


# ── Cours autonomes (type MOOC / formation structurée) ──────────────────────

COURSE_LEVEL_CHOICES = [
    ('beginner',     'Débutant'),
    ('intermediate', 'Intermédiaire'),
    ('advanced',     'Avancé'),
    ('all_levels',   'Tous niveaux'),
]

COURSE_STATUS_CHOICES = [
    ('draft',     'Brouillon'),
    ('published', 'Publié'),
    ('archived',  'Archivé'),
]

COURSE_CONTENT_TYPE_CHOICES = [
    ('video',   'Vidéo'),
    ('audio',   'Audio'),
    ('pdf',     'PDF'),
    ('ppt',     'PowerPoint'),
    ('word',    'Word'),
    ('image',   'Image'),
    ('text',    'Texte'),
    ('youtube', 'YouTube'),
    ('vimeo',   'Vimeo'),
    ('iframe',  'Iframe'),
    ('html5',   'HTML5'),
]


class Course(BaseModel):
    """Cours autonome structuré (Sections → Chapitres → Leçons)."""
    site       = models.ForeignKey('core.Site', on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses_taught')
    quiz       = models.ForeignKey('Quiz', on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    title      = models.CharField(max_length=255)
    subtitle   = models.CharField(max_length=500, blank=True)
    description         = models.TextField(blank=True)
    thumbnail           = models.ImageField(upload_to='courses/thumbnails/', null=True, blank=True)
    level               = models.CharField(max_length=20, choices=COURSE_LEVEL_CHOICES, default='all_levels')
    language            = models.CharField(max_length=50, default='Français')
    status              = models.CharField(max_length=20, choices=COURSE_STATUS_CHOICES, default='draft')
    price               = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_free             = models.BooleanField(default=True)
    certificate_enabled = models.BooleanField(default=False)
    target_audience     = models.TextField(blank=True)
    requirements        = models.JSONField(default=list, blank=True)
    what_you_will_learn = models.JSONField(default=list, blank=True)
    video_url           = models.URLField(blank=True, help_text="URL vidéo de présentation (YouTube, Vimeo…)")
    total_students      = models.PositiveIntegerField(default=0)
    average_rating      = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    class Meta:
        db_table = 'courses'
        verbose_name = 'Cours'
        verbose_name_plural = 'Cours'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class CourseSection(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title  = models.CharField(max_length=255)
    order  = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'course_sections'
        verbose_name = 'Section de cours'
        verbose_name_plural = 'Sections de cours'
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} — {self.title}"


class CourseChapter(BaseModel):
    section     = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='chapters')
    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order       = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'course_chapters'
        verbose_name = 'Chapitre de cours'
        verbose_name_plural = 'Chapitres de cours'
        ordering = ['order']

    def __str__(self):
        return f"{self.section.title} — {self.title}"


class CourseLesson(BaseModel):
    chapter           = models.ForeignKey(CourseChapter, on_delete=models.CASCADE, related_name='lessons')
    title             = models.CharField(max_length=255)
    content_type      = models.CharField(max_length=20, choices=COURSE_CONTENT_TYPE_CHOICES, default='video')
    duration_seconds  = models.PositiveIntegerField(default=0)
    is_preview_free   = models.BooleanField(default=False)
    download_allowed  = models.BooleanField(default=False)
    text_content      = models.TextField(blank=True)
    external_embed_url = models.URLField(blank=True)
    video_file        = models.FileField(upload_to='courses/videos/', null=True, blank=True)
    document_file     = models.FileField(upload_to='courses/documents/', null=True, blank=True)
    order             = models.PositiveIntegerField(default=0)

    @property
    def has_media(self):
        return bool(self.video_file or self.document_file)

    class Meta:
        db_table = 'course_lessons'
        verbose_name = 'Leçon de cours'
        verbose_name_plural = 'Leçons de cours'
        ordering = ['order']

    def __str__(self):
        return f"{self.chapter.title} — {self.title}"


class CourseLessonProgress(BaseModel):
    """Tracks a student's completion of a CourseLesson (the self-paced
    Course/CourseChapter/CourseLesson builder) — separate from LessonProgress,
    which tracks the older Lesson/Chapter (parcours) model.
    """
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='course_lesson_progress'
    )
    lesson = models.ForeignKey(
        CourseLesson, on_delete=models.CASCADE, related_name='progress_records'
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'course_lesson_progress'
        verbose_name = 'Progression de leçon de cours'
        verbose_name_plural = 'Progressions de leçons de cours'
        unique_together = ['student', 'lesson']

    def __str__(self):
        return f"{self.student.matricule} - {self.lesson.title}"
