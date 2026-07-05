from rest_framework import serializers
from .models import AIKeywordResponse


class AIKeywordResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIKeywordResponse
        fields = [
            'id', 'keyword', 'question_example', 'response', 'priority',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
