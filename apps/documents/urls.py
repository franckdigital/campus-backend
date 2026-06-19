from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import DocumentCategoryViewSet, DocumentViewSet, ArchiveViewSet

router = DefaultRouter()
router.register(r'document-categories', DocumentCategoryViewSet, basename='document-category')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'archives', ArchiveViewSet, basename='archive')

urlpatterns = [
    path('', include(router.urls)),
]
