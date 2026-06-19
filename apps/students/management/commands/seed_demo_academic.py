"""
Management command to seed demo academic data for angealain@gmail.com.
Inserts invoices, attendance records, grades, and a published report card.

Usage:
    python manage.py seed_demo_academic
"""
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Seed demo invoices, absences, grades and bulletins for angealain@gmail.com'

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.students.models import Student
        from apps.core.models import AcademicYear
        from apps.academic.models import Class, Subject, Semester, Session
        from apps.finance.models import FeeType, Invoice, InvoiceItem, PaymentMethod, Payment
        from apps.attendance.models import AttendanceSession, AttendanceRecord
        from apps.grades.models import GradeCategory, Grade, ReportCard

        self.stdout.write(self.style.MIGRATE_HEADING('Seeding demo academic data for angealain@gmail.com...'))

        with transaction.atomic():
            # ── 0. Get student ───────────────────────────────────────────────
            try:
                student_user = User.objects.get(email='angealain@gmail.com')
                student = Student.objects.get(user=student_user)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR('User angealain@gmail.com not found. Run seed_demo_students first.'))
                return
            except Student.DoesNotExist:
                self.stdout.write(self.style.ERROR('Student profile not found. Run seed_demo_students first.'))
                return

            self.stdout.write(f'  Student: {student_user.full_name} (#{student.matricule})')

            site = student.site
            academic_year = AcademicYear.objects.filter(is_current=True).first()
            if not academic_year:
                self.stdout.write(self.style.ERROR('No current academic year found.'))
                return

            enrollment = student.enrollments.select_related('class_obj').order_by('-created_at').first()
            if not enrollment:
                self.stdout.write(self.style.ERROR('No enrollment found. Run seed_demo_students first.'))
                return
            class_obj = enrollment.class_obj
            self.stdout.write(f'  Class: {class_obj.name}')

            # ── 1. Fee types ─────────────────────────────────────────────────
            inscription_ft, _ = FeeType.objects.get_or_create(
                code='INSCRIPTION',
                defaults={'name': "Frais d'inscription", 'default_amount': 150000, 'is_recurring': False}
            )
            scolarite_ft, _ = FeeType.objects.get_or_create(
                code='SCOLARITE',
                defaults={'name': 'Frais de scolarite', 'default_amount': 1000000, 'is_recurring': True}
            )
            self.stdout.write('  Fee types ready')

            # ── 2. Payment methods ───────────────────────────────────────────
            cash_pm, _ = PaymentMethod.objects.get_or_create(
                code='CASH',
                defaults={'name': 'Especes', 'is_online': False}
            )
            mobile_pm, _ = PaymentMethod.objects.get_or_create(
                code='MOBILE_MONEY',
                defaults={'name': 'Mobile Money', 'is_online': True}
            )
            self.stdout.write('  Payment methods ready')

            # ── 3. Invoices ──────────────────────────────────────────────────
            # Invoice 1: Inscription 150 000 FCFA – PAID
            inv1 = Invoice.objects.filter(
                student=student, academic_year=academic_year, notes='Frais inscription 2025-2026'
            ).first()
            if not inv1:
                inv1 = Invoice.objects.create(
                    student=student, site=site, academic_year=academic_year,
                    due_date=datetime.date(2025, 9, 30),
                    notes='Frais inscription 2025-2026',
                )
                InvoiceItem.objects.create(
                    invoice=inv1, fee_type=inscription_ft,
                    description="Frais d'inscription 2025-2026",
                    quantity=1, unit_price=150000, total=150000,
                )
                inv1.amount_paid = 150000
                inv1.save()
                Payment.objects.create(
                    invoice=inv1, payment_method=cash_pm,
                    amount=150000, status='SUCCESS',
                    reference='REF-INSC-001',
                    notes='Paiement frais inscription',
                )
                self.stdout.write(f'  Created invoice {inv1.invoice_number}: 150 000 FCFA (PAID)')
            else:
                self.stdout.write(f'  Invoice already exists: {inv1.invoice_number}')

            # Invoice 2: Scolarite S1 800 000 FCFA – PAID
            inv2 = Invoice.objects.filter(
                student=student, academic_year=academic_year, notes='Scolarite Semestre 1 2025-2026'
            ).first()
            if not inv2:
                inv2 = Invoice.objects.create(
                    student=student, site=site, academic_year=academic_year,
                    due_date=datetime.date(2025, 11, 30),
                    notes='Scolarite Semestre 1 2025-2026',
                )
                InvoiceItem.objects.create(
                    invoice=inv2, fee_type=scolarite_ft,
                    description='Scolarite - Semestre 1 2025-2026',
                    quantity=1, unit_price=800000, total=800000,
                )
                inv2.amount_paid = 800000
                inv2.save()
                Payment.objects.create(
                    invoice=inv2, payment_method=mobile_pm,
                    amount=800000, status='SUCCESS',
                    reference='REF-SCOL-S1-001',
                    notes='Paiement scolarite S1',
                )
                self.stdout.write(f'  Created invoice {inv2.invoice_number}: 800 000 FCFA (PAID)')
            else:
                self.stdout.write(f'  Invoice already exists: {inv2.invoice_number}')

            # Invoice 3: Scolarite S2 1 050 000 FCFA – PARTIAL (600k paid, 450k remaining)
            inv3 = Invoice.objects.filter(
                student=student, academic_year=academic_year, notes='Scolarite Semestre 2 2025-2026'
            ).first()
            if not inv3:
                inv3 = Invoice.objects.create(
                    student=student, site=site, academic_year=academic_year,
                    due_date=datetime.date(2026, 4, 30),
                    notes='Scolarite Semestre 2 2025-2026',
                )
                InvoiceItem.objects.create(
                    invoice=inv3, fee_type=scolarite_ft,
                    description='Scolarite - Semestre 2 2025-2026',
                    quantity=1, unit_price=1050000, total=1050000,
                )
                inv3.amount_paid = 600000
                inv3.save()
                Payment.objects.create(
                    invoice=inv3, payment_method=cash_pm,
                    amount=600000, status='SUCCESS',
                    reference='REF-SCOL-S2-001',
                    notes='Premier versement scolarite S2',
                )
                self.stdout.write(f'  Created invoice {inv3.invoice_number}: 1 050 000 FCFA (PARTIAL - 600k paid)')
            else:
                self.stdout.write(f'  Invoice already exists: {inv3.invoice_number}')

            # ── 4. Subjects ──────────────────────────────────────────────────
            subjects_data = [
                ('MATHS-L1', 'Mathematiques', 3.0),
                ('ALGO-L1', 'Algorithmique et Programmation', 3.0),
                ('ANGLAIS-L1', 'Anglais Technique', 2.0),
                ('RESEAUX-L1', 'Reseaux Informatiques', 2.0),
                ('BD-L1', 'Bases de Donnees', 3.0),
            ]
            subjects = {}
            for code, name, coeff in subjects_data:
                subj, _ = Subject.objects.get_or_create(
                    code=code,
                    defaults={'name': name, 'coefficient': coeff, 'hours_per_week': 2}
                )
                subjects[code] = subj
            self.stdout.write(f'  Subjects ready: {len(subjects)}')

            # ── 5. Schedule sessions ─────────────────────────────────────────
            sessions_schedule = [
                ('MATHS-L1', 0, datetime.time(8, 0), datetime.time(10, 0)),
                ('ALGO-L1', 1, datetime.time(10, 0), datetime.time(12, 0)),
                ('ANGLAIS-L1', 2, datetime.time(14, 0), datetime.time(16, 0)),
                ('RESEAUX-L1', 3, datetime.time(8, 0), datetime.time(10, 0)),
                ('BD-L1', 4, datetime.time(10, 0), datetime.time(12, 0)),
            ]
            sessions = {}
            for subj_code, day, start, end in sessions_schedule:
                sess, _ = Session.objects.get_or_create(
                    class_obj=class_obj,
                    subject=subjects[subj_code],
                    day_of_week=day,
                    defaults={'start_time': start, 'end_time': end, 'is_recurring': True}
                )
                sessions[subj_code] = sess
            self.stdout.write(f'  Schedule sessions ready: {len(sessions)}')

            # ── 6. Semester ──────────────────────────────────────────────────
            semester, _ = Semester.objects.get_or_create(
                academic_year=academic_year,
                name='S1',
                defaults={
                    'label': 'Semestre 1 2025-2026',
                    'start_date': datetime.date(2025, 9, 1),
                    'end_date': datetime.date(2026, 1, 31),
                    'is_current': True,
                }
            )
            self.stdout.write(f'  Semester: {semester}')

            # ── 7. Attendance records ────────────────────────────────────────
            # 15 records: 11 PRESENT, 2 ABSENT, 1 LATE, 1 EXCUSED
            attendance_data = [
                ('MATHS-L1',    datetime.date(2025, 9,  8), 'PRESENT'),
                ('ALGO-L1',     datetime.date(2025, 9,  9), 'PRESENT'),
                ('ANGLAIS-L1',  datetime.date(2025, 9, 10), 'PRESENT'),
                ('RESEAUX-L1',  datetime.date(2025, 9, 11), 'PRESENT'),
                ('BD-L1',       datetime.date(2025, 9, 12), 'PRESENT'),
                ('MATHS-L1',    datetime.date(2025, 9, 15), 'ABSENT'),
                ('ALGO-L1',     datetime.date(2025, 9, 16), 'PRESENT'),
                ('ANGLAIS-L1',  datetime.date(2025, 9, 17), 'LATE'),
                ('RESEAUX-L1',  datetime.date(2025, 9, 18), 'PRESENT'),
                ('BD-L1',       datetime.date(2025, 9, 19), 'PRESENT'),
                ('MATHS-L1',    datetime.date(2025, 9, 22), 'PRESENT'),
                ('ALGO-L1',     datetime.date(2025, 9, 23), 'ABSENT'),
                ('ANGLAIS-L1',  datetime.date(2025, 9, 24), 'EXCUSED'),
                ('RESEAUX-L1',  datetime.date(2025, 9, 25), 'PRESENT'),
                ('BD-L1',       datetime.date(2025, 9, 26), 'PRESENT'),
            ]

            att_created = 0
            for subj_code, date, status in attendance_data:
                att_session, _ = AttendanceSession.objects.get_or_create(
                    session=sessions[subj_code],
                    date=date,
                    defaults={'status': 'CLOSED'}
                )
                _, rec_created = AttendanceRecord.objects.get_or_create(
                    attendance_session=att_session,
                    student=student,
                    defaults={'status': status, 'check_in_method': 'MANUAL'}
                )
                if rec_created:
                    att_created += 1

            self.stdout.write(f'  Attendance records created: {att_created} (total: {len(attendance_data)})')

            # ── 8. Grade categories ──────────────────────────────────────────
            cat_devoir, _ = GradeCategory.objects.get_or_create(
                code='DEVOIR',
                defaults={'name': 'Devoir sur table', 'weight': 0.4}
            )
            cat_exam, _ = GradeCategory.objects.get_or_create(
                code='EXAMEN',
                defaults={'name': 'Examen final', 'weight': 0.6}
            )

            # ── 9. Grades ────────────────────────────────────────────────────
            # Devoir (coeff 0.4) + Examen (coeff 0.6) per subject
            grades_data = [
                ('MATHS-L1',   cat_devoir, 14.5, datetime.date(2025, 10, 15)),
                ('MATHS-L1',   cat_exam,   13.0, datetime.date(2026,  1, 20)),
                ('ALGO-L1',    cat_devoir, 16.0, datetime.date(2025, 10, 16)),
                ('ALGO-L1',    cat_exam,   15.5, datetime.date(2026,  1, 21)),
                ('ANGLAIS-L1', cat_devoir, 12.0, datetime.date(2025, 10, 17)),
                ('ANGLAIS-L1', cat_exam,   11.5, datetime.date(2026,  1, 22)),
                ('RESEAUX-L1', cat_devoir, 15.0, datetime.date(2025, 10, 20)),
                ('RESEAUX-L1', cat_exam,   14.0, datetime.date(2026,  1, 23)),
                ('BD-L1',      cat_devoir, 17.0, datetime.date(2025, 10, 21)),
                ('BD-L1',      cat_exam,   16.5, datetime.date(2026,  1, 24)),
            ]

            grades_created = 0
            for subj_code, category, score, date in grades_data:
                _, g_created = Grade.objects.get_or_create(
                    student=student,
                    subject=subjects[subj_code],
                    category=category,
                    semester=semester,
                    defaults={
                        'class_group': class_obj,
                        'score': score,
                        'max_score': 20,
                        'date': date,
                    }
                )
                if g_created:
                    grades_created += 1

            self.stdout.write(f'  Grades created: {grades_created} (total: {len(grades_data)})')

            # ── 10. Published report card ────────────────────────────────────
            # Weighted averages per subject (devoir*0.4 + examen*0.6):
            #   MATHS:   14.5*0.4 + 13.0*0.6 = 5.80 + 7.80 = 13.60
            #   ALGO:    16.0*0.4 + 15.5*0.6 = 6.40 + 9.30 = 15.70
            #   ANGLAIS: 12.0*0.4 + 11.5*0.6 = 4.80 + 6.90 = 11.70
            #   RESEAUX: 15.0*0.4 + 14.0*0.6 = 6.00 + 8.40 = 14.40
            #   BD:      17.0*0.4 + 16.5*0.6 = 6.80 + 9.90 = 16.70
            #   General average: (13.60+15.70+11.70+14.40+16.70)/5 = 14.42
            report_card, rc_created = ReportCard.objects.get_or_create(
                student=student,
                class_group=class_obj,
                semester=semester,
                defaults={
                    'average': 14.42,
                    'rank': 3,
                    'total_students': 28,
                    'status': 'PASS',
                    'teacher_comment': 'Bon semestre, continuer dans cette voie.',
                    'principal_comment': 'Resultats satisfaisants. Encouragements.',
                    'is_published': True,
                }
            )
            if rc_created:
                self.stdout.write(f'  Report card created: avg=14.42/20, rank=3/28, published')
            else:
                if not report_card.is_published:
                    report_card.is_published = True
                    report_card.save()
                self.stdout.write(f'  Report card already exists: avg={report_card.average}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Demo academic data seeded successfully!'))
        self.stdout.write('')
        self.stdout.write('  Summary for angealain@gmail.com:')
        self.stdout.write('    Invoices  : 3 (inscription PAID + scolarite S1 PAID + scolarite S2 PARTIAL)')
        self.stdout.write('    Attendance: 15 records (11 PRESENT, 2 ABSENT, 1 LATE, 1 EXCUSED)')
        self.stdout.write('    Grades    : 10 notes across 5 subjects (devoir + examen each)')
        self.stdout.write('    Bulletin  : 1 published (avg 14.42/20, rank 3/28)')
        self.stdout.write('')
