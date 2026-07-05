from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import AIKeywordResponseViewSet, AIAssistantView

router = SimpleRouter()
router.register(r'ai-responses', AIKeywordResponseViewSet, basename='ai-response')

urlpatterns = [
    path('landing/ai-assistant/', AIAssistantView.as_view(), name='ai-assistant'),
    path('', include(router.urls)),
]
