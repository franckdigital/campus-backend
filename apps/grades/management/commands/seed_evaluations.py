"""
seed_evaluations.py
-------------------
1. Supprime les semestres sans année (label = 'Semestre 1' / 'Semestre 2')
2. Crée les évaluations (CC, TP, Examen, Rattrapage) pour toutes les classes
   de l'année 2025-2026 sur les deux semestres, par matière via LevelSubject.

Usage:
    python manage.py seed_evaluations
    python manage.py seed_evaluations --wipe   # supprime toutes les évals 2025-2026 avant
"""
from datetime import date
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seed evaluations for all 2025-2026 classes (all types: CC, TP, Examen, Rattrapage)'

    def add_arguments(self, parser):
        parser.add_argument('--wipe', action='store_true',
                            help='Supprimer toutes les évaluations 2025-2026 avant de créer')

    def handle(self, *args, **options):
        from apps.academic.models import Class, Semester, LevelSubject, ClassSubjectTeacher
        from apps.grades.models import Evaluation, GradeCategory
        from apps.accounts.models import User
        from apps.core.models import AcademicYear

        # ── 0. Nettoyer les sémestres sans année ────────────────────────────
        self._clean_orphan_semesters()

        # ── 1. Récupérer les références 2025-2026 ───────────────────────────
        try:
            ay = AcademicYear.objects.get(name='2025-2026')
        except AcademicYear.DoesNotExist:
            self.stderr.write('Année académique 2025-2026 introuvable.')
            return

        try:
            s1 = Semester.objects.get(academic_year=ay, name='S1')
            s2 = Semester.objects.get(academic_year=ay, name='S2')
        except Semester.DoesNotExist as e:
            self.stderr.write(f'Semestre introuvable : {e}')
            return

        classes = list(Class.objects.filter(academic_year=ay).select_related('level', 'main_teacher__user'))
        if not classes:
            self.stderr.write('Aucune classe trouvée pour 2025-2026.')
            return

        # Utilisateur créateur = premier admin actif
        creator = User.objects.filter(user_type='ADMIN', is_active=True).first()
        if not creator:
            creator = User.objects.filter(is_superuser=True).first()

        # ── 2. Catégories de notes ───────────────────────────────────────────
        cat_cc, _   = GradeCategory.objects.get_or_create(code='CC',   defaults={'name': 'Contrôle Continu', 'weight': 0.4})
        cat_tp, _   = GradeCategory.objects.get_or_create(code='TP',   defaults={'name': 'Travaux Pratiques', 'weight': 0.2})
        cat_ex, _   = GradeCategory.objects.get_or_create(code='EXAM', defaults={'name': 'Examen Final',      'weight': 0.6})
        cat_ra, _   = GradeCategory.objects.get_or_create(code='RATTR',defaults={'name': 'Rattrapage',        'weight': 1.0})

        # ── 3. Optionnel : wipe ─────────────────────────────────────────────
        if options['wipe']:
            deleted, _ = Evaluation.objects.filter(
                class_group__academic_year=ay
            ).delete()
            self.stdout.write(self.style.WARNING(f'  {deleted} évaluations supprimées (--wipe)'))

        # ── 4. Créer les évaluations ─────────────────────────────────────────
        # Calendrier S1 : sept → jan
        s1_dates = {
            'DEVOIR':     date(2025, 10, 20),   # CC1
            'TP':         date(2025, 11, 17),   # TP1
            'EXAMEN':     date(2026,  1, 19),   # Exam S1
            'RATTRAPAGE': date(2026,  2,  9),   # Rattrapage S1
        }
        # Calendrier S2 : fév → juin
        s2_dates = {
            'DEVOIR':     date(2026,  3, 23),   # CC2
            'TP':         date(2026,  4, 20),   # TP2
            'EXAMEN':     date(2026,  6, 15),   # Exam S2
            'RATTRAPAGE': date(2026,  7,  6),   # Rattrapage S2
        }

        # Libellés et coefficients par type
        EVAL_CONFIG = {
            # (titre_template, coefficient, max_score)
            'DEVOIR':     ('CC1 {short}',        1,  20),
            'TP':         ('TP1 {short}',         1,  20),
            'EXAMEN':     ('Examen S{sem} {short}', 2, 20),
            'RATTRAPAGE': ('Rattrapage S{sem} {short}', 1, 20),
        }

        total_created = total_skipped = 0

        for cls in classes:
            level_subjects = LevelSubject.objects.filter(
                level=cls.level
            ).select_related('subject')

            if not level_subjects.exists():
                self.stdout.write(f'  [SKIP] {cls.name} — aucune matière au niveau {cls.level}')
                continue

            # Map subject → teacher via ClassSubjectTeacher (si dispo)
            cst_map = {
                str(cst.subject_id): cst.teacher
                for cst in ClassSubjectTeacher.objects.filter(class_obj=cls).select_related('teacher__user')
            }
            fallback_teacher = cls.main_teacher or (
                ClassSubjectTeacher.objects.filter(class_obj=cls)
                .select_related('teacher__user').first()
            )
            fallback_teacher = fallback_teacher.teacher if hasattr(fallback_teacher, 'teacher') else fallback_teacher

            for ls in level_subjects:
                subj = ls.subject
                # Diminutif pour les titres : ex. "ALGO" ou "Algorithmique..."[:8]
                short = subj.code if len(subj.code) <= 8 else subj.name[:12]
                teacher = cst_map.get(str(subj.id)) or fallback_teacher

                for sem_obj, dates_map, sem_num in [
                    (s1, s1_dates, 1),
                    (s2, s2_dates, 2),
                ]:
                    for eval_type, (title_tpl, coeff, max_score) in EVAL_CONFIG.items():
                        title = title_tpl.format(short=short, sem=sem_num)
                        ev_date = dates_map[eval_type]

                        # Ajuste le titre pour S2 CC/TP
                        if sem_num == 2 and eval_type == 'DEVOIR':
                            title = title.replace('CC1', 'CC2')
                        if sem_num == 2 and eval_type == 'TP':
                            title = title.replace('TP1', 'TP2')

                        _, created = Evaluation.objects.get_or_create(
                            title=title,
                            eval_type=eval_type,
                            subject=subj,
                            class_group=cls,
                            semester=sem_obj,
                            defaults={
                                'date': ev_date,
                                'max_score': max_score,
                                'coefficient': coeff,
                                'is_locked': False,
                                'created_by': creator,
                            },
                        )
                        if created:
                            total_created += 1
                        else:
                            total_skipped += 1

            self.stdout.write(f'  OK {cls.name}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Terminé : {total_created} évaluations créées, {total_skipped} déjà existantes'
        ))

    # ─────────────────────────────────────────────────────────────────────────
    def _clean_orphan_semesters(self):
        from apps.academic.models import Semester
        # Supprime les semestres dont le label ne contient pas d'année (ex. "Semestre 1")
        to_delete = Semester.objects.filter(
            academic_year__name='2024-2025'
        )
        count = to_delete.count()
        if count:
            names = list(to_delete.values_list('label', flat=True))
            to_delete.delete()
            self.stdout.write(self.style.WARNING(
                f'  Supprimé {count} semestre(s) 2024-2025 : {names}'
            ))
        else:
            self.stdout.write('  Aucun semestre 2024-2025 à supprimer')
