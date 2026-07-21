"""
Realign one student's invoices onto the correct barème (FeeConfiguration) for
their actual enrollment (site/level/modality/affectation/année) — for cases
where the student's dossier shows an inscription/scolarité total that doesn't
match what the barème currently defines for their level.

Two distinct causes are fixed, both scoped to this one student:

1. Duplicate non-cancelled invoices of the same fee_category (e.g. two
   150 000 F INSCRIPTION invoices summing to 300 000 F instead of the real
   150 000 F barème — every total/aggregate in the app sums ALL non-cancelled
   invoices of a given type). Keeps the PAID one if any, else the one with
   the most amount_paid, and cancels the rest — CANCELLED invoices are
   already excluded from every total/aggregate, no other code change needed.
   (Mirrors fix_duplicate_registration_invoice, generalized to SCOLARITE too.)

2. A stale unit_price on the kept invoice's item(s) that no longer matches
   the barème currently on file for this student's level/modality/
   affectation/année (e.g. the barème was corrected after the invoice was
   issued). Only the item(s) whose fee_type.code matches the barème's
   fee_category are touched, and only on invoices not yet PAID/CANCELLED —
   already-settled invoices are left alone.

Never modifies amount_paid or existing payments; invoice.balance/status are
simply recomputed from the corrected item total via calculate_totals().

Usage:
    python manage.py fix_student_fee_config --email fatou.bamba@escam-test.ci             # dry-run
    python manage.py fix_student_fee_config --email fatou.bamba@escam-test.ci --yes        # apply
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Realign one student's invoices (duplicates + stale amounts) onto the correct barème for their enrollment."

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Email of the student user')
        parser.add_argument('--matricule', help='Matricule of the student (alternative to --email)')
        parser.add_argument('--id', help='Student UUID (alternative to --email/--matricule — e.g. from the dossier page URL)')
        parser.add_argument(
            '--yes', action='store_true',
            help='Actually apply the fix. Without this flag, only a dry-run preview is printed.'
        )

    def handle(self, *args, **options):
        from apps.students.models import Student
        from apps.finance.models import FeeConfiguration, Invoice
        from apps.academic.models import Class as AcademicClass

        if not options['email'] and not options['matricule'] and not options['id']:
            raise CommandError('Pass --email, --matricule, or --id to identify the student.')

        try:
            if options['email']:
                student = Student.objects.select_related('user', 'site').get(user__email=options['email'])
            elif options['matricule']:
                student = Student.objects.select_related('user', 'site').get(matricule=options['matricule'])
            else:
                student = Student.objects.select_related('user', 'site').get(pk=options['id'])
        except Student.DoesNotExist:
            raise CommandError('No matching student found.')

        confirm = options['yes']

        enrollment_row = student.enrollments.filter(
            status='ENROLLED', is_active=True
        ).order_by('-created_at').values_list('class_obj_id', 'academic_year_id').first()
        if not enrollment_row:
            raise CommandError('Student has no active enrollment — cannot resolve level/year to find the correct barème.')
        class_obj_id, academic_year_id = enrollment_row
        class_obj = AcademicClass.objects.select_related('level', 'academic_year').get(pk=class_obj_id)
        level = class_obj.level
        academic_year = class_obj.academic_year

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== fix_student_fee_config — {student.user.full_name} ({student.user.email}) — #{student.matricule} ===\n"
        ))
        self.stdout.write(
            f"  Classe={class_obj.name} | Niveau={level} | Site={student.site} | "
            f"Modalité={student.modality} | Affectation={student.affectation_status} | Année={academic_year}\n"
        )

        any_change = False

        for category in ('INSCRIPTION', 'SCOLARITE'):
            fee_config = FeeConfiguration.get_for_enrollment(
                student.site, level, category, academic_year,
                modality=student.modality, affectation_status=student.affectation_status,
            )
            if not fee_config:
                self.stdout.write(self.style.WARNING(f"  [{category}] Aucun barème trouvé — ignoré."))
                continue

            correct_amount = fee_config.amount
            self.stdout.write(f"  [{category}] Barème correct = {correct_amount} FCFA ({fee_config})")

            candidates = [
                inv for inv in Invoice.objects.filter(student=student, is_active=True)
                .exclude(status='CANCELLED').prefetch_related('items__fee_type')
                if any((it.fee_type.code or '').upper() == category for it in inv.items.all() if it.fee_type_id)
            ]

            if not candidates:
                self.stdout.write(f"    Aucune facture {category} trouvée.")
                continue

            # --- Step 1: collapse duplicates, keep the best one ---
            keep = max(candidates, key=lambda inv: (inv.status == 'PAID', inv.amount_paid))
            to_cancel = [inv for inv in candidates if inv.pk != keep.pk]

            for inv in candidates:
                marker = ' (conservée)' if inv.pk == keep.pk else ' (doublon -> annulée)' if inv in to_cancel else ''
                self.stdout.write(
                    f"    - {inv.invoice_number} | total={inv.total} paid={inv.amount_paid} status={inv.status}{marker}"
                )

            if to_cancel:
                any_change = True
                if confirm:
                    with transaction.atomic():
                        for inv in to_cancel:
                            inv.status = 'CANCELLED'
                            inv.save()

            # --- Step 2: fix stale unit_price on the kept invoice ---
            if keep.status not in ('PAID', 'CANCELLED'):
                keep.refresh_from_db()
                item_changed = False
                for item in keep.items.all():
                    code = (item.fee_type.code or '').upper() if item.fee_type_id else ''
                    if code != category or item.unit_price == correct_amount:
                        continue
                    self.stdout.write(
                        f"    - {keep.invoice_number}: item {item.description!r} "
                        f"{item.unit_price} -> {correct_amount} FCFA"
                    )
                    any_change = True
                    item_changed = True
                    if confirm:
                        item.unit_price = correct_amount
                        item.save(update_fields=['unit_price', 'total'])
                if item_changed and confirm:
                    keep.refresh_from_db()
                    keep.save()  # recompute totals/balance/status

            # --- Sync is_enrolled for INSCRIPTION ---
            if category == 'INSCRIPTION' and confirm:
                keep.refresh_from_db()
                new_flag = keep.balance <= 0
                if student.is_enrolled != new_flag:
                    student.is_enrolled = new_flag
                    student.save(update_fields=['is_enrolled'])

        if not any_change:
            self.stdout.write(self.style.SUCCESS('\nRien à corriger — les factures correspondent déjà au barème.'))
        elif not confirm:
            self.stdout.write(self.style.WARNING(
                '\nDry-run only — no changes made. Re-run with --yes to execute.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\nTerminé. Factures réalignées sur le barème.'))
