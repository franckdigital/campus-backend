"""
seed_elearning.py — Peuple tous les modules ELearning (Leçons, Quiz, Devoirs,
Examens sécurisés, Laboratoires virtuels, Bibliothèque, Vidéothèque, Classes
virtuelles, Réunions Zoom, IA Enseignant/Tutorat) sur les classes, matières et
étudiants déjà créés par `seed_full`.

Usage: python manage.py seed_elearning
Pré-requis : avoir déjà exécuté `python manage.py seed_full` (Sites, Programmes,
Classes, Matières, Enseignants, Étudiants doivent exister).
ATTENTION : efface les données ELearning existantes avant de reseeder — ne touche
à aucune autre donnée (étudiants, finances, notes, présences...).
"""
import random
from collections import defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

LIBRARY_DOCS = [
    ('Algorithmique et structures de données — Cours complet', 'BOOK',
     'Cours de référence sur les algorithmes et structures de données.'),
    ('Introduction à la programmation Python', 'COURSE',
     'Support de cours pour débutants en Python.'),
    ('Bases de données relationnelles — Théorie et pratique', 'BOOK',
     'Manuel sur la modélisation et les SGBD relationnels.'),
    ('Sécurité informatique — Bonnes pratiques', 'REPORT',
     'Rapport sur les bonnes pratiques de cybersécurité.'),
    ('Mémoire — Développement web full-stack', 'MEMOIR',
     'Mémoire de fin de cycle sur le développement web.'),
]

STATS_LABELS = {
    'lessons': 'Leçons', 'lesson_progress': 'Progressions de leçon',
    'quizzes': 'Quiz', 'questions': 'Questions', 'quiz_attempts': 'Tentatives de quiz',
    'assignments': 'Devoirs', 'submissions': 'Soumissions', 'corrections': 'Corrections',
    'labs': 'Laboratoires virtuels', 'lab_submissions': 'Soumissions de labo',
    'exams': 'Examens sécurisés',
    'videos': 'Vidéos', 'video_progress': 'Progressions vidéo',
    'classrooms': 'Classes virtuelles', 'zoom_meetings': 'Réunions Zoom',
    'ai_conversations': 'Conversations IA',
    'library_documents': 'Documents de bibliothèque',
}


class Command(BaseCommand):
    help = (
        'Seed demo data across all ELearning modules (lessons, quizzes, assignments, '
        'secure exams, virtual labs, library, videos, virtual classrooms, Zoom, AI tutor) '
        'on top of classes/students/teachers already created by seed_full.'
    )

    def handle(self, *args, **options):
        from apps.academic.models import Class as ClassModel
        from apps.students.models import Student

        if not ClassModel.objects.exists():
            raise CommandError(
                "Aucune classe trouvée. Exécutez d'abord `python manage.py seed_full` "
                "pour créer les sites, programmes, classes, matières et étudiants."
            )

        self.stdout.write('\n=== NETTOYAGE ELEARNING ===')
        self._clean()

        stats = defaultdict(int)

        self.stdout.write('\n=== SEED PAR CLASSE ===')
        classes = ClassModel.objects.select_related('site').prefetch_related(
            'subject_teachers__subject', 'subject_teachers__teacher__user'
        )
        for cls in classes:
            cst = list(cls.subject_teachers.select_related('subject', 'teacher__user').all())
            if not cst:
                continue
            students = list(Student.objects.filter(enrollments__class_obj=cls).distinct())
            if not students:
                continue
            self.stdout.write(f'\n--- {cls.code} ({cls.site.name}) — {len(cst)} matières, {len(students)} étudiants ---')
            self._seed_class(cls, cst, students, stats)

        self.stdout.write('\n=== BIBLIOTHEQUE NUMERIQUE ===')
        self._seed_library(stats)

        self._summary(stats)

    # =========================================================================
    # NETTOYAGE
    # =========================================================================

    def _clean(self):
        from apps.elearning.models import (
            HandRaise, ClassroomChatMessage, PollResponse, ClassroomPoll, VirtualClassroom,
            VideoDownloadToken, VideoProgress, VideoSubtitle, VideoLibrary,
            AIMessage, AIConversation,
            LabSubmission, VirtualLab,
            ExamSnapshot, ExamSession, SecureExam,
            ReadingProgress, DocumentFavorite, LibraryDocument,
            AssignmentCorrection, AssignmentSubmission, Assignment,
            AttemptAnswer, QuizAttempt, Choice, Question, Quiz,
            LessonProgress, LessonAttachment, Lesson, Chapter,
            ZoomMeeting,
        )
        order = [
            HandRaise, ClassroomChatMessage, PollResponse, ClassroomPoll, VirtualClassroom,
            VideoDownloadToken, VideoProgress, VideoSubtitle, VideoLibrary,
            AIMessage, AIConversation,
            LabSubmission, VirtualLab,
            ExamSnapshot, ExamSession, SecureExam,
            ReadingProgress, DocumentFavorite, LibraryDocument,
            AssignmentCorrection, AssignmentSubmission, Assignment,
            AttemptAnswer, QuizAttempt, Choice, Question, Quiz,
            LessonProgress, LessonAttachment, Lesson, Chapter,
            ZoomMeeting,
        ]
        for model in order:
            n = model.objects.count()
            model.objects.all().delete()
            if n:
                self.stdout.write(f'  Supprimé {n:>4}  {model.__name__}')

    # =========================================================================
    # SEED PAR CLASSE
    # =========================================================================

    def _seed_class(self, cls, cst, students, stats):
        from apps.elearning.models import (
            Chapter, Lesson, LessonProgress, Quiz, Question, Choice, QuizAttempt, AttemptAnswer,
            Assignment, AssignmentSubmission, AssignmentCorrection, SecureExam,
            VirtualLab, LabSubmission, VideoLibrary, VideoProgress, VirtualClassroom, ZoomMeeting,
            AIConversation, AIMessage,
        )
        from apps.academic.models import Session as AcaSession

        now = timezone.now()
        sessions = list(
            AcaSession.objects.filter(class_obj=cls).select_related('subject', 'teacher__user')
        )

        for idx, link in enumerate(cst):
            subject = link.subject
            teacher = link.teacher

            chapter = Chapter.objects.create(
                title=f'Chapitre 1 — {subject.name}',
                description=f'Introduction à {subject.name}.',
                class_obj=cls, subject=subject, order=1, is_published=True,
            )

            lessons = []
            for li, (ltitle, lcontent) in enumerate([
                (f'Introduction à {subject.name}', f'Présentation générale du cours de {subject.name}.'),
                (f'Notions fondamentales — {subject.name}', f'Approfondissement des bases de {subject.name}.'),
            ], start=1):
                lesson = Lesson.objects.create(
                    title=ltitle, description=lcontent[:120], content=lcontent,
                    class_obj=cls, subject=subject, teacher=teacher, chapter=chapter,
                    order=li, is_published=True, published_at=now, min_watch_percent=80,
                )
                lessons.append(lesson)
                stats['lessons'] += 1

            for si, student in enumerate(students):
                watch = [100, 80, 45, 0][si % 4]
                lp = LessonProgress.objects.create(
                    student=student, lesson=lessons[0],
                    started_at=now - timedelta(days=7),
                    watch_percent=watch, time_spent_seconds=watch * 6,
                )
                lp.evaluate_completion()
                stats['lesson_progress'] += 1

            quiz = Quiz.objects.create(
                title=f'Quiz — {subject.name}',
                description=f'Évaluez vos connaissances en {subject.name}.',
                class_obj=cls, subject=subject, lesson=lessons[0],
                time_limit_minutes=20, max_attempts=2, pass_score_percent=50, is_published=True,
            )
            q1 = Question.objects.create(
                quiz=quiz, question_type='QCU', text=f"Qu'est-ce que {subject.name} ?", order=1, points=2,
            )
            Choice.objects.create(question=q1, text='Une discipline académique', is_correct=True, order=1)
            Choice.objects.create(question=q1, text='Un loisir', is_correct=False, order=2)
            q2 = Question.objects.create(
                quiz=quiz, question_type='QCM',
                text=f'Quels sont des prérequis utiles pour {subject.name} ?', order=2, points=2,
            )
            Choice.objects.create(question=q2, text='Assiduité', is_correct=True, order=1)
            Choice.objects.create(question=q2, text='Lecture régulière', is_correct=True, order=2)
            Choice.objects.create(question=q2, text='Aucun travail', is_correct=False, order=3)
            stats['quizzes'] += 1
            stats['questions'] += 2

            for si, student in enumerate(students[:3]):
                attempt = QuizAttempt.objects.create(quiz=quiz, student=student)
                for q in quiz.questions.all():
                    ans = AttemptAnswer.objects.create(attempt=attempt, question=q)
                    correct = q.choices.filter(is_correct=True)
                    if si != 2:
                        ans.selected_choices.set(correct)
                    else:
                        ans.selected_choices.set(q.choices.filter(is_correct=False)[:1])
                    ans.grade()
                attempt.finalize()
                stats['quiz_attempts'] += 1

            assignment = Assignment.objects.create(
                title=f'Devoir — {subject.name}',
                description=f'Devoir maison portant sur {subject.name}.',
                instructions='Rédiger une synthèse de 2 pages et la soumettre avant la date limite.',
                class_obj=cls, subject=subject, teacher=teacher, lesson=lessons[0],
                due_date=now + timedelta(days=10), status='PUBLISHED', published_at=now,
            )
            stats['assignments'] += 1
            for si, student in enumerate(students):
                if si % 3 == 2:
                    continue
                sub = AssignmentSubmission.objects.create(
                    assignment=assignment, student=student,
                    content=f'Synthèse rédigée par {student.user.first_name} {student.user.last_name}.',
                )
                stats['submissions'] += 1
                if si % 2 == 0:
                    AssignmentCorrection.objects.create(
                        submission=sub, score=14 + (si % 5),
                        feedback='Bon travail, continuez ainsi.', corrected_by=teacher.user,
                    )
                    stats['corrections'] += 1

            if idx == 0:
                lab = VirtualLab.objects.create(
                    title=f'TP — {subject.name}', description=f'Travaux pratiques de {subject.name}.',
                    instructions='Suivre le protocole détaillé et soumettre votre rapport.',
                    objectives=f'Mettre en pratique les notions de {subject.name}.',
                    lab_type='INFO', class_obj=cls, subject=subject, lesson=lessons[0],
                    duration_minutes=120, due_date=now + timedelta(days=14), is_published=True,
                )
                stats['labs'] += 1
                for student in students[:3]:
                    LabSubmission.objects.create(
                        lab=lab, student=student, status='SUBMITTED',
                        report_text='Compte-rendu du TP réalisé.', submitted_at=now,
                    )
                    stats['lab_submissions'] += 1

                exam_quiz = Quiz.objects.create(
                    title=f'Examen final — {subject.name}', class_obj=cls, subject=subject,
                    time_limit_minutes=60, max_attempts=1, pass_score_percent=50, is_published=True,
                )
                eq1 = Question.objects.create(
                    quiz=exam_quiz, question_type='QCU',
                    text=f"Question d'examen sur {subject.name}", order=1, points=10,
                )
                Choice.objects.create(question=eq1, text='Réponse correcte', is_correct=True, order=1)
                Choice.objects.create(question=eq1, text='Réponse incorrecte', is_correct=False, order=2)
                SecureExam.objects.create(
                    title=f'Examen final — {subject.name}',
                    description='Examen surveillé de fin de semestre.',
                    class_obj=cls, subject=subject, quiz=exam_quiz,
                    exam_type='FINAL', duration_minutes=60,
                    start_date=now + timedelta(days=20), end_date=now + timedelta(days=20, hours=3),
                    is_published=True,
                )
                stats['exams'] += 1

            video = VideoLibrary.objects.create(
                title=f'Vidéo cours — {subject.name}',
                description=f'Capture vidéo du cours de {subject.name}.',
                source_type='YOUTUBE', source_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                duration_seconds=1800, class_obj=cls, subject=subject, lesson=lessons[0],
                is_published=True,
            )
            stats['videos'] += 1
            for si, student in enumerate(students[:2]):
                VideoProgress.objects.create(
                    student=student, video=video,
                    position_seconds=600 * (si + 1), total_watched_seconds=600 * (si + 1),
                )
                stats['video_progress'] += 1

            VirtualClassroom.objects.create(
                title=f'Séance en ligne — {subject.name}', provider='JITSI',
                class_obj=cls, subject=subject, lesson=lessons[0],
                start_time=now + timedelta(days=2, hours=9), duration_minutes=90,
                jitsi_room_name=f'campus-{cls.code}-{subject.code}', created_by=teacher.user,
            )
            stats['classrooms'] += 1

        teacher_user_default = cst[0].teacher.user
        for sess in sessions[:2]:
            ZoomMeeting.objects.create(
                session=sess,
                meeting_id=f'{random.randint(100, 999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)}',
                topic=f'{sess.subject.name} — {cls.code}',
                start_time=now + timedelta(days=3, hours=9), duration=90,
                join_url='https://zoom.us/j/0000000000',
                host=teacher_user_default, created_by=teacher_user_default,
            )
            stats['zoom_meetings'] += 1

        teacher_for_ai = cst[0].teacher
        conv_t = AIConversation.objects.create(
            user=teacher_for_ai.user, conv_type='TEACHER',
            title=f'Assistant pédagogique — {cls.code}',
        )
        AIMessage.objects.create(
            conversation=conv_t, role='user',
            content=f'Aide-moi à préparer un plan de cours pour {cls.code}.',
        )
        AIMessage.objects.create(
            conversation=conv_t, role='assistant',
            content='Voici une proposition de plan de cours structuré en 4 chapitres...',
        )
        stats['ai_conversations'] += 1

        for student in students[:2]:
            conv_s = AIConversation.objects.create(
                user=student.user, conv_type='TUTOR', title=f'Tutorat IA — {cls.code}',
            )
            AIMessage.objects.create(
                conversation=conv_s, role='user',
                content="Peux-tu m'expliquer ce chapitre plus simplement ?",
            )
            AIMessage.objects.create(
                conversation=conv_s, role='assistant',
                content='Bien sûr ! Reprenons étape par étape...',
            )
            stats['ai_conversations'] += 1

        self.stdout.write(f'  OK {cls.code}: leçons, quiz, devoirs, examen, labo, vidéos, classe virtuelle, IA')

    # =========================================================================
    # BIBLIOTHEQUE NUMERIQUE
    # =========================================================================

    def _seed_library(self, stats):
        from apps.elearning.models import LibraryDocument
        from apps.core.models import Site
        from apps.academic.models import Subject
        from apps.accounts.models import User

        uploader = User.objects.filter(is_superuser=True).first()
        subjects = list(Subject.objects.all()[:10])

        for site in Site.objects.all():
            for title, dtype, abstract in LIBRARY_DOCS[:3]:
                doc = LibraryDocument.objects.create(
                    title=f'{title} — {site.code}', authors='Équipe pédagogique', doc_type=dtype,
                    year=2024, abstract=abstract, publisher='Campus Editions', language='fr',
                    site=site, is_downloadable=True, is_online_readable=True, is_published=True,
                    uploaded_by=uploader,
                )
                if subjects:
                    doc.subjects.set(random.sample(subjects, min(2, len(subjects))))
                stats['library_documents'] += 1

        for title, dtype, abstract in LIBRARY_DOCS[3:]:
            doc = LibraryDocument.objects.create(
                title=title, authors='Équipe pédagogique', doc_type=dtype,
                year=2024, abstract=abstract, publisher='Campus Editions', language='fr',
                site=None, is_downloadable=True, is_online_readable=True, is_published=True,
                uploaded_by=uploader,
            )
            stats['library_documents'] += 1

    # =========================================================================
    # RESUME
    # =========================================================================

    def _summary(self, stats):
        sep = '=' * 70
        self.stdout.write('\n' + sep)
        self.stdout.write('SEED ELEARNING TERMINE')
        self.stdout.write(sep)
        for key, label in STATS_LABELS.items():
            self.stdout.write(f'  {label:<28}: {stats.get(key, 0)}')
        self.stdout.write(sep + '\n')
