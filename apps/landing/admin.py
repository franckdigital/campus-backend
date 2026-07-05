from django.contrib import admin
from .models import AIKeywordResponse


@admin.register(AIKeywordResponse)
class AIKeywordResponseAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'priority', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('keyword', 'question_example', 'response')
    ordering = ('priority', 'keyword')
