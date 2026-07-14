import calendar
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import ExtractMonth, ExtractWeekDay
from django.utils import timezone
from datetime import timedelta

MONTHS_FR = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
# ExtractWeekDay is DB-normalized to 1=Sunday..7=Saturday regardless of backend.
WEEKDAY_TO_LABEL = {2: 'Lun', 3: 'Mar', 4: 'Mer', 5: 'Jeu', 6: 'Ven', 7: 'Sam', 1: 'Dim'}


def _period_to_range(period, today):
    """Mirrors the frontend's getPeriodDates(): 'week', 'all', or a month number '1'..'12'."""
    if period == 'week':
        start = today - timedelta(days=today.weekday())
        return start, today
    if period == 'all':
        return today.replace(month=1, day=1), today.replace(month=12, day=31)
    try:
        m = int(period)
        if not 1 <= m <= 12:
            raise ValueError
    except (TypeError, ValueError):
        start = today - timedelta(days=today.weekday())
        return start, today
    start = today.replace(month=m, day=1)
    last_day = calendar.monthrange(today.year, m)[1]
    return start, today.replace(month=m, day=last_day)


class DashboardView(APIView):
    def get(self, request):
        site_id = request.query_params.get('site_id')
        
        from apps.students.models import Student
        from apps.academic.models import TeacherProfile, Class, Enrollment
        from apps.finance.models import Invoice, Payment
        from apps.attendance.models import AttendanceRecord
        
        students = Student.objects.filter(is_active=True, status='ACTIVE')
        teachers = TeacherProfile.objects.filter(is_active=True)
        classes = Class.objects.filter(is_active=True)
        
        if site_id:
            students = students.filter(site_id=site_id)
            classes = classes.filter(site_id=site_id)
        
        today = timezone.now().date()
        this_month_start = today.replace(day=1)
        
        invoices = Invoice.objects.filter(is_active=True)
        payments = Payment.objects.filter(status='SUCCESS')
        
        if site_id:
            invoices = invoices.filter(site_id=site_id)
            payments = payments.filter(invoice__site_id=site_id)
        
        total_invoiced = invoices.aggregate(total=Sum('total'))['total'] or 0
        total_paid = payments.aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_payments = payments.filter(
            payment_date__gte=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        attendance_today = AttendanceRecord.objects.filter(
            attendance_session__date=today
        )
        if site_id:
            attendance_today = attendance_today.filter(
                attendance_session__session__class_obj__site_id=site_id
            )
        
        present_today = attendance_today.filter(status='PRESENT').count()
        absent_today = attendance_today.filter(status='ABSENT').count()
        
        return Response({
            'overview': {
                'total_students': students.count(),
                'total_teachers': teachers.count(),
                'total_classes': classes.count(),
                'active_enrollments': Enrollment.objects.filter(is_active=True, status='ENROLLED').count()
            },
            'finance': {
                'total_invoiced': total_invoiced,
                'total_paid': total_paid,
                'outstanding': total_invoiced - total_paid,
                'monthly_payments': monthly_payments
            },
            'attendance_today': {
                'present': present_today,
                'absent': absent_today,
                'rate': round(present_today / (present_today + absent_today) * 100, 2) if (present_today + absent_today) > 0 else 0
            }
        })


class FinanceReportView(APIView):
    def get(self, request):
        site_id = request.query_params.get('site_id')
        period = request.query_params.get('period', 'month')
        
        from apps.finance.models import Invoice, Payment
        from apps.core.models import AcademicYear
        
        today = timezone.now().date()
        
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today.replace(day=1)
        elif period == 'year':
            current_year = AcademicYear.get_current()
            start_date = current_year.start_date if current_year else today.replace(month=1, day=1)
        else:
            start_date = today - timedelta(days=30)
        
        invoices = Invoice.objects.filter(issue_date__gte=start_date)
        payments = Payment.objects.filter(payment_date__date__gte=start_date, status='SUCCESS')
        
        if site_id:
            invoices = invoices.filter(site_id=site_id)
            payments = payments.filter(invoice__site_id=site_id)
        
        invoices_by_status = invoices.values('status').annotate(
            count=Count('id'),
            total=Sum('total')
        )
        
        payments_by_method = payments.values('payment_method__name').annotate(
            count=Count('id'),
            total=Sum('amount')
        )
        
        return Response({
            'period': {'start': start_date, 'end': today},
            'invoices': {
                'count': invoices.count(),
                'total': invoices.aggregate(total=Sum('total'))['total'] or 0,
                'by_status': list(invoices_by_status)
            },
            'payments': {
                'count': payments.count(),
                'total': payments.aggregate(total=Sum('amount'))['total'] or 0,
                'by_method': list(payments_by_method)
            }
        })


class AttendanceReportView(APIView):
    def get(self, request):
        site_id = request.query_params.get('site_id')
        class_id = request.query_params.get('class_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        from apps.attendance.models import AttendanceRecord, AttendanceSession
        
        records = AttendanceRecord.objects.filter(is_active=True)
        
        if site_id:
            records = records.filter(
                attendance_session__session__class_obj__site_id=site_id
            )
        
        if class_id:
            records = records.filter(
                attendance_session__session__class_obj_id=class_id
            )
        
        if start_date:
            records = records.filter(attendance_session__date__gte=start_date)
        
        if end_date:
            records = records.filter(attendance_session__date__lte=end_date)
        
        by_status = records.values('status').annotate(count=Count('id'))
        
        total = records.count()
        present = records.filter(status='PRESENT').count()
        
        return Response({
            'total_records': total,
            'by_status': list(by_status),
            'attendance_rate': round(present / total * 100, 2) if total > 0 else 0
        })


class StudentReportView(APIView):
    def get(self, request):
        site_id = request.query_params.get('site_id')

        from apps.students.models import Student
        from apps.academic.models import Enrollment

        students = Student.objects.filter(is_active=True)

        if site_id:
            students = students.filter(site_id=site_id)

        by_status = students.values('status').annotate(count=Count('id'))
        by_gender = students.values('gender').annotate(count=Count('id'))

        enrollments = Enrollment.objects.filter(is_active=True)
        if site_id:
            enrollments = enrollments.filter(class_obj__site_id=site_id)

        by_class = enrollments.values(
            'class_obj__name', 'class_obj__code'
        ).annotate(count=Count('id'))

        return Response({
            'total_students': students.count(),
            'by_status': list(by_status),
            'by_gender': list(by_gender),
            'by_class': list(by_class)
        })


class GradesReportView(APIView):
    """School-wide success rate / grade distribution, for the admin
    Statistiques page — mirrors StudentReportView/AttendanceReportView."""
    def get(self, request):
        site_id = request.query_params.get('site_id')
        academic_year_id = request.query_params.get('academic_year')
        semester_id = request.query_params.get('semester')

        from apps.grades.models import ReportCard

        cards = ReportCard.objects.all()

        if site_id:
            cards = cards.filter(class_group__site_id=site_id)
        if academic_year_id:
            cards = cards.filter(semester__academic_year_id=academic_year_id)
        if semester_id:
            cards = cards.filter(semester_id=semester_id)

        by_status = cards.values('status').annotate(count=Count('id'))
        by_class = cards.values(
            'class_group__name', 'class_group__code'
        ).annotate(count=Count('id'), avg_score=Avg('average'))

        total = cards.count()
        passed = cards.filter(status__in=['PASS', 'HONORS', 'CONDITIONAL']).count()
        avg_score = cards.aggregate(avg=Avg('average'))['avg'] or 0

        return Response({
            'total_report_cards': total,
            'passed': passed,
            'success_rate': round(passed / total * 100, 1) if total else 0,
            'average_score': round(float(avg_score), 2),
            'by_status': list(by_status),
            'by_class': list(by_class),
        })


class ElearningReportView(APIView):
    """Platform-wide e-learning stats (all quizzes + all lessons combined),
    for the admin Statistiques page — mirrors the other apps/reports views."""
    def get(self, request):
        site_id = request.query_params.get('site_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        from apps.elearning.models import Quiz, QuizAttempt, Lesson, LessonProgress

        quizzes = Quiz.objects.filter(is_active=True)
        attempts = QuizAttempt.objects.filter(submitted_at__isnull=False)
        lessons = Lesson.objects.filter(is_active=True)
        progress = LessonProgress.objects.filter(is_active=True)

        if site_id:
            quizzes = quizzes.filter(class_obj__site_id=site_id)
            attempts = attempts.filter(quiz__class_obj__site_id=site_id)
            lessons = lessons.filter(class_obj__site_id=site_id)
            progress = progress.filter(lesson__class_obj__site_id=site_id)
        if start_date:
            attempts = attempts.filter(submitted_at__date__gte=start_date)
        if end_date:
            attempts = attempts.filter(submitted_at__date__lte=end_date)

        total_attempts = attempts.count()
        passed_attempts = attempts.filter(is_passed=True).count()
        avg_score = attempts.aggregate(avg=Avg('percent'))['avg'] or 0

        total_lessons = lessons.count()
        completed_progress = progress.filter(lesson__in=lessons, is_completed=True).count()
        total_progress = progress.filter(lesson__in=lessons).count()

        return Response({
            'quizzes': {
                'total_quizzes': quizzes.count(),
                'total_attempts': total_attempts,
                'passed': passed_attempts,
                'pass_rate': round(passed_attempts / total_attempts * 100, 1) if total_attempts else 0,
                'average_score': round(float(avg_score), 1),
            },
            'lessons': {
                'total_lessons': total_lessons,
                'total_progress_records': total_progress,
                'completed': completed_progress,
                'completion_rate': round(completed_progress / total_progress * 100, 1) if total_progress else 0,
            },
        })


class RevenueChartView(APIView):
    """Monthly revenue + distinct paying students, Jan through the current
    month of the selected year — feeds the admin Dashboard revenue chart."""
    def get(self, request):
        site_id = request.query_params.get('site_id')
        today = timezone.now().date()
        year = int(request.query_params.get('year') or today.year)

        from apps.finance.models import Payment

        payments = Payment.objects.filter(status='SUCCESS', payment_date__year=year)
        if site_id:
            payments = payments.filter(invoice__site_id=site_id)

        by_month = {
            row['m']: row
            for row in payments.annotate(m=ExtractMonth('payment_date')).values('m').annotate(
                revenue=Sum('amount'),
                students=Count('invoice__student', distinct=True),
            )
        }

        last_month = today.month if year == today.year else 12
        data = [
            {
                'month': MONTHS_FR[m - 1],
                'revenue': float(by_month[m]['revenue']) if m in by_month else 0,
                'students': by_month[m]['students'] if m in by_month else 0,
            }
            for m in range(1, last_month + 1)
        ]
        return Response(data)


class AttendanceChartView(APIView):
    """Present/absent counts by weekday over the selected period — feeds the
    admin Dashboard attendance chart."""
    def get(self, request):
        site_id = request.query_params.get('site_id')
        period = request.query_params.get('period', 'week')
        today = timezone.now().date()
        start, end = _period_to_range(period, today)

        from apps.attendance.models import AttendanceRecord

        records = AttendanceRecord.objects.filter(
            attendance_session__date__gte=start,
            attendance_session__date__lte=end,
        )
        if site_id:
            records = records.filter(attendance_session__session__class_obj__site_id=site_id)

        by_day = {
            row['wd']: row
            for row in records.annotate(wd=ExtractWeekDay('attendance_session__date')).values('wd').annotate(
                present=Count('id', filter=Q(status='PRESENT')),
                absent=Count('id', filter=Q(status='ABSENT')),
            )
        }

        # Mon(2)..Sat(7) then Sun(1), so the week reads left-to-right starting Monday.
        ordered_weekdays = [2, 3, 4, 5, 6, 7, 1]
        data = [
            {
                'day': WEEKDAY_TO_LABEL[wd],
                'present': by_day[wd]['present'] if wd in by_day else 0,
                'absent': by_day[wd]['absent'] if wd in by_day else 0,
            }
            for wd in ordered_weekdays
            if wd in by_day
        ]
        return Response(data)
