"""
fix_stuck_exam_sessions.py
───────────────────────────
Avant ce correctif, ExamSessionSubmitFileView (upload de copie PDF) et
ExamSessionGradeView (correction prof) ne faisaient jamais passer
ExamSession.status à 'SUBMITTED'. Résultat : toute copie remise en upload
(par opposition à un quiz en ligne) reste bloquée en 'STARTED' pour toujours,
et n'apparaît donc jamais dans l'onglet "Complétés" côté étudiant.

Le même problème existait pour les examens QCM (liés à un Quiz) avant que
QuizAttemptViewSet.submit ne soit corrigé (2026-07-04, apps/elearning/views.py
_sync_exam_session) : toute session créée avant ce correctif, ou dont la
QuizAttempt a été finalisée par un autre chemin, peut rester bloquée en
STARTED alors que la tentative de quiz liée est bel et bien terminée/notée —
ce qui laisse le bouton "Commencer l'examen" actif côté étudiant alors que
le classement affiche déjà son résultat.

Cette commande corrige les sessions déjà bloquées : toute session qui a
une copie (submission_file), qui a déjà été corrigée (corrected_at), ou dont
la QuizAttempt liée est déjà soumise/notée, mais qui est encore au statut
STARTED, est passée à SUBMITTED.

Usage :
    python manage.py fix_stuck_exam_sessions --dry-run   # affiche sans corriger
    python manage.py fix_stuck_exam_sessions             # corrige
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.elearning.models import ExamSession


class Command(BaseCommand):
    help = "Corrige les ExamSession bloquées en STARTED alors qu'une copie/tentative a été soumise ou corrigée."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Affiche les sessions concernées sans les modifier.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        stuck = ExamSession.objects.filter(status='STARTED').filter(
            Q(submission_file__isnull=False, submission_file__gt='')
            | Q(corrected_at__isnull=False)
            | Q(quiz_attempt__submitted_at__isnull=False)
        ).select_related('quiz_attempt')

        count = stuck.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('Aucune session bloquée trouvée.'))
            return

        self.stdout.write(f"{count} session(s) bloquée(s) en STARTED trouvée(s).")
        for session in stuck:
            self.stdout.write(f"  - {session.student.matricule} · {session.exam.title} (session {session.id})")
            if not dry_run:
                session.status = 'SUBMITTED'
                session.submitted_at = (
                    session.submitted_at
                    or session.corrected_at
                    or (session.quiz_attempt.submitted_at if session.quiz_attempt else None)
                    or timezone.now()
                )
                session.save(update_fields=['status', 'submitted_at'])

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run : aucune modification appliquée.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'{count} session(s) corrigée(s).'))
