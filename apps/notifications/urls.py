from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import (
    NotificationViewSet, NotificationPreferenceViewSet,
    NotificationLogViewSet, NotificationTemplateViewSet,
    SendNotificationView, NotificationStatsView, RegisterDeviceView,
)

router = DefaultRouter()
router.register(r'notifications',             NotificationViewSet,           basename='notification')
router.register(r'notification-preferences',  NotificationPreferenceViewSet, basename='notification-preference')
router.register(r'notification-logs',         NotificationLogViewSet,        basename='notification-log')
router.register(r'notification-templates',    NotificationTemplateViewSet,   basename='notification-template')

urlpatterns = [
    path('notifications/send/',            SendNotificationView.as_view(),  name='send-notification'),
    path('notifications/stats/',           NotificationStatsView.as_view(), name='notification-stats'),
    path('notifications/register-device/', RegisterDeviceView.as_view(),    name='register-device'),
    path('', include(router.urls)),
]
