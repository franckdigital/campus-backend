from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import (
    SiteViewSet, AcademicYearViewSet, AuditLogViewSet, SystemConfigViewSet,
    WorkspaceSettingsView,
)

router = DefaultRouter()
router.register(r'sites', SiteViewSet, basename='site')
router.register(r'academic-years', AcademicYearViewSet, basename='academic-year')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
router.register(r'configs', SystemConfigViewSet, basename='config')

urlpatterns = [
    path('workspace-settings/', WorkspaceSettingsView.as_view(), name='workspace-settings'),
    path('', include(router.urls)),
]
