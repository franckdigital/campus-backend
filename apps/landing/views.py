from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import AIKeywordResponse
from .serializers import AIKeywordResponseSerializer


class IsAdminOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.user_type in ('ADMIN', 'STAFF'))


class AIKeywordResponseViewSet(viewsets.ModelViewSet):
    """Admin CRUD for the vitrine chatbot's keyword → response table."""
    queryset = AIKeywordResponse.objects.all().order_by('priority', 'keyword')
    serializer_class = AIKeywordResponseSerializer
    permission_classes = [IsAdminOrStaff]
    # This viewset is admin-only anyway (IsAdminOrStaff), but mark it exempt
    # for documentation/consistency with the rest of the codebase's pattern.
    fee_gate_exempt = True


class AIAssistantView(APIView):
    """Public endpoint the vitrine's chatbot widget calls. Plain keyword
    substring match — no LLM. Mirrors plateforme-travail/backend/landing/views.py
    ai_assistant exactly."""
    permission_classes = [permissions.AllowAny]
    fee_gate_exempt = True

    def post(self, request):
        question = (request.data.get('question') or '').strip()
        if not question:
            return Response({'detail': 'question requise'}, status=status.HTTP_400_BAD_REQUEST)

        question_lower = question.lower()
        answer = None
        for kr in AIKeywordResponse.objects.filter(is_active=True).order_by('priority'):
            if kr.keyword.lower() in question_lower:
                answer = kr.response
                break

        if not answer:
            default_response = AIKeywordResponse.objects.filter(
                keyword__iexact='default', is_active=True
            ).first()
            answer = default_response.response if default_response else (
                "Merci pour votre question. Un conseiller vous répondra bientôt — "
                "vous pouvez aussi nous contacter directement via la page Contact."
            )

        return Response({'answer': answer})
