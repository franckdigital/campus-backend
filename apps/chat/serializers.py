from rest_framework import serializers
from .models import ClassChat, ChatMessage, ChatMember, Conversation, DirectMessage


class ChatMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)
    unread_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ChatMember
        fields = [
            'id', 'chat', 'user', 'user_name', 'user_email', 'user_avatar',
            'role', 'is_muted', 'muted_until', 'last_read_at', 'joined_at',
            'unread_count', 'is_active'
        ]
        read_only_fields = ['id', 'joined_at']


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_avatar = serializers.ImageField(source='sender.avatar', read_only=True)
    reply_to_content = serializers.CharField(source='reply_to.content', read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'chat', 'sender', 'sender_name', 'sender_avatar',
            'message_type', 'content', 'file', 'reply_to', 'reply_to_content',
            'is_edited', 'edited_at', 'is_deleted', 'is_pinned',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'is_edited', 'edited_at', 'is_deleted', 'created_at']


class ClassChatSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_obj.name', read_only=True)
    message_count = serializers.IntegerField(read_only=True)
    last_message = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = ClassChat
        fields = [
            'id', 'class_obj', 'class_name', 'name', 'description',
            'is_moderated', 'message_count', 'last_message', 'members_count',
            'created_by', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_last_message(self, obj):
        last = obj.messages.filter(is_active=True, is_deleted=False).first()
        if last:
            return {
                'content': last.content[:100],
                'sender': last.sender.full_name if last.sender else 'Système',
                'created_at': last.created_at
            }
        return None

    def get_members_count(self, obj):
        return obj.members.filter(is_active=True).count()


class ClassChatDetailSerializer(ClassChatSerializer):
    members = ChatMemberSerializer(many=True, read_only=True)
    pinned_messages = serializers.SerializerMethodField()

    class Meta(ClassChatSerializer.Meta):
        fields = ClassChatSerializer.Meta.fields + ['members', 'pinned_messages']

    def get_pinned_messages(self, obj):
        pinned = obj.messages.filter(is_active=True, is_pinned=True, is_deleted=False)
        return ChatMessageSerializer(pinned, many=True).data


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField()
    message_type = serializers.ChoiceField(
        choices=ChatMessage.MESSAGE_TYPE_CHOICES,
        default='TEXT'
    )
    reply_to = serializers.UUIDField(required=False, allow_null=True)
    file = serializers.FileField(required=False, allow_null=True)


# ── Direct messaging ──────────────────────────────────────────────────────────

class DirectMessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.UUIDField(source='sender.id', read_only=True)
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_avatar = serializers.ImageField(source='sender.avatar', read_only=True)

    class Meta:
        model = DirectMessage
        fields = [
            'id', 'conversation', 'sender_id', 'sender_name', 'sender_avatar',
            'content', 'is_read', 'read_at', 'is_deleted', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'is_read', 'read_at']


class ConversationParticipantSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    user_type = serializers.CharField()
    avatar = serializers.ImageField()


class ConversationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'other_user', 'last_message_at',
            'last_message_preview', 'unread_count', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_other_user(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        other = obj.other_participant(request.user)
        if not other:
            return None
        return {
            'id': str(other.id),
            'full_name': other.full_name,
            'email': other.email,
            'user_type': other.user_type,
            'avatar': request.build_absolute_uri(other.avatar.url) if other.avatar else None,
        }

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request:
            return 0
        return obj.unread_count_for(request.user)


class StartConversationSerializer(serializers.Serializer):
    participant_id = serializers.UUIDField()
    initial_message = serializers.CharField(required=False, allow_blank=True)
