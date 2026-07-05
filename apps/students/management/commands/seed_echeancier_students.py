"""
Seed 2 test students (+ their linked parent) enrolled at ESCAM Cocody,
partially paid on both inscription and scolarité, with an échéancier
(Mai + Juin tranches) configured on their barème — for testing the
tuition reminder task (apps.finance.tasks.send_echeancier_reminders).

Usage:
    python manage.py seed_echeancier_students
"""
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Seed ESCAM Cocody test students/parents with a partial-payment échéancier'

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.students.models import Student, Parent, StudentParent
        from apps.core.models import Site, AcademicYear
        from apps.academic.models import Program, Level, Class, Enrollment
        from apps.finance.models import (
            FeeType, PaymentMethod, FeeConfiguration, FeeInstallment,
            Invoice, InvoiceItem, Payment,
        )

        self.stdout.write(self.style.MIGRATE_HEADING('Seeding ESCAM échéancier test data...'))

        with transaction.atomic():
            # ── 1. Site ESCAM Cocody ──────────────────────────────────────────
            site = Site.objects.filter(name__icontains='ESCAM').first()
            if not site:
                site = Site.objects.create(
                    name='ESCAM Cocody', code='ESCAM-COCODY', city='Abidjan',
                )
                self.stdout.write(f'  Cree site: {site.name}')
            else:
                self.stdout.write(f'  Site: {site.name}')

            # ── 2. Annee academique ───────────────────────────────────────────
            academic_year = AcademicYear.objects.filter(is_current=True).first()
            if not academic_year:
                academic_year = AcademicYear.objects.create(
                    name='2025-2026', code='2025-2026',
                    start_date=datetime.date(2025, 9, 1),
                    end_date=datetime.date(2026, 7, 31),
                    is_current=True,
                )
                self.stdout.write(f'  Cree annee: {academic_year.name}')
            else:
                self.stdout.write(f'  Annee: {academic_year.name}')

            # ── 3. Programme + niveau ─────────────────────────────────────────
            program, _ = Program.objects.get_or_create(
                code='ESCAM-BTSGESCOM', site=site,
                defaults={'name': 'BTS Gestion Commerciale', 'duration_years': 2},
            )
            level, _ = Level.objects.get_or_create(
                program=program, code='L1BTSGESCOM',
                defaults={'name': '1ère année BTS Gestion Commerciale', 'order': 1},
            )
            self.stdout.write(f'  Filiere/Niveau: {program.name} / {level.name}')

            # ── 4. Classe ──────────────────────────────────────────────────────
            class_obj, _ = Class.objects.get_or_create(
                level=level, site=site, academic_year=academic_year,
                code='L1BTSGESCOM-2526',
                defaults={'name': '1ère année BTS Gestion Commerciale', 'max_students': 40},
            )
            self.stdout.write(f'  Classe: {class_obj.name}')

            # ── 5. Baremes — inscription et scolarite sont 2 lignes separees ──
            # (l'echeancier ne s'applique qu'a la scolarite ; l'inscription se
            # paie toujours integralement, jamais en tranches)
            reg_config, reg_created = FeeConfiguration.objects.get_or_create(
                site=site, program=program, level=level, academic_year=academic_year,
                modality='PRESENTIEL', affectation_status='AFFECTE', fee_category='INSCRIPTION',
                defaults={'amount': 150000, 'label': '1ère année BTS Gestion Commerciale', 'is_active': True},
            )
            fee_config, fc_created = FeeConfiguration.objects.get_or_create(
                site=site, program=program, level=level, academic_year=academic_year,
                modality='PRESENTIEL', affectation_status='AFFECTE', fee_category='SCOLARITE',
                defaults={'amount': 500000, 'label': '1ère année BTS Gestion Commerciale', 'is_active': True},
            )
            self.stdout.write(f'  Bareme inscription: {reg_config} ({"cree" if reg_created else "existe"})')
            self.stdout.write(f'  Bareme scolarite: {fee_config} ({"cree" if fc_created else "existe"})')

            # ── 6. Echeancier (tranches Mai + Juin) — sur le bareme SCOLARITE ──
            mai, mai_created = FeeInstallment.objects.get_or_create(
                fee_configuration=fee_config, label='Mai',
                defaults={'due_date': datetime.date(2026, 5, 25), 'amount': 250000, 'order': 0},
            )
            juin, juin_created = FeeInstallment.objects.get_or_create(
                fee_configuration=fee_config, label='Juin',
                defaults={'due_date': datetime.date(2026, 6, 25), 'amount': 150000, 'order': 1},
            )
            self.stdout.write(
                f'  Echeance Mai: {mai.amount} FCFA / {mai.due_date} ({"creee" if mai_created else "existe"})'
            )
            self.stdout.write(
                f'  Echeance Juin: {juin.amount} FCFA / {juin.due_date} ({"creee" if juin_created else "existe"})'
            )

            # ── 7. FeeTypes (codes canoniques utilises par prepare-invoices/
            # recalculate_invoices_for_fee_config) + moyen de paiement ─────────
            fee_inscr, _ = FeeType.objects.get_or_create(
                code='INSCRIPTION', defaults={'name': "Frais d'inscription", 'default_amount': 150000},
            )
            fee_scol, _ = FeeType.objects.get_or_create(
                code='SCOLARITE', defaults={'name': 'Frais de scolarite', 'default_amount': 500000, 'is_recurring': True},
            )
            pay_method, _ = PaymentMethod.objects.get_or_create(
                code='ESPECES', defaults={'name': 'Especes', 'is_online': False},
            )
            admin_user = User.objects.filter(is_staff=True).first() or User.objects.filter(user_type='ADMIN').first()

            # ── 8. Etudiants + parents (soldes partiels — inscription ET scolarite) ──
            students_data = [
                {
                    'email': 'fatou.bamba@escam-test.ci', 'first_name': 'Fatou', 'last_name': 'Bamba',
                    'phone': '+225 07 12 34 56', 'gender': 'F',
                    'birth_date': datetime.date(2004, 2, 10), 'birth_place': 'Abidjan',
                    'inscr_paid': 50000, 'scol_paid': 100000,
                    'parent_email': 'aya.bamba@escam-test.ci', 'parent_first': 'Aya', 'parent_last': 'Bamba',
                    'parent_relation': 'MOTHER',
                },
                {
                    'email': 'ibrahim.coulibaly@escam-test.ci', 'first_name': 'Ibrahim', 'last_name': 'Coulibaly',
                    'phone': '+225 05 98 76 54', 'gender': 'M',
                    'birth_date': datetime.date(2003, 11, 3), 'birth_place': 'Bouake',
                    'inscr_paid': 75000, 'scol_paid': 150000,
                    'parent_email': 'salif.coulibaly@escam-test.ci', 'parent_first': 'Salif', 'parent_last': 'Coulibaly',
                    'parent_relation': 'FATHER',
                },
            ]

            for data in students_data:
                self.stdout.write(f"\n  -- Etudiant: {data['first_name']} {data['last_name']} --")

                # User + profil etudiant
                user, created = User.objects.get_or_create(
                    email=data['email'], defaults={'user_type': 'STUDENT'},
                )
                user.first_name = data['first_name']
                user.last_name = data['last_name']
                user.phone = data['phone']
                user.user_type = 'STUDENT'
                user.site = site
                user.is_active = True
                user.set_password('campus123')
                user.save()

                student, s_created = Student.objects.get_or_create(
                    user=user,
                    defaults={
                        'site': site, 'gender': data['gender'],
                        'birth_date': data['birth_date'], 'birth_place': data['birth_place'],
                        'nationality': 'Ivoirienne', 'status': 'ACTIVE',
                        'modality': 'PRESENTIEL', 'affectation_status': 'AFFECTE',
                        'admission_date': datetime.date(2025, 9, 1),
                        'registration_fee': 150000, 'registration_fee_paid': False,
                        'tuition_fee': 500000,
                        'total_paid': data['inscr_paid'] + data['scol_paid'],
                        'remaining_balance': 650000 - (data['inscr_paid'] + data['scol_paid']),
                    },
                )
                if not s_created:
                    student.site = site
                    student.modality = 'PRESENTIEL'
                    student.affectation_status = 'AFFECTE'
                    student.status = 'ACTIVE'
                    student.registration_fee_paid = False
                    student.save()
                self.stdout.write(f'    Student: #{student.matricule} ({"cree" if s_created else "existe"})')

                # Inscription en classe
                Enrollment.objects.get_or_create(
                    student=student, academic_year=academic_year,
                    defaults={'class_obj': class_obj, 'status': 'ENROLLED', 'is_active': True},
                )

                # Facture d'inscription (partiellement soldee)
                inscr_invoice, inv_created = Invoice.objects.get_or_create(
                    student=student, site=site, academic_year=academic_year,
                    notes="Frais d'inscription 2025-2026",
                    defaults={'due_date': datetime.date(2025, 10, 31), 'status': 'PARTIAL', 'created_by': admin_user},
                )
                if inv_created:
                    InvoiceItem.objects.create(
                        invoice=inscr_invoice, fee_type=fee_inscr,
                        description="Frais d'inscription 2025-2026",
                        quantity=1, unit_price=150000, total=150000,
                    )
                    inscr_invoice.amount_paid = data['inscr_paid']
                    inscr_invoice.save()
                    inscr_invoice.refresh_from_db()
                    Payment.objects.create(
                        payment_number=f"PAY-{student.matricule}-INSCR",
                        invoice=inscr_invoice, payment_method=pay_method,
                        amount=data['inscr_paid'], status='SUCCESS',
                        reference='RECU-INSCR-001', notes='Acompte inscription',
                        received_by=admin_user,
                    )
                self.stdout.write(
                    f'    Inscription: {data["inscr_paid"]:,} / 150 000 FCFA payes'.replace(',', ' ')
                )

                # Facture de scolarite (partiellement soldee)
                scol_invoice, inv_created = Invoice.objects.get_or_create(
                    student=student, site=site, academic_year=academic_year,
                    notes='Frais de scolarite 2025-2026',
                    defaults={'due_date': datetime.date(2026, 6, 30), 'status': 'PARTIAL', 'created_by': admin_user},
                )
                if inv_created:
                    InvoiceItem.objects.create(
                        invoice=scol_invoice, fee_type=fee_scol,
                        description='Frais de scolarite 2025-2026',
                        quantity=1, unit_price=500000, total=500000,
                    )
                    scol_invoice.amount_paid = data['scol_paid']
                    scol_invoice.save()
                    scol_invoice.refresh_from_db()
                    Payment.objects.create(
                        payment_number=f"PAY-{student.matricule}-SCOL",
                        invoice=scol_invoice, payment_method=pay_method,
                        amount=data['scol_paid'], status='SUCCESS',
                        reference='RECU-SCOL-001', notes='Acompte scolarite',
                        received_by=admin_user,
                    )
                self.stdout.write(
                    f'    Scolarite: {data["scol_paid"]:,} / 500 000 FCFA payes'.replace(',', ' ')
                )

                # Parent + lien
                parent_user, _ = User.objects.get_or_create(
                    email=data['parent_email'], defaults={'user_type': 'PARENT'},
                )
                parent_user.first_name = data['parent_first']
                parent_user.last_name = data['parent_last']
                parent_user.user_type = 'PARENT'
                parent_user.site = site
                parent_user.is_active = True
                parent_user.set_password('campus123')
                parent_user.save()

                parent, _ = Parent.objects.get_or_create(
                    user=parent_user, defaults={'relationship': data['parent_relation']},
                )
                StudentParent.objects.get_or_create(
                    student=student, parent=parent,
                    defaults={'is_primary': True, 'can_pickup': True, 'receives_notifications': True},
                )
                self.stdout.write(f'    Parent: {parent_user.full_name} ({parent_user.email})')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('OK Etudiants ESCAM + echeancier de test generes!'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Comptes (mot de passe: campus123):'))
        for data in students_data:
            self.stdout.write(f"  Etudiant: {data['email']}")
            self.stdout.write(f"  Parent:   {data['parent_email']}")
        self.stdout.write('')
