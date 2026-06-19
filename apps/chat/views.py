from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.utils import timezone
from django.db.models import Q

from .models import ClassChat, ChatMessage, ChatMember, Conversation, DirectMessage
from .serializers import (
    ClassChatSerializer, ClassChatDetailSerializer,
    ChatMessageSerializer, ChatMemberSerializer, SendMessageSerializer,
    ConversationSerializer, DirectMessageSerializer, StartConversationSerializer,
)


class ClassChatViewSet(viewsets.ModelViewSet):
    queryset = ClassChat.objects.select_related('class_obj', 'created_by').all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['class_obj', 'is_moderated', 'is_active']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ClassChatDetailSerializer
        return ClassChatSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        chat = self.get_object()
        messages = chat.messages.filter(is_active=True).select_related('sender')
        
        limit = int(request.query_params.get('limit', 50))
        before = request.query_params.get('before')
        
        if before:
            messages = messages.filter(created_at__lt=before)
        
        messages = messages[:limit]
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='send-message')
    def send_message(self, request, pk=None):
        chat = self.get_object()
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        reply_to = None
        if data.get('reply_to'):
            try:
                reply_to = ChatMessage.objects.get(id=data['reply_to'])
            except ChatMessage.DoesNotExist:
                pass
        
        message = ChatMessage.objects.create(
            chat=chat,
            sender=request.user,
            message_type=data['message_type'],
            content=data['content'],
            file=data.get('file'),
            reply_to=reply_to
        )
        
        return Response(
            ChatMessageSerializer(message).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        chat = self.get_object()
        members = chat.members.filter(is_active=True).select_related('user')
        serializer = ChatMemberSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='add-member')
    def add_member(self, request, pk=None):
        chat = self.get_object()
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'MEMBER')
        
        member, created = ChatMember.objects.get_or_create(
            chat=chat,
            user_id=user_id,
            defaults={'role': role}
        )
        
        if not created:
            member.is_active = True
            member.role = role
            member.save()
        
        return Response(ChatMemberSerializer(member).data)

    @action(detail=True, methods=['post'], url_path='remove-member')
    def remove_member(self, request, pk=None):
        chat = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            member = ChatMember.objects.get(chat=chat, user_id=user_id)
            member.is_active = False
            member.save()
            return Response({'detail': 'Membre retiré'})
        except ChatMember.DoesNotExist:
            return Response(
                {'detail': 'Membre non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )


class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.select_related('chat', 'sender', 'reply_to').all()
    serializer_class = ChatMessageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['created_at']
    filterset_fields = ['chat', 'sender', 'message_type', 'is_pinned', 'is_active']

    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        message = self.get_object()
        message.is_pinned = True
        message.pinned_by = request.user
        message.save()
        return Response(ChatMessageSerializer(message).data)

    @action(detail=True, methods=['post'])
    def unpin(self, request, pk=None):
        message = self.get_object()
        message.is_pinned = False
        message.pinned_by = None
        message.save()
        return Response(ChatMessageSerializer(message).data)

    @action(detail=True, methods=['post'])
    def edit(self, request, pk=None):
        message = self.get_object()
        
        if message.sender != request.user:
            return Response(
                {'detail': 'Vous ne pouvez modifier que vos propres messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_content = request.data.get('content')
        if not new_content:
            return Response(
                {'detail': 'Le contenu est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message.edit(new_content)
        return Response(ChatMessageSerializer(message).data)

    @action(detail=True, methods=['post'])
    def delete(self, request, pk=None):
        message = self.get_object()

        if message.sender != request.user:
            member = ChatMember.objects.filter(
                chat=message.chat,
                user=request.user,
                role__in=['ADMIN', 'MODERATOR']
            ).exists()

            if not member:
                return Response(
                    {'detail': 'Vous n\'avez pas la permission de supprimer ce message'},
                    status=status.HTTP_403_FORBIDDEN
                )

        message.soft_delete()
        return Response({'detail': 'Message supprimé'})


# ── Direct messaging ──────────────────────────────────────────────────────────

class ConversationViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user,
            is_active=True,
        ).prefetch_related('participants').order_by('-last_message_at')

    def list(self, request):
        """GET /conversations/ — mes conversations triées par activité."""
        qs = self.get_queryset()
        serializer = ConversationSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    def create(self, request):
        """POST /conversations/ — démarrer ou récupérer une conversation avec un utilisateur."""
        ser = StartConversationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        participant_id = ser.validated_data['participant_id']
        initial_message = ser.validated_data.get('initial_message', '')

        from apps.accounts.models import User
        try:
            other_user = User.objects.get(id=participant_id)
        except User.DoesNotExist:
            return Response({'detail': 'Utilisateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if other_user == request.user:
            return Response({'detail': 'Impossible de créer une conversation avec soi-même.'}, status=status.HTTP_400_BAD_REQUEST)

        # Find existing conversation between the two
        existing = Conversation.objects.filter(
            participants=request.user, is_active=True
        ).filter(participants=other_user).first()

        if existing:
            conversation = existing
            created = False
        else:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, other_user)
            created = True

        if initial_message:
            msg = DirectMessage.objects.create(
                conversation=conversation,
                sender=request.user,
                content=initial_message,
            )
            conversation.update_preview(initial_message)

        response_data = ConversationSerializer(conversation, context={'request': request}).data
        return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """GET /conversations/{id}/messages/ — messages paginés (50 derniers par défaut)."""
        conversation = self._get_conversation_or_403(pk, request.user)
        if isinstance(conversation, Response):
            return conversation

        limit = min(int(request.query_params.get('limit', 50)), 200)
        before = request.query_params.get('before')

        qs = conversation.direct_messages.filter(is_active=True, is_deleted=False)
        if before:
            qs = qs.filter(created_at__lt=before)
        qs = qs.select_related('sender').order_by('created_at')[:limit]

        # Mark incoming messages as read
        DirectMessage.objects.filter(
            conversation=conversation,
            is_read=False,
            is_active=True,
        ).exclude(sender=request.user).update(
            is_read=True, read_at=timezone.now()
        )

        serializer = DirectMessageSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """POST /conversations/{id}/send/ — envoyer un message."""
        conversation = self._get_conversation_or_403(pk, request.user)
        if isinstance(conversation, Response):
            return conversation

        content = request.data.get('content', '').strip()
        if not content:
            return Response({'detail': 'Le message ne peut pas être vide.'}, status=status.HTTP_400_BAD_REQUEST)

        msg = DirectMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
        )
        conversation.update_preview(content)

        return Response(DirectMessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """POST /conversations/{id}/mark-read/ — marquer tous les messages comme lus."""
        conversation = self._get_conversation_or_403(pk, request.user)
        if isinstance(conversation, Response):
            return conversation

        updated = DirectMessage.objects.filter(
            conversation=conversation,
            is_read=False,
            is_active=True,
        ).exclude(sender=request.user).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({'marked_read': updated})

    @action(detail=False, methods=['get'])
    def contacts(self, request):
        """GET /conversations/contacts/ — liste des utilisateurs joignables (admins, enseignants, administration)."""
        from apps.accounts.models import User
        qs = User.objects.filter(
            is_active=True,
            user_type__in=['ADMIN', 'STAFF', 'TEACHER'],
        ).exclude(id=request.user.id).order_by('last_name', 'first_name')

        data = [
            {
                'id': str(u.id),
                'full_name': u.full_name,
                'email': u.email,
                'user_type': u.user_type,
                'avatar': request.build_absolute_uri(u.avatar.url) if u.avatar else None,
            }
            for u in qs
        ]
        return Response(data)

    def _get_conversation_or_403(self, pk, user):
        try:
            conv = Conversation.objects.filter(participants=user, is_active=True).get(pk=pk)
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return conv
