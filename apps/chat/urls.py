from django.urls import path, include
from rest_framework.routers import SimpleRouter as DefaultRouter
from .views import ClassChatViewSet, ChatMessageViewSet, ConversationViewSet

router = DefaultRouter()
router.register(r'chats', ClassChatViewSet, basename='chat')
router.register(r'chat-messages', ChatMessageViewSet, basename='chat-message')
router.register(r'conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    path('', include(router.urls)),
]
