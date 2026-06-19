from django.contrib import admin
from .models import ClassChat, ChatMessage, ChatMember


@admin.register(ClassChat)
class ClassChatAdmin(admin.ModelAdmin):
    list_display = ['name', 'class_obj', 'is_moderated', 'message_count', 'created_by', 'created_at']
    list_filter = ['is_moderated', 'is_active']
    search_fields = ['name', 'class_obj__name']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['chat', 'sender', 'message_type', 'content_preview', 'is_pinned', 'is_deleted', 'created_at']
    list_filter = ['message_type', 'is_pinned', 'is_deleted', 'chat']
    search_fields = ['content', 'sender__email']
    ordering = ['-created_at']

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Contenu'


@admin.register(ChatMember)
class ChatMemberAdmin(admin.ModelAdmin):
    list_display = ['chat', 'user', 'role', 'is_muted', 'joined_at', 'is_active']
    list_filter = ['role', 'is_muted', 'is_active']
    search_fields = ['user__email', 'chat__name']
