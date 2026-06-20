"""
seed_saturday.py
Crée :
  1. Une session samedi 10h-12h pour Marc-Antoine Brou (ITA Plateau) dans sa classe Licence 1
  2. Inscrit k.kouadio@ita-marc.ci dans cette classe (si pas déjà inscrit)

Usage:
    python manage.py seed_saturday
    python manage.py seed_saturday --wipe  (supprime les données créées par ce seed)
"""
from datetime import time
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crée la session samedi de Marc-Antoine Brou et inscrit k.kouadio'

    def add_arguments(self, parser):
        parser.add_argument('--wipe', action='store_true', help='Supprime les données de ce seed')

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.academic.models import Session, Class as ClassModel, Enrollment, AcademicYear
        from apps.students.models import Student

        if options['wipe']:
            Session.objects.filter(
                teacher__user__email='m.brou@ita-plat.ci',
                day_of_week=6,
                start_time=time(10, 0),
            ).delete()
            self.stdout.write(self.style.SUCCESS('Session samedi supprimée.'))
            return

        # ── Trouver Marc-Antoine Brou ────────────────────────────
        try:
            brou_user = User.objects.get(email='m.brou@ita-plat.ci')
            brou = brou_user.teacher_profile
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                "Enseignant m.brou@ita-plat.ci introuvable. Lancez seed_full d'abord."
            ))
            return

        # ── Trouver la classe Licence 1 de Marc-Antoine Brou ────
        cls = ClassModel.objects.filter(
            main_teacher=brou
        ).order_by('created_at').first()

        if not cls:
            # Cherche dans ClassSubjectTeacher
            from apps.academic.models import ClassSubjectTeacher
            cst = ClassSubjectTeacher.objects.filter(teacher=brou).first()
            cls = cst.class_obj if cst else None

        if not cls:
            self.stderr.write(self.style.ERROR(
                'Aucune classe trouvée pour Marc-Antoine Brou. Lancez seed_full d\'abord.'
            ))
            return

        self.stdout.write(f'Classe trouvée : {cls.name} ({cls.code})')

        # ── Trouver une matière pour la session ─────────────────
        from apps.academic.models import ClassSubjectTeacher, Subject
        cst = ClassSubjectTeacher.objects.filter(class_obj=cls, teacher=brou).first()
        if cst:
            subject = cst.subject
        else:
            subject = Subject.objects.filter(is_active=True).first()
        if not subject:
            self.stderr.write(self.style.ERROR('Aucune matière disponible.'))
            return

        self.stdout.write(f'Matière : {subject.name}')

        # ── Créer ou récupérer la session samedi ─────────────────
        # day_of_week=6 → Samedi (convention frontend: 1=Lun … 6=Sam)
        sess, created = Session.objects.get_or_create(
            class_obj=cls,
            teacher=brou,
            subject=subject,
            day_of_week=6,
            start_time=time(10, 0),
            defaults={
                'end_time': time(12, 0),
                'is_recurring': True,
            }
        )
        if sess.end_time != time(12, 0):
            sess.end_time = time(12, 0)
            sess.save(update_fields=['end_time'])

        verb = 'créée' if created else 'déjà existante'
        self.stdout.write(self.style.SUCCESS(
            f'Session samedi 10h-12h ({subject.name}) {verb} — classe {cls.code}'
        ))

        # ── Trouver k.kouadio ────────────────────────────────────
        try:
            kevin_user = User.objects.get(email='k.kouadio@ita-marc.ci')
            kevin = kevin_user.student_profile
        except (User.DoesNotExist, Student.DoesNotExist):
            self.stderr.write(self.style.ERROR(
                "Étudiant k.kouadio@ita-marc.ci introuvable. Lancez seed_full d'abord."
            ))
            return

        # ── Inscrire Kevin dans la classe de Marc-Antoine ────────
        # unique_together = (student, academic_year) → update_or_create sur cette clé
        ay = cls.academic_year
        existing = Enrollment.objects.filter(student=kevin, academic_year=ay).first()
        if existing:
            if str(existing.class_obj_id) == str(cls.pk):
                self.stdout.write(self.style.SUCCESS(
                    f'Inscription de k.kouadio dans {cls.code} ({ay.name}) déjà existante'
                ))
            else:
                prev = existing.class_obj.code
                existing.class_obj = cls
                existing.status = 'ENROLLED'
                existing.save(update_fields=['class_obj', 'status'])
                self.stdout.write(self.style.SUCCESS(
                    f'Inscription de k.kouadio transférée : {prev} → {cls.code} ({ay.name})'
                ))
        else:
            Enrollment.objects.create(
                student=kevin, class_obj=cls, academic_year=ay, status='ENROLLED'
            )
            self.stdout.write(self.style.SUCCESS(
                f'Inscription de k.kouadio dans {cls.code} ({ay.name}) créée'
            ))

        self.stdout.write('')
        self.stdout.write('─' * 55)
        self.stdout.write('IDENTIFIANTS POUR TESTER LE POINTAGE')
        self.stdout.write('─' * 55)
        self.stdout.write(f'  Enseignant  : m.brou@ita-plat.ci   / Campus2024!')
        self.stdout.write(f'  Étudiant    : k.kouadio@ita-marc.ci / Campus2024!')
        self.stdout.write(f'  Classe      : {cls.name}')
        self.stdout.write(f'  Session     : Samedi 10h-12h → {subject.name}')
        self.stdout.write('─' * 55)
