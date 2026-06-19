from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import StaffViewSet

router = SimpleRouter()
router.register(r'staff', StaffViewSet, basename='staff')

urlpatterns = [
    path('', include(router.urls)),
]
