from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import (
    AttendanceSessionViewSet, AttendanceRecordViewSet,
    AbsenceRequestViewSet, AttendanceOpenView, AttendanceScanView,
    ClassQRView, ClassStudentsView, StudentScanView, AutoMarkAbsentView,
    ClassTodaySessionsView, SessionQRView, PostponeSessionView,
)

router = DefaultRouter()
router.register(r'attendance-sessions', AttendanceSessionViewSet, basename='attendance-session')
router.register(r'attendance-records', AttendanceRecordViewSet, basename='attendance-record')
router.register(r'absence-requests', AbsenceRequestViewSet, basename='absence-request')

urlpatterns = [
    path('attendance/open/',                           AttendanceOpenView.as_view(),         name='attendance-open'),
    path('attendance/scan/',                           AttendanceScanView.as_view(),         name='attendance-scan'),
    path('attendance/class-qr/<uuid:class_id>/',       ClassQRView.as_view(),                name='class-qr'),
    path('attendance/class-students/<uuid:class_id>/', ClassStudentsView.as_view(),          name='class-students'),
    path('attendance/class-sessions-today/<uuid:class_id>/', ClassTodaySessionsView.as_view(), name='class-sessions-today'),
    path('attendance/student-scan/',                   StudentScanView.as_view(),            name='student-scan'),
    path('attendance/auto-mark-absent/',               AutoMarkAbsentView.as_view(),         name='auto-mark-absent'),
    path('attendance/session-qr/<uuid:att_session_id>/', SessionQRView.as_view(),           name='session-qr'),
    path('attendance/postpone-session/',               PostponeSessionView.as_view(),        name='postpone-session'),
    path('', include(router.urls)),
]
