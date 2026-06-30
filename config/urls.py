"""
URL configuration for Campus Management System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/', include([
        path('auth/', include('apps.accounts.urls')),
        path('', include('apps.core.urls')),
        path('', include('apps.students.urls')),
        path('', include('apps.academic.urls')),
        path('', include('apps.attendance.urls')),
        path('', include('apps.finance.urls')),
        path('', include('apps.payments.urls')),
        path('', include('apps.accounting.urls')),
        path('', include('apps.documents.urls')),
        path('', include('apps.elearning.urls')),
        path('', include('apps.chat.urls')),
        path('', include('apps.notifications.urls')),
        path('', include('apps.reports.urls')),
        path('', include('apps.grades.urls')),
        path('', include('apps.staff.urls')),
    ])),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Les fichiers media (PDF, vidéos, images uploadés) doivent être servis même
# hors DEBUG tant qu'aucun stockage S3/CDN n'est configuré (USE_S3=False),
# sinon les liens de téléchargement renvoient une 404 en production.
if not settings.USE_S3:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
