"""
Management command to seed 2 test students with invoices and payments.

Usage:
    python manage.py seed_test_finance
"""
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed 2 test students with invoices and payments for PDF testing'

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.students.models import Student
        from apps.core.models import Site, AcademicYear
        from apps.finance.models import FeeType, PaymentMethod, Invoice, InvoiceItem, Payment

        self.stdout.write(self.style.MIGRATE_HEADING('Seeding test finance data...'))

        with transaction.atomic():
            # ── 1. Site ──────────────────────────────────────────────────────
            site = Site.objects.filter(is_active=True).first()
            if not site:
                site = Site.objects.create(
                    name='ITA Marcory',
                    code='ITAMARCORY',
                    city='Abidjan',
                    is_main=True,
                )
                self.stdout.write(f'  Cree site: {site.name}')
            else:
                self.stdout.write(f'  Site: {site.name}')

            # ── 2. Annee academique ───────────────────────────────────────────
            academic_year = AcademicYear.objects.filter(is_current=True).first()
            if not academic_year:
                academic_year = AcademicYear.objects.create(
                    name='2025-2026',
                    code='2025-2026',
                    start_date=datetime.date(2025, 9, 1),
                    end_date=datetime.date(2026, 7, 31),
                    is_current=True,
                )
                self.stdout.write(f'  Cree annee: {academic_year.name}')
            else:
                self.stdout.write(f'  Annee: {academic_year.name}')

            # ── 3. FeeTypes ───────────────────────────────────────────────────
            fee_scol, _ = FeeType.objects.get_or_create(
                code='SCOL',
                defaults={
                    'name': 'Frais de scolarite',
                    'default_amount': 750000,
                    'is_recurring': True,
                }
            )
            fee_inscr, _ = FeeType.objects.get_or_create(
                code='INSCR',
                defaults={
                    'name': "Frais d'inscription",
                    'default_amount': 150000,
                    'is_recurring': False,
                }
            )
            self.stdout.write('  FeeTypes OK')

            # ── 4. PaymentMethod ──────────────────────────────────────────────
            pay_method, _ = PaymentMethod.objects.get_or_create(
                code='ESPECES',
                defaults={
                    'name': 'Especes',
                    'is_online': False,
                }
            )
            self.stdout.write('  PaymentMethod OK')

            # ── 5. Admin user (received_by) ───────────────────────────────────
            admin_user = User.objects.filter(is_staff=True).first()
            if not admin_user:
                admin_user = User.objects.filter(user_type='ADMIN').first()

            # ── 6. Donnees des 2 etudiants ────────────────────────────────────
            students_data = [
                {
                    'email': 'konan.kouassi@ita.ci',
                    'first_name': 'Kouassi',
                    'last_name': 'Konan',
                    'phone': '+225 07 11 22 33',
                    'gender': 'M',
                    'birth_date': datetime.date(2002, 3, 12),
                    'birth_place': 'Yamoussoukro',
                    'city': 'Abidjan',
                    'scol_amount': 750000,
                    'inscr_amount': 150000,
                    'paid_amount': 500000,
                    'tranche': 2,
                },
                {
                    'email': 'amoin.brou@ita.ci',
                    'first_name': 'Amoin',
                    'last_name': 'Brou',
                    'phone': '+225 05 44 55 66',
                    'gender': 'F',
                    'birth_date': datetime.date(2003, 7, 25),
                    'birth_place': 'Abidjan',
                    'city': 'Abidjan',
                    'scol_amount': 750000,
                    'inscr_amount': 150000,
                    'paid_amount': 900000,
                    'tranche': 3,
                },
            ]

            for data in students_data:
                self.stdout.write(f"\n  -- Etudiant: {data['first_name']} {data['last_name']} --")

                # User
                user, created = User.objects.get_or_create(
                    email=data['email'],
                    defaults={'user_type': 'STUDENT'},
                )
                user.first_name = data['first_name']
                user.last_name = data['last_name']
                user.phone = data['phone']
                user.user_type = 'STUDENT'
                user.site = site
                user.is_active = True
                user.set_password('campus123')
                user.save()
                self.stdout.write(f'    User: {user.email} ({"cree" if created else "maj"})')

                # Student profile
                student, created = Student.objects.get_or_create(
                    user=user,
                    defaults={
                        'site': site,
                        'gender': data['gender'],
                        'birth_date': data['birth_date'],
                        'birth_place': data['birth_place'],
                        'nationality': 'Ivoirienne',
                        'city': data['city'],
                        'status': 'ACTIVE',
                        'admission_date': datetime.date(2025, 9, 1),
                        'registration_fee': data['inscr_amount'],
                        'registration_fee_paid': True,
                        'tuition_fee': data['scol_amount'],
                        'total_paid': data['paid_amount'],
                        'remaining_balance': data['scol_amount'] + data['inscr_amount'] - data['paid_amount'],
                    }
                )
                if not created:
                    student.site = site
                    student.status = 'ACTIVE'
                    student.save()
                self.stdout.write(f'    Student: #{student.matricule} ({"cree" if created else "existe"})')

                # Invoice (1 par etudiant)
                total = data['scol_amount'] + data['inscr_amount']
                invoice, inv_created = Invoice.objects.get_or_create(
                    student=student,
                    academic_year=academic_year,
                    defaults={
                        'site': site,
                        'due_date': datetime.date(2025, 12, 31),
                        'status': 'PARTIAL',
                        'notes': 'Facture annee academique 2025-2026',
                        'created_by': admin_user,
                    }
                )

                if inv_created:
                    # Lignes de facture
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        fee_type=fee_scol,
                        description='Frais de scolarite 2025-2026',
                        quantity=1,
                        unit_price=data['scol_amount'],
                        total=data['scol_amount'],
                    )
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        fee_type=fee_inscr,
                        description="Frais d'inscription 2025-2026",
                        quantity=1,
                        unit_price=data['inscr_amount'],
                        total=data['inscr_amount'],
                    )
                    # Mettre a jour les totaux
                    invoice.amount_paid = data['paid_amount']
                    invoice.save()  # recalcule subtotal/total/balance via calculate_totals
                    invoice.refresh_from_db()
                    self.stdout.write(f'    Facture: {invoice.invoice_number} | Total: {invoice.total} | Reste: {invoice.balance}')

                    # Paiements en tranches
                    tranche_amount = data['paid_amount'] // data['tranche']
                    for i in range(1, data['tranche'] + 1):
                        amt = tranche_amount if i < data['tranche'] else data['paid_amount'] - tranche_amount * (data['tranche'] - 1)
                        pay_num = f"PAY-{student.matricule}-T{i}"
                        if not Payment.objects.filter(payment_number=pay_num).exists():
                            Payment.objects.create(
                                payment_number=pay_num,
                                invoice=invoice,
                                payment_method=pay_method,
                                amount=amt,
                                status='SUCCESS',
                                reference=f'RECU-{i:03d}',
                                notes=f'Tranche {i}/{data["tranche"]}',
                                received_by=admin_user,
                            )
                            self.stdout.write(f'    Paiement T{i}: {amt:,} FCFA')
                else:
                    self.stdout.write(f'    Facture existe: {invoice.invoice_number}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('OK Donnees de test generees avec succes!'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Comptes etudiants (mot de passe: campus123):'))
        self.stdout.write('  konan.kouassi@ita.ci')
        self.stdout.write('  amoin.brou@ita.ci')
        self.stdout.write('')
