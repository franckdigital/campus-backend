from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta


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
