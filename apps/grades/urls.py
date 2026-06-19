from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import GradeCategoryViewSet, EvaluationViewSet, GradeViewSet, ReportCardViewSet

router = DefaultRouter()
router.register(r'grades', GradeViewSet, basename='grade')
router.register(r'grade-categories', GradeCategoryViewSet, basename='grade-category')
router.register(r'evaluations', EvaluationViewSet, basename='evaluation')
router.register(r'report-cards', ReportCardViewSet, basename='report-card')

urlpatterns = router.urls
