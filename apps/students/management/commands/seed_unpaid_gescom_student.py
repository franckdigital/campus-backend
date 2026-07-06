"""
Seed ONE clean test student (+ linked parent) in BTS Gestion Commerciale
(ESCAM Cocody), matching the existing barème exactly, but with ZERO
payments at all — not enrolled (registration fee unpaid, no inscription
invoice) and nothing paid on scolarité either. Unlike
seed_echeancier_students.py (which seeds 2 students with partial payments
already muddying the échéancier math), this one is meant for a clean,
from-scratch test of the échéancier reminder notification (both the
"Non à jour" badge and the red-card mobile reminder) end-to-end on a real
device, with no pre-existing invoices to confuse the picture.

Reuses the same barème/échéancier (Mai + Juin tranches) created by
seed_echeancier_students.py — run that command first if it hasn't been run
on this environment yet.

Usage:
    python manage.py seed_unpaid_gescom_student
    python manage.py seed_unpaid_gescom_student --first-name Yves --last-name Kouassi \
        --email yves.kouassi@escam-test.ci --parent-first Adjoua --parent-last Kouassi \
        --parent-email adjoua.kouassi@escam-test.ci
"""
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Seed one unpaid/not-yet-enrolled BTS Gestion Commerciale test student for échéancier reminder testing'

    def add_arguments(self, parser):
        parser.add_argument('--first-name', default='Aminata')
        parser.add_argument('--last-name', default='Traore')
        parser.add_argument('--email', default='aminata.traore@escam-test.ci')
        parser.add_argument('--phone', default='+225 01 23 45 67')
        parser.add_argument('--gender', default='F', choices=['F', 'M'])
        parser.add_argument('--parent-first', default='Koné')
        parser.add_argument('--parent-last', default='Traore')
        parser.add_argument('--parent-email', default='kone.traore@escam-test.ci')
        parser.add_argument('--parent-relation', default='FATHER', choices=['FATHER', 'MOTHER', 'GUARDIAN'])

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.students.models import Student, Parent, StudentParent
        from apps.core.models import Site, AcademicYear
        from apps.academic.models import Program, Level, Class, Enrollment

        self.stdout.write(self.style.MIGRATE_HEADING('Seeding unpaid BTS Gestion Commerciale test student...'))

        with transaction.atomic():
            site = Site.objects.filter(name__icontains='ESCAM').first()
            if not site:
                raise SystemExit('Aucun site ESCAM trouvé — lancez seed_echeancier_students en premier.')

            academic_year = AcademicYear.objects.filter(is_current=True).first()
            if not academic_year:
                raise SystemExit('Aucune année académique courante trouvée.')

            program = Program.objects.filter(code='ESCAM-BTSGESCOM', site=site).first()
            level = Level.objects.filter(program=program, code='L1BTSGESCOM').first() if program else None
            class_obj = Class.objects.filter(level=level, site=site, academic_year=academic_year).first() if level else None

            if not (program and level and class_obj):
                raise SystemExit(
                    'Barème/classe BTS Gestion Commerciale introuvable — '
                    'lancez d\'abord: python manage.py seed_echeancier_students'
                )

            self.stdout.write(f'  Site: {site.name} | Filière/Niveau: {program.name} / {level.name} | Classe: {class_obj.name}')

            email = options['email']
            parent_email = options['parent_email']
            password = 'campus123'

            user, created = User.objects.get_or_create(
                email=email, defaults={'user_type': 'STUDENT'},
            )
            user.first_name = options['first_name']
            user.last_name = options['last_name']
            user.phone = options['phone']
            user.user_type = 'STUDENT'
            user.site = site
            user.is_active = True
            user.set_password(password)
            user.save()

            student, s_created = Student.objects.get_or_create(
                user=user,
                defaults={
                    'site': site, 'gender': options['gender'],
                    'birth_date': datetime.date(2004, 6, 15), 'birth_place': 'Abidjan',
                    'nationality': 'Ivoirienne', 'status': 'ACTIVE',
                    'modality': 'PRESENTIEL', 'affectation_status': 'AFFECTE',
                    'admission_date': datetime.date(2025, 9, 1),
                    'registration_fee': 150000, 'registration_fee_paid': False,
                    'tuition_fee': 500000,
                    'total_paid': 0, 'remaining_balance': 650000,
                },
            )
            if not s_created:
                student.site = site
                student.modality = 'PRESENTIEL'
                student.affectation_status = 'AFFECTE'
                student.status = 'ACTIVE'
                student.registration_fee_paid = False
                student.echeance_override = False
                student.save()
            self.stdout.write(f'  Student: #{student.matricule} ({"créé" if s_created else "déjà existant"}) — registration_fee_paid=False, aucune facture')

            Enrollment.objects.get_or_create(
                student=student, academic_year=academic_year,
                defaults={'class_obj': class_obj, 'status': 'ENROLLED', 'is_active': True},
            )

            # Delete any invoices left over from a previous run of this
            # command, so the test always starts from a truly clean slate.
            from apps.finance.models import Invoice
            deleted, _ = Invoice.objects.filter(student=student).delete()
            if deleted:
                self.stdout.write(f'  ({deleted} facture(s) résiduelle(s) supprimée(s) pour repartir à zéro)')

            parent_user, _ = User.objects.get_or_create(
                email=parent_email, defaults={'user_type': 'PARENT'},
            )
            parent_user.first_name = options['parent_first']
            parent_user.last_name = options['parent_last']
            parent_user.user_type = 'PARENT'
            parent_user.site = site
            parent_user.is_active = True
            parent_user.set_password(password)
            parent_user.save()

            parent, _ = Parent.objects.get_or_create(
                user=parent_user, defaults={'relationship': options['parent_relation']},
            )
            StudentParent.objects.get_or_create(
                student=student, parent=parent,
                defaults={'is_primary': True, 'can_pickup': True, 'receives_notifications': True},
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('OK — étudiant non-inscrit prêt pour le test de rappel échéancier.'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(f'Compte étudiant : {email} / mot de passe : {password}'))
        self.stdout.write(self.style.WARNING(f'Compte parent   : {parent_email} / mot de passe : {password}'))
        self.stdout.write('')
        self.stdout.write(
            "Le premier rappel ne part qu'à partir du 25 du mois (voir apps.finance.tasks."
            "REMINDER_START_DAY) pour le calcul d'éligibilité — mais l'envoi est immédiat, "
            "quelle que soit la date simulée.\n"
            'Pour déclencher le rappel tout de suite :\n'
            f'  python manage.py test_echeancier_reminders --date 2026-07-25 --email {email}'
        )
