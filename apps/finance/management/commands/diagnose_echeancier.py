"""
Read-only diagnostic: walks through every step of
_resolve_fee_config_for_student() / compute_tuition_schedule_status() for one
student and prints each intermediate value, to find exactly where the
échéancier resolution chain breaks (no enrollment? wrong site/modality/
affectation? FeeConfiguration missing or mismatched? no installments?).

Usage:
    python manage.py diagnose_echeancier --email ibrahim.coulibaly@escam-test.ci
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Diagnose why a student's échéancier de scolarité isn't resolving (has_schedule=False)."

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Email of the student user')
        parser.add_argument('--matricule', help='Matricule of the student (alternative to --email)')

    def handle(self, *args, **options):
        from apps.students.models import Student
        from apps.academic.models import Class as AcademicClass
        from apps.finance.models import (
            FeeConfiguration, compute_tuition_schedule_status,
            _resolve_fee_config_for_student, get_student_installment_schedule,
        )

        if not options['email'] and not options['matricule']:
            raise CommandError('Pass --email or --matricule to identify the student.')

        try:
            if options['email']:
                student = Student.objects.select_related('user', 'site').get(user__email=options['email'])
            else:
                student = Student.objects.select_related('user', 'site').get(matricule=options['matricule'])
        except Student.DoesNotExist:
            raise CommandError('No matching student found.')

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== diagnose_echeancier — {student.user.full_name} ({student.user.email}) ===\n"
        ))
        self.stdout.write(f"  site           = {student.site} (id={student.site_id})")
        self.stdout.write(f"  modality       = {student.modality!r}")
        self.stdout.write(f"  affectation    = {student.affectation_status!r}")
        self.stdout.write(f"  echeance_override = {student.echeance_override}")

        # ── Step 1: active ENROLLED enrollment ──────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[1] Enrollment (status=ENROLLED, is_active=True)'))
        all_enrollments = list(student.enrollments.all().values('id', 'status', 'is_active', 'class_obj_id', 'academic_year_id', 'created_at'))
        if not all_enrollments:
            self.stdout.write(self.style.ERROR('  Aucune inscription (Enrollment) trouvée du tout pour cet étudiant.'))
        else:
            for e in all_enrollments:
                self.stdout.write(f"    id={e['id']} status={e['status']!r} is_active={e['is_active']} class_obj_id={e['class_obj_id']} academic_year_id={e['academic_year_id']} created_at={e['created_at']}")

        enrollment_row = student.enrollments.filter(
            status='ENROLLED', is_active=True
        ).order_by('-created_at').values_list('class_obj_id', 'academic_year_id').first()

        level = None
        if not enrollment_row:
            self.stdout.write(self.style.ERROR('  -> AUCUNE inscription ENROLLED+active trouvée — level et academic_year resteront None.'))
        else:
            class_obj_id, academic_year_id = enrollment_row
            self.stdout.write(f"  -> class_obj_id retenu = {class_obj_id} | academic_year_id retenu = {academic_year_id}")
            try:
                class_obj = AcademicClass.objects.select_related('level', 'level__program').get(pk=class_obj_id)
                level = class_obj.level
                self.stdout.write(f"  -> classe = {class_obj} | niveau = {level} (id={level.id if level else None}) | programme = {level.program if level else None}")
            except AcademicClass.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'  -> Classe {class_obj_id} introuvable (supprimée ?).'))

        # ── Step 2: matching FeeConfiguration rows (SCOLARITE) ──────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[2] Barèmes SCOLARITE actifs en base (toutes portées confondues)'))
        scol_configs = FeeConfiguration.objects.filter(fee_category='SCOLARITE', is_active=True)
        if not scol_configs.exists():
            self.stdout.write(self.style.ERROR('  Aucun barème SCOLARITE actif du tout en base !'))
        for cfg in scol_configs:
            self.stdout.write(
                f"    id={cfg.id} site={cfg.site_id} program={cfg.program_id} level={cfg.level_id} "
                f"academic_year={cfg.academic_year_id} modality={cfg.modality!r} affectation={cfg.affectation_status!r} "
                f"amount={cfg.amount} installments={cfg.installments.count()}"
            )

        # ── Step 3: actual resolution (real shared resolver — site + level +
        # academic_year auto-resolved from the enrollment + modality/affectation) ──
        self.stdout.write(self.style.MIGRATE_HEADING('\n[3] Résolution via _resolve_fee_config_for_student (le vrai chemin utilisé partout)'))
        resolved = _resolve_fee_config_for_student(student)
        if resolved:
            self.stdout.write(self.style.SUCCESS(f"  -> Résolu : {resolved} (id={resolved.id}, amount={resolved.amount}, installments={resolved.installments.count()})"))
        else:
            self.stdout.write(self.style.ERROR('  -> AUCUN barème SCOLARITE ne correspond (site/niveau/modalité/affectation ne matchent aucune ligne ci-dessus).'))

        # ── Step 4: final compute_tuition_schedule_status ───────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[4] compute_tuition_schedule_status (résultat final utilisé par les rappels)'))
        status = compute_tuition_schedule_status(student)
        for k, v in status.items():
            self.stdout.write(f"    {k} = {v}")

        # ── Step 5: exact payload the admin dossier's "Échéancier" table
        # consumes (GET /students/{id}/echeancier/) — confirms whether the
        # table SHOULD be visible, isolating a "table absent" report to
        # either the frontend/network layer or a real backend gap. ────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n[5] get_student_installment_schedule (payload de /students/{id}/echeancier/)'))
        schedule = get_student_installment_schedule(student)
        self.stdout.write(f"    has_schedule = {schedule['has_schedule']}")
        self.stdout.write(f"    total = {schedule['total']} | cumulative_paid = {schedule['cumulative_paid']}")
        if schedule['installments']:
            for row in schedule['installments']:
                self.stdout.write(
                    f"      - {row['label']!r} due={row['due_date']} amount={row['amount']} "
                    f"cumulative_due={row['cumulative_due']} status={row['status']}"
                )
        else:
            self.stdout.write(self.style.WARNING('      (aucune tranche — le tableau ne peut pas s\'afficher)'))
