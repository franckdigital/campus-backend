"""
fix_orphaned_exam_quiz_attempts.py
────────────────────────────────────
Before this fix, ExamSession.start_session always created a brand-new
QuizAttempt whenever a session was first created for a quiz-based exam —
even though the student's actual answers were submitted against a
*different* QuizAttempt created earlier by the quiz's own start-attempt
endpoint (called first in the frontend's startExam() flow). The session
ended up linked to an empty, never-submitted "decoy" attempt, so the
admin correction screen (which reads session.quiz_attempt) showed 0 for
every question despite the student having actually submitted answers.

This command repairs existing sessions: for every ExamSession whose linked
quiz_attempt has no submitted answers, it looks for another QuizAttempt on
the same quiz+student that was actually submitted, and repoints the
session to it.

Usage :
    python manage.py fix_orphaned_exam_quiz_attempts --dry-run
    python manage.py fix_orphaned_exam_quiz_attempts
"""

from django.core.management.base import BaseCommand

from apps.elearning.models import ExamSession


class Command(BaseCommand):
    help = "Repointe les ExamSession vers le bon QuizAttempt soumis par l'étudiant."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Affiche les sessions concernées sans les modifier.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        sessions = ExamSession.objects.filter(quiz_attempt__isnull=False).select_related('quiz_attempt', 'exam', 'student')
        fixed = 0

        for session in sessions:
            current = session.quiz_attempt
            if current.submitted_at is not None or current.answers.exists():
                continue  # already the real, answered attempt

            quiz = session.exam.quiz
            if not quiz:
                continue

            real_attempt = quiz.attempts.filter(student=session.student).exclude(id=current.id).filter(
                submitted_at__isnull=False
            ).order_by('-submitted_at').first()
            if not real_attempt:
                continue  # nothing to repoint to — student never actually submitted

            fixed += 1
            self.stdout.write(
                f"  - {session.student.matricule} · {session.exam.title}: "
                f"attempt {current.id} (vide) -> attempt {real_attempt.id} (soumis, {real_attempt.score}/{real_attempt.max_score})"
            )
            if not dry_run:
                session.quiz_attempt = real_attempt
                session.save(update_fields=['quiz_attempt'])

        if fixed == 0:
            self.stdout.write(self.style.SUCCESS('Aucune session à corriger.'))
        elif dry_run:
            self.stdout.write(self.style.WARNING(f'{fixed} session(s) à corriger (dry-run, rien appliqué).'))
        else:
            self.stdout.write(self.style.SUCCESS(f'{fixed} session(s) corrigée(s).'))
