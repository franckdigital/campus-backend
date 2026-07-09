"""
Reset every @escam-test.ci student's Inscription and Scolarité invoices back
to a clean, fully-unpaid baseline matching the current barème (FeeConfiguration)
for their program/level — deletes their existing Invoice/InvoiceItem/Payment
rows first, so no leftover duplicate/stray invoices survive (the exact class
of bug that caused "à jour" to be wrong and the Scolarité column to show
"—" earlier tonight).

Read-only by default (dry-run); pass --yes to actually apply.

Usage:
    python manage.py reset_escam_student_fees
    python manage.py reset_escam_student_fees --yes
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone as tz
from datetime import timedelta


class Command(BaseCommand):
    help = "Reset ESCAM test students' Inscription/Scolarité invoices to a clean, unpaid baseline matching the barème."

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Actually apply (default: dry-run)')

    def handle(self, *args, **options):
        from apps.students.models import Student
        from apps.finance.models import (
            Invoice, InvoiceItem, Payment, FeeType, FeeConfiguration,
            _resolve_fee_config_for_student,
        )

        students = Student.objects.filter(
            user__email__endswith='@escam-test.ci'
        ).select_related('user', 'site')

        if not students.exists():
            self.stdout.write(self.style.ERROR('Aucun etudiant @escam-test.ci trouve.'))
            return

        fee_inscr, _ = FeeType.objects.get_or_create(
            code='INSCRIPTION', defaults={'name': "Frais d'inscription", 'default_amount': 150000},
        )
        fee_scol, _ = FeeType.objects.get_or_create(
            code='SCOLARITE', defaults={'name': 'Frais de scolarite', 'default_amount': 500000, 'is_recurring': True},
        )

        self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== {students.count()} etudiant(s) @escam-test.ci ===\n'))

        from apps.payments.models import CinetPayTransaction

        plan = []
        for student in students:
            existing_invoices = Invoice.objects.filter(student=student)
            existing_payments = Payment.objects.filter(invoice__student=student)
            existing_transactions = CinetPayTransaction.objects.filter(invoice__student=student)

            inscr_config = FeeConfiguration.objects.filter(
                site=student.site, program=student.enrollments.filter(is_active=True).values_list('class_obj__level__program', flat=True).first(),
                level=student.enrollments.filter(is_active=True).values_list('class_obj__level', flat=True).first(),
                fee_category='INSCRIPTION', is_active=True,
            ).first()
            scol_config = _resolve_fee_config_for_student(student)

            inscr_amount = inscr_config.amount if inscr_config else 150000
            scol_amount = scol_config.amount if scol_config else 500000

            self.stdout.write(f'\n  -- {student.user.full_name} ({student.user.email}) --')
            self.stdout.write(
                f'     Factures existantes a supprimer: {existing_invoices.count()} '
                f'(paiements: {existing_payments.count()}, transactions CinetPay: {existing_transactions.count()})'
            )
            self.stdout.write(f'     Nouvelle facture Inscription: {inscr_amount} FCFA (0 paye)')
            self.stdout.write(f'     Nouvelle facture Scolarite: {scol_amount} FCFA (0 paye)')

            plan.append((student, inscr_amount, scol_amount))

        if not options['yes']:
            self.stdout.write(self.style.WARNING('\nDry-run — rien modifie. Relancez avec --yes pour appliquer.'))
            return

        with transaction.atomic():
            for student, inscr_amount, scol_amount in plan:
                from apps.payments.models import CinetPayTransaction
                # CinetPayTransaction.invoice is on_delete=PROTECT — tonight's
                # extensive CinetPay debugging left dozens of test
                # transactions attached to these invoices, which blocks a
                # plain Invoice.delete() outright.
                CinetPayTransaction.objects.filter(invoice__student=student).delete()
                Payment.objects.filter(invoice__student=student).delete()
                InvoiceItem.objects.filter(invoice__student=student).delete()
                Invoice.objects.filter(student=student).delete()

                academic_year = None
                enrollment = student.enrollments.filter(is_active=True).first()
                if enrollment:
                    academic_year = enrollment.academic_year

                inscr_invoice = Invoice.objects.create(
                    student=student, site=student.site, academic_year=academic_year,
                    due_date=tz.now().date() + timedelta(days=30),
                    notes="Frais d'inscription 2025-2026",
                )
                InvoiceItem.objects.create(
                    invoice=inscr_invoice, fee_type=fee_inscr,
                    description="Frais d'inscription 2025-2026",
                    quantity=1, unit_price=inscr_amount,
                )
                inscr_invoice.refresh_from_db()
                inscr_invoice.save()
                if inscr_invoice.status == 'PAID' and inscr_invoice.balance > 0:
                    inscr_invoice.status = 'PENDING'
                    inscr_invoice.save(update_fields=['status'])

                scol_invoice = Invoice.objects.create(
                    student=student, site=student.site, academic_year=academic_year,
                    due_date=tz.now().date() + timedelta(days=300),
                    notes='Frais de scolarite 2025-2026',
                )
                InvoiceItem.objects.create(
                    invoice=scol_invoice, fee_type=fee_scol,
                    description='Frais de scolarite 2025-2026',
                    quantity=1, unit_price=scol_amount,
                )
                scol_invoice.refresh_from_db()
                scol_invoice.save()
                if scol_invoice.status == 'PAID' and scol_invoice.balance > 0:
                    scol_invoice.status = 'PENDING'
                    scol_invoice.save(update_fields=['status'])

                student.registration_fee_paid = False
                student.total_paid = 0
                student.remaining_balance = inscr_amount + scol_amount
                student.save(update_fields=['registration_fee_paid', 'total_paid', 'remaining_balance'])

        self.stdout.write(self.style.SUCCESS(f'\nOK. {len(plan)} etudiant(s) reinitialise(s) selon le bareme actuel.'))
