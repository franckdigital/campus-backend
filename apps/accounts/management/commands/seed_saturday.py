"""
seed_saturday.py
Crée une session samedi 10h-12h pour la classe Licence 1 d'ITA Marcory
(enseignant : e.ngoran@ita-marc.ci — Réseaux & Sécurité).
k.kouadio est déjà inscrit dans cette classe via seed_full.

Usage:
    python manage.py seed_saturday
    python manage.py seed_saturday --wipe
"""
from datetime import time
from django.core.management.base import BaseCommand

TEACHER_EMAIL = 'e.ngoran@ita-marc.ci'
SITE_CODE     = 'ITA-MARC'
DAY_SAT       = 6   # convention frontend : 1=Lun … 6=Sam
START         = time(10, 0)
END           = time(12, 0)


class Command(BaseCommand):
    help = 'Crée la session samedi 10h-12h à ITA Marcory'

    def add_arguments(self, parser):
        parser.add_argument('--wipe', action='store_true',
                            help='Supprime la session créée par ce seed')

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.academic.models import Session, Class as ClassModel, ClassSubjectTeacher
        from apps.core.models import Site

        # ── Wipe ────────────────────────────────────────────────
        if options['wipe']:
            deleted, _ = Session.objects.filter(
                teacher__user__email=TEACHER_EMAIL,
                day_of_week=DAY_SAT,
                start_time=START,
            ).delete()
            self.stdout.write(self.style.SUCCESS(f'{deleted} session(s) samedi supprimée(s).'))
            return

        # ── Trouver le site ITA Marcory ─────────────────────────
        site = Site.objects.filter(code=SITE_CODE).order_by('created_at').first()
        if not site:
            self.stderr.write(self.style.ERROR(
                f'Site {SITE_CODE} introuvable. Lancez seed_full d\'abord.'
            ))
            return

        # ── Trouver l'enseignant ────────────────────────────────
        try:
            teacher_user = User.objects.get(email=TEACHER_EMAIL)
            teacher = teacher_user.teacher_profile
        except (User.DoesNotExist, Exception) as exc:
            self.stderr.write(self.style.ERROR(
                f'Enseignant {TEACHER_EMAIL} introuvable : {exc}\n'
                'Lancez seed_full d\'abord.'
            ))
            return

        # ── Trouver la classe Licence 1 — ITA Marcory ──────────
        cls = (
            ClassModel.objects
            .filter(site=site)
            .order_by('created_at')
            .first()
        )
        if not cls:
            self.stderr.write(self.style.ERROR(
                'Aucune classe trouvée pour ITA Marcory. Lancez seed_full d\'abord.'
            ))
            return

        self.stdout.write(f'Classe  : {cls.name} ({cls.code})')
        self.stdout.write(f'Site    : {site.name}')
        self.stdout.write(f'Enseignant : {teacher.user.full_name}')

        # ── Trouver une matière enseignée par cet enseignant ────
        cst = ClassSubjectTeacher.objects.filter(
            class_obj=cls, teacher=teacher
        ).first()
        if cst:
            subject = cst.subject
        else:
            # Fallback : première matière de la classe
            cst_any = ClassSubjectTeacher.objects.filter(class_obj=cls).first()
            subject = cst_any.subject if cst_any else None

        if not subject:
            self.stderr.write(self.style.ERROR('Aucune matière trouvée pour cette classe.'))
            return

        self.stdout.write(f'Matière : {subject.name}')

        # ── Créer (ou récupérer) la session samedi ──────────────
        sess, created = Session.objects.get_or_create(
            class_obj=cls,
            teacher=teacher,
            subject=subject,
            day_of_week=DAY_SAT,
            start_time=START,
            defaults={'end_time': END, 'is_recurring': True},
        )
        if not created and sess.end_time != END:
            sess.end_time = END
            sess.save(update_fields=['end_time'])

        verb = 'créée ✓' if created else 'déjà existante (inchangée)'
        self.stdout.write(self.style.SUCCESS(
            f'Session samedi {START.strftime("%Hh")}-{END.strftime("%Hh")} '
            f'({subject.name}) {verb}'
        ))

        # ── Vérifier l'inscription de k.kouadio ─────────────────
        from apps.academic.models import Enrollment
        kevin_enrolled = Enrollment.objects.filter(
            student__user__email='k.kouadio@ita-marc.ci',
            class_obj=cls,
        ).exists()

        self.stdout.write('')
        self.stdout.write('─' * 58)
        self.stdout.write('RÉSUMÉ POUR LE TEST DE POINTAGE — ITA MARCORY')
        self.stdout.write('─' * 58)
        self.stdout.write(f'  Site        : {site.name}')
        self.stdout.write(f'  Classe      : {cls.name}')
        self.stdout.write(f'  Session     : Samedi {START.strftime("%Hh")}-{END.strftime("%Hh")} → {subject.name}')
        self.stdout.write(f'  Enseignant  : {TEACHER_EMAIL}  /  Campus2024!')
        self.stdout.write(f'  Étudiant    : k.kouadio@ita-marc.ci  /  Campus2024!')
        self.stdout.write(f'  Parent      : p.kouadio@gmail.com    /  Campus2024!')
        self.stdout.write(f'  Kevin inscrit dans la classe : {"oui" if kevin_enrolled else "NON — relancer seed_full"}')
        self.stdout.write('─' * 58)
