"""
Exercise the real alert-sending functions (apps.notifications.services) for
one student and their linked parent(s), using REAL existing data (a real
payment, attendance record, graded submission...) rather than fabricating
fake rows — safe to run against a live database, it only ever creates
Notification records (the intended side effect of testing alerts), never
mutates Payment/Invoice/AttendanceRecord/etc.

Covers every alert type that actually reaches a student and/or their
parent(s): paiement validé (les deux), devoir corrigé (les deux), absence
constatée (parent), retard constaté (parent), rappel d'échéancier de
scolarité (les deux, via apps.finance.tasks._maybe_remind_student).

Any check that finds no suitable existing data for this student is skipped
with a clear message instead of guessing/fabricating one.

Usage:
    python manage.py test_student_parent_alerts --email ibrahim.coulibaly@escam-test.ci
    python manage.py test_student_parent_alerts --matricule ESCAM-CO20260002
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Trigger every real student+parent alert type for one student, using their existing real data."

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Email of the student user')
        parser.add_argument('--matricule', help='Matricule of the student (alternative to --email)')

    def handle(self, *args, **options):
        from apps.students.models import Student, StudentParent
        from apps.finance.models import Payment
        from apps.attendance.models import AttendanceRecord
        from apps.elearning.models import AssignmentCorrection
        from apps.notifications.models import Notification
        from apps.notifications.services import (
            notify_payment_validated, notify_absence_recorded,
            notify_late_recorded, notify_assignment_graded,
        )
        from apps.finance.tasks import _maybe_remind_student

        if not options['email'] and not options['matricule']:
            raise CommandError('Pass --email or --matricule to identify the student.')

        try:
            if options['email']:
                student = Student.objects.select_related('user').get(user__email=options['email'])
            else:
                student = Student.objects.select_related('user').get(matricule=options['matricule'])
        except Student.DoesNotExist:
            raise CommandError('No matching student found.')

        parents = list(StudentParent.objects.filter(student=student).select_related('parent__user'))
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== test_student_parent_alerts — {student.user.full_name} ({student.user.email}) — #{student.matricule} ===\n"
        ))
        if not parents:
            self.stdout.write(self.style.WARNING('  ATTENTION : aucun parent lié à cet étudiant — les alertes "parent" ne pourront pas être vérifiées.'))
        else:
            for sp in parents:
                self.stdout.write(f"  Parent lié : {sp.parent.user.full_name} ({sp.parent.user.email}) — receives_notifications={sp.receives_notifications}")

        recipients = [student.user] + [sp.parent.user for sp in parents]
        before_ids = set(Notification.objects.filter(recipient__in=recipients).values_list('id', flat=True))

        # ── 1. Paiement validé (étudiant + parent) ──────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[1] Paiement validé (étudiant + parent)'))
        payment = Payment.objects.filter(
            invoice__student=student, status='SUCCESS'
        ).order_by('-payment_date').first()
        if payment:
            notify_payment_validated(payment)
            self.stdout.write(f"  Déclenché sur paiement {payment.payment_number} ({payment.amount} FCFA)")
        else:
            self.stdout.write(self.style.WARNING('  Ignoré — aucun paiement SUCCESS trouvé pour cet étudiant.'))

        # ── 2. Devoir corrigé (étudiant + parent) ───────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[2] Devoir corrigé (étudiant + parent)'))
        correction = AssignmentCorrection.objects.filter(
            submission__student=student
        ).order_by('-created_at').first()
        if correction:
            notify_assignment_graded(correction)
            self.stdout.write(f"  Déclenché sur la correction de \"{correction.submission.assignment.title}\"")
        else:
            self.stdout.write(self.style.WARNING('  Ignoré — aucun devoir corrigé trouvé pour cet étudiant.'))

        # ── 3. Absence constatée (parent) ───────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[3] Absence constatée (parent)'))
        absence = AttendanceRecord.objects.filter(
            student=student, status='ABSENT'
        ).order_by('-created_at').first()
        if absence:
            notify_absence_recorded(absence)
            self.stdout.write(f"  Déclenché sur l'absence du {absence.attendance_session.date}")
        else:
            self.stdout.write(self.style.WARNING('  Ignoré — aucune absence trouvée pour cet étudiant.'))

        # ── 4. Retard constaté (parent) ─────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[4] Retard constaté (parent)'))
        late = AttendanceRecord.objects.filter(
            student=student, status='LATE'
        ).order_by('-created_at').first()
        if late:
            notify_late_recorded(late)
            self.stdout.write(f"  Déclenché sur le retard du {late.attendance_session.date}")
        else:
            self.stdout.write(self.style.WARNING('  Ignoré — aucun retard trouvé pour cet étudiant.'))

        # ── 5. Rappel d'échéancier de scolarité (étudiant + parent) ─────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[5] Rappel échéancier de scolarité (étudiant + parent)'))
        sent = _maybe_remind_student(student, timezone.now().date())
        if sent:
            self.stdout.write(f"  Déclenché — {sent} notification(s) de rappel envoyée(s)")
        else:
            self.stdout.write(self.style.WARNING(
                '  Ignoré — étudiant à jour, sans échéancier configuré, hors fenêtre de rappel, ou déjà relancé récemment.'
            ))

        # ── Résultat ─────────────────────────────────────────────────────────
        new_notifs = Notification.objects.filter(
            recipient__in=recipients
        ).exclude(id__in=before_ids).order_by('recipient__email', '-created_at')

        self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== {new_notifs.count()} nouvelle(s) notification(s) créée(s) ==='))
        for n in new_notifs:
            who = 'ÉTUDIANT' if n.recipient_id == student.user_id else 'PARENT'
            self.stdout.write(f"  [{who}] {n.recipient.email} — {n.notification_type} — {n.title}")
            self.stdout.write(f"      {n.message}")
