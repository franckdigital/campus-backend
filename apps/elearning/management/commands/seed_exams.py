"""
seed_exams.py — Seed examens sécurisés dans tous les formats et scénarios.

Usage: python manage.py seed_exams
Couvre:
  - Partiel (MID) — en ligne via quiz
  - Examen final (FINAL) — sujet PDF + upload copie
  - Rattrapage (SUPP) — via classe virtuelle
  - TP noté (TP) — formulaire en ligne
  - Examen à venir / en cours / terminé
  - Sessions étudiants : complétées / en cours / abandonnées
  - Anti-triche : plein écran, webcam, blocage copier-coller
"""
import random
from django.core.management.base import BaseCommand
from django.utils import timezone

EXAM_DATA = [
    {
        'title': 'Partiel S1 — Algorithmique',
        'exam_type': 'MID',
        'duration': 60,
        'pass_score': 50,
        'offset_hours': -48,    # terminé
        'available': False,
        'fullscreen': True,
        'webcam': False,
        'block_copy': True,
        'use_quiz': True,
    },
    {
        'title': 'Examen Final — Base de données',
        'exam_type': 'FINAL',
        'duration': 120,
        'pass_score': 60,
        'offset_hours': 24,     # à venir
        'available': False,
        'fullscreen': True,
        'webcam': True,
        'block_copy': True,
        'use_quiz': True,
    },
    {
        'title': 'Partiel — Réseaux et Protocoles',
        'exam_type': 'MID',
        'duration': 90,
        'pass_score': 50,
        'offset_hours': -2,     # vient de terminer
        'available': False,
        'fullscreen': True,
        'webcam': False,
        'block_copy': False,
        'use_quiz': True,
    },
    {
        'title': 'TP noté — Implémentation en Python',
        'exam_type': 'TP',
        'duration': 180,
        'pass_score': 40,
        'offset_hours': 0,      # maintenant
        'available': True,
        'fullscreen': False,
        'webcam': False,
        'block_copy': True,
        'use_quiz': True,
    },
    {
        'title': 'Examen Final — Intelligence Artificielle',
        'exam_type': 'FINAL',
        'duration': 120,
        'pass_score': 60,
        'offset_hours': 72,
        'available': False,
        'fullscreen': True,
        'webcam': True,
        'block_copy': True,
        'use_quiz': False,      # PDF upload
    },
    {
        'title': 'Rattrapage — Algorithmique S1',
        'exam_type': 'SUPP',
        'duration': 90,
        'pass_score': 40,
        'offset_hours': 120,
        'available': False,
        'fullscreen': True,
        'webcam': True,
        'block_copy': True,
        'use_quiz': True,
    },
    {
        'title': 'Concours d\'entrée — Génie Logiciel',
        'exam_type': 'CONCOURS',
        'duration': 240,
        'pass_score': 70,
        'offset_hours': 168,
        'available': False,
        'fullscreen': True,
        'webcam': True,
        'block_copy': True,
        'use_quiz': True,
    },
]

EXAM_QUESTIONS = [
    ('MCQ', 'Quelle est la complexité de la recherche dans un arbre binaire équilibré ?', ['O(log n)', 'O(n)', 'O(1)', 'O(n²)'], [0]),
    ('MCQ', 'Quel patron de conception sépare la construction d\'un objet de sa représentation ?', ['Builder', 'Singleton', 'Factory', 'Observer'], [0]),
    ('TRUEFALSE', 'TCP/IP est un protocole sans connexion.', None, False),
    ('MCQ', 'Quelle structure de données permet d\'implémenter un algorithme BFS ?', ['File (Queue)', 'Pile (Stack)', 'Arbre', 'Tableau'], [0]),
    ('MULTI', 'Lesquels sont des principes SOLID ?', ['Single Responsibility', 'Open/Closed', 'Liskov', 'Global State'], [0, 1, 2]),
    ('TEXT', 'Expliquez le concept de normalisation en base de données.', None, None),
    ('NUMERIC', 'Combien de tables résultent d\'une relation Many-to-Many entre 2 entités ?', None, 3),
    ('MCQ', 'Quel algorithme ML est le plus adapté pour la détection d\'anomalies ?', ['Isolation Forest', 'Linear Regression', 'KNN', 'Naive Bayes'], [0]),
    ('TRUEFALSE', 'Les index SQL accélèrent toujours les requêtes SELECT.', None, False),
    ('MCQ', 'Quel protocole utilise le port 443 ?', ['HTTPS', 'HTTP', 'FTP', 'SSH'], [0]),
]


class Command(BaseCommand):
    help = 'Seed examens sécurisés de tous types avec sessions étudiants'

    def handle(self, *args, **options):
        from apps.elearning.models import (
            SecureExam, ExamSession,
            Quiz, Question, Choice,
        )
        from apps.students.models import Student
        from apps.academic.models import Class as ClassModel

        self.stdout.write(self.style.MIGRATE_HEADING('=== Seed Examens ==='))

        classes = list(ClassModel.objects.filter(is_active=True)[:3])
        if not classes:
            self.stdout.write(self.style.ERROR('Aucune classe trouvée.'))
            return

        all_students = list(Student.objects.select_related('user').all()[:20])
        created_exams = []

        for i, edata in enumerate(EXAM_DATA):
            cls = classes[i % len(classes)]
            subjects = list(cls.subjects.all())
            subject = subjects[i % len(subjects)] if subjects else None

            start = timezone.now() + timezone.timedelta(hours=edata['offset_hours'])

            # Créer le quiz associé si nécessaire
            quiz = None
            if edata['use_quiz']:
                quiz = Quiz.objects.create(
                    title=f"Quiz — {edata['title']}",
                    class_obj=cls,
                    subject=subject,
                    duration_minutes=edata['duration'],
                    passing_score=edata['pass_score'],
                    total_points=100,
                    is_published=True,
                    is_active=True,
                )
                for j, (qtype, text, choices, correct) in enumerate(EXAM_QUESTIONS[:8]):
                    if qtype == 'TRUEFALSE':
                        Question.objects.create(
                            quiz=quiz, order=j+1,
                            question_type='TRUEFALSE', text=text, points=12,
                            true_false_answer=correct,
                        )
                    elif qtype == 'TEXT':
                        Question.objects.create(
                            quiz=quiz, order=j+1,
                            question_type='TEXT', text=text, points=16,
                        )
                    elif qtype == 'NUMERIC':
                        Question.objects.create(
                            quiz=quiz, order=j+1,
                            question_type='NUMERIC', text=text, points=12,
                            numeric_answer=correct, numeric_tolerance=0,
                        )
                    else:
                        q = Question.objects.create(
                            quiz=quiz, order=j+1,
                            question_type='MCQ', text=text, points=12,
                            allow_multiple=(qtype == 'MULTI'),
                        )
                        for k, c in enumerate(choices or []):
                            Choice.objects.create(
                                question=q, text=c, order=k,
                                is_correct=(k in (correct or [])),
                            )

            exam = SecureExam.objects.create(
                title=edata['title'],
                exam_type=edata['exam_type'],
                class_obj=cls,
                subject=subject,
                quiz=quiz,
                duration_minutes=edata['duration'],
                pass_score_percent=edata['pass_score'],
                start_date=start,
                end_date=start + timezone.timedelta(minutes=edata['duration']),
                fullscreen_required=edata['fullscreen'],
                webcam_required=edata['webcam'],
                block_copy_paste=edata['block_copy'],
                max_tab_switches=5,
                is_published=True,
                is_active=True,
            )
            created_exams.append((exam, edata))
            self.stdout.write(f'  ✓ Examen : {exam.title} ({exam.exam_type})')

        # Sessions étudiants
        self.stdout.write('\nSimulation des sessions étudiants...')
        for exam, edata in created_exams:
            if edata['offset_hours'] >= 24:
                continue  # pas encore passé

            students_sample = random.sample(all_students, min(12, len(all_students)))
            for student in students_sample:
                score = random.randint(0, 100) if random.random() > 0.1 else None
                status = 'SUBMITTED' if score is not None else 'IN_PROGRESS'
                ExamSession.objects.create(
                    exam=exam,
                    student=student,
                    status=status,
                    score=score,
                    started_at=timezone.now() - timezone.timedelta(hours=abs(edata['offset_hours']) + 1),
                    submitted_at=timezone.now() - timezone.timedelta(hours=abs(edata['offset_hours'])) if status == 'SUBMITTED' else None,
                    tab_switches=random.randint(0, 3),
                )

        self.stdout.write(self.style.SUCCESS(f'\n✅ {len(created_exams)} examens créés avec sessions.'))
