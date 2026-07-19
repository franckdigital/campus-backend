"""
Read-only diagnostic: shows a student's real attributes (site, modality,
affectation_status, enrollment level/academic_year) next to which
FeeConfiguration row get_for_enrollment() actually resolves for INSCRIPTION
and SCOLARITE — used to explain why a dossier's configured fallback totals
(shown when an invoice's fee_type doesn't match the classification regex)
don't match the barème visible in the admin "Types de frais" table.

Usage:
    python manage.py diagnose_student_bareme --email fatou.bamba@escam-test.ci
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Show which FeeConfiguration row actually resolves for a student, vs their enrollment attributes."

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Email of the student user')
        parser.add_argument('--matricule', help='Matricule of the student (alternative to --email)')
        parser.add_argument('--id', help='Student UUID (alternative to --email/--matricule — e.g. from the dossier page URL)')

    def handle(self, *args, **options):
        from apps.students.models import Student
        from apps.finance.models import FeeConfiguration

        if not options['email'] and not options['matricule'] and not options['id']:
            raise CommandError('Pass --email, --matricule, or --id.')

        try:
            if options['email']:
                student = Student.objects.select_related('user', 'site').get(user__email=options['email'])
            elif options['matricule']:
                student = Student.objects.select_related('user', 'site').get(matricule=options['matricule'])
            else:
                student = Student.objects.select_related('user', 'site').get(pk=options['id'])
        except Student.DoesNotExist:
            raise CommandError('No matching student found.')

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== {student.user.full_name} ({student.user.email}) — #{student.matricule} ===\n"
        ))
        self.stdout.write(f"  site           = {student.site} (id={student.site_id})")
        self.stdout.write(f"  modality       = {student.modality!r}")
        self.stdout.write(f"  affectation    = {student.affectation_status!r}")

        # Surface duplicate ENROLLED+active rows directly — resolve_current_enrollment
        # (used everywhere: this command, ensure_student_invoices, financial_summary)
        # picks the most-recent by created_at when more than one exists, which is
        # exactly the failure mode that silently prices a student off a stale/wrong
        # programme's barème (see apps.academic.signals.deactivate_other_enrollments,
        # which prevents this going forward but doesn't retroactively clean up rows
        # created before it existed).
        active_enrollments = list(student.enrollments.filter(status='ENROLLED', is_active=True).select_related('class_obj__level__program', 'academic_year').order_by('-created_at'))
        if len(active_enrollments) > 1:
            self.stdout.write(self.style.ERROR(f"\n  /!\\ {len(active_enrollments)} inscriptions ENROLLED+active trouvées — une seule devrait exister :"))
            for e in active_enrollments:
                self.stdout.write(f"    - id={e.id} classe={e.class_obj} créée le {e.created_at} {'<- la plus récente (celle utilisée)' if e is active_enrollments[0] else '(IGNORÉE mais toujours active — à désactiver/supprimer via l\'onglet Parcours)'}")
            self.stdout.write('')

        enrollment_row = student.enrollments.filter(
            status='ENROLLED', is_active=True
        ).order_by('-created_at').values_list('class_obj_id', 'academic_year_id').first()

        level = None
        academic_year = None
        if not enrollment_row:
            self.stdout.write(self.style.ERROR('  Aucune inscription (Enrollment) ENROLLED+active trouvée.'))
        else:
            class_obj_id, academic_year_id = enrollment_row
            self.stdout.write(f"  enrollment class_obj_id = {class_obj_id} | academic_year_id = {academic_year_id}")
            if class_obj_id:
                from apps.academic.models import Class as AcademicClass
                try:
                    class_obj = AcademicClass.objects.select_related('level', 'level__program').get(pk=class_obj_id)
                    level = class_obj.level
                    self.stdout.write(f"  -> classe = {class_obj} | niveau = {level} (id={level.id if level else None}) | programme = {level.program if level else None}")
                except AcademicClass.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'  Classe {class_obj_id} introuvable.'))
            if academic_year_id:
                from apps.core.models import AcademicYear
                academic_year = AcademicYear.objects.filter(pk=academic_year_id).first()
                self.stdout.write(f"  -> academic_year = {academic_year}")

        for category in ('INSCRIPTION', 'SCOLARITE'):
            self.stdout.write(self.style.MIGRATE_HEADING(f'\n[{category}] Résolution via get_for_enrollment'))
            resolved = FeeConfiguration.get_for_enrollment(
                student.site, level, category, academic_year,
                modality=student.modality, affectation_status=student.affectation_status
            )
            if resolved:
                self.stdout.write(self.style.SUCCESS(
                    f"  -> Résolu : id={resolved.id} label={resolved.label!r} site={resolved.site_id} "
                    f"level={resolved.level_id} academic_year={resolved.academic_year_id} "
                    f"modality={resolved.modality!r} affectation={resolved.affectation_status!r} amount={resolved.amount}"
                ))
            else:
                self.stdout.write(self.style.ERROR('  -> AUCUN barème ne correspond.'))

            self.stdout.write(f'\n  Tous les barèmes {category} actifs en base :')
            for cfg in FeeConfiguration.objects.filter(fee_category=category, is_active=True):
                self.stdout.write(
                    f"    id={cfg.id} label={cfg.label!r} site={cfg.site_id} level={cfg.level_id} "
                    f"academic_year={cfg.academic_year_id} modality={cfg.modality!r} "
                    f"affectation={cfg.affectation_status!r} amount={cfg.amount}"
                )
