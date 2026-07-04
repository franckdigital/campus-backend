from django.urls import path
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import (
    GradeCategoryViewSet, EvaluationViewSet, GradeViewSet, ReportCardViewSet,
    ElearningEvaluationsView, ElearningStudentScoresView, ElearningImportGradesView,
)

router = DefaultRouter()
router.register(r'grades', GradeViewSet, basename='grade')
router.register(r'grade-categories', GradeCategoryViewSet, basename='grade-category')
router.register(r'evaluations', EvaluationViewSet, basename='evaluation')
router.register(r'report-cards', ReportCardViewSet, basename='report-card')

urlpatterns = router.urls + [
    path('elearning-evaluations/', ElearningEvaluationsView.as_view(), name='elearning-evaluations'),
    path('elearning-student-scores/<str:item_type>/<str:item_id>/', ElearningStudentScoresView.as_view(), name='elearning-student-scores'),
    path('elearning-import-grades/', ElearningImportGradesView.as_view(), name='elearning-import-grades'),
]
