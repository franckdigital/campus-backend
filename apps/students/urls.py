from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import ParentViewSet, StudentViewSet, StudentFileViewSet, StudentCardViewSet

router = DefaultRouter()
router.register(r'parents', ParentViewSet, basename='parent')
router.register(r'students', StudentViewSet, basename='student')
router.register(r'student-files', StudentFileViewSet, basename='student-file')
router.register(r'student-cards', StudentCardViewSet, basename='student-card')

urlpatterns = [
    path('', include(router.urls)),
]
