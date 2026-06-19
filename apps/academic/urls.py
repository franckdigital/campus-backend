from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import (
    ProgramViewSet, LevelViewSet, SubjectViewSet, TeacherViewSet,
    ClassViewSet, EnrollmentViewSet, RoomViewSet, SessionViewSet, SemesterViewSet,
    LevelSubjectViewSet, ClassSubjectTeacherViewSet,
)

router = DefaultRouter()
router.register(r'semesters', SemesterViewSet, basename='semester')
router.register(r'programs', ProgramViewSet, basename='program')
router.register(r'levels', LevelViewSet, basename='level')
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'teachers', TeacherViewSet, basename='teacher')
router.register(r'classes', ClassViewSet, basename='class')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'sessions', SessionViewSet, basename='session')
router.register(r'level-subjects', LevelSubjectViewSet, basename='level-subject')
router.register(r'class-subject-teachers', ClassSubjectTeacherViewSet, basename='class-subject-teacher')

urlpatterns = [
    path('', include(router.urls)),
]
