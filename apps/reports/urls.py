from django.urls import path
from .views import (
    DashboardView, FinanceReportView, AttendanceReportView, StudentReportView,
    GradesReportView, ElearningReportView,
)

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('reports/finance/', FinanceReportView.as_view(), name='finance-report'),
    path('reports/attendance/', AttendanceReportView.as_view(), name='attendance-report'),
    path('reports/students/', StudentReportView.as_view(), name='student-report'),
    path('reports/grades/', GradesReportView.as_view(), name='grades-report'),
    path('reports/elearning/', ElearningReportView.as_view(), name='elearning-report'),
]
