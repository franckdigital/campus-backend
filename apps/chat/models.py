from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import BaseModel
from apps.academic.models import Class


class Conversation(BaseModel):
    """Direct message thread between two users."""
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_message_preview = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'conversations'
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        ordering = ['-last_message_at']

    def __str__(self):
        names = ', '.join(p.full_name for p in self.participants.all()[:2])
        return f"Conv({names})"

    def other_participant(self, user):
        return self.participants.exclude(id=user.id).first()

    def unread_count_for(self, user):
        return self.direct_messages.filter(
            is_active=True, is_deleted=False
        ).exclude(sender=user).filter(is_read=False).count()

    def update_preview(self, content):
        self.last_message_at = timezone.now()
        self.last_message_preview = content[:200]
        self.save(update_fields=['last_message_at', 'last_message_preview'])


class DirectMessage(BaseModel):
    """A single message within a direct conversation."""
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='direct_messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_direct_messages',
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'direct_messages'
        verbose_name = 'Message direct'
        verbose_name_plural = 'Messages directs'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender} -> {self.content[:50]}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class ClassChat(BaseModel):
    """Chat room for a class."""
    class_obj = models.OneToOneField(
        Class,
        on_delete=models.CASCADE,
        related_name='chat'
    )
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    is_moderated = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_chats'
    )

    class Meta:
        db_table = 'class_chats'
        verbose_name = 'Chat de classe'
        verbose_name_plural = 'Chats de classe'

    def __str__(self):
        return f"Chat - {self.class_obj.name}"

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"Chat {self.class_obj.name}"
        super().save(*args, **kwargs)

    @property
    def message_count(self):
        return self.messages.filter(is_active=True).count()


class ChatMessage(BaseModel):
    """Message in a class chat."""
    MESSAGE_TYPE_CHOICES = [
        ('TEXT', 'Texte'),
        ('FILE', 'Fichier'),
        ('IMAGE', 'Image'),
        ('SYSTEM', 'Système'),
    ]

    chat = models.ForeignKey(
        ClassChat,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chat_messages'
    )
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='TEXT')
    content = models.TextField()
    file = models.FileField(upload_to='chat/files/', blank=True, null=True)
    
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    is_pinned = models.BooleanField(default=False)
    pinned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pinned_messages'
    )

    class Meta:
        db_table = 'chat_messages'
        verbose_name = 'Message de chat'
        verbose_name_plural = 'Messages de chat'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender} - {self.content[:50]}"

    def soft_delete(self):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.content = "[Message supprimé]"
        self.save()

    def edit(self, new_content):
        from django.utils import timezone
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save()


class ChatMember(BaseModel):
    """Member of a chat room."""
    ROLE_CHOICES = [
        ('ADMIN', 'Administrateur'),
        ('MODERATOR', 'Modérateur'),
        ('MEMBER', 'Membre'),
    ]

    chat = models.ForeignKey(
        ClassChat,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_memberships'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER')
    is_muted = models.BooleanField(default=False)
    muted_until = models.DateTimeField(null=True, blank=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_members'
        verbose_name = 'Membre du chat'
        verbose_name_plural = 'Membres du chat'
        unique_together = ['chat', 'user']

    def __str__(self):
        return f"{self.user.full_name} - {self.chat.name}"

    @property
    def unread_count(self):
        if not self.last_read_at:
            return self.chat.messages.filter(is_active=True, is_deleted=False).count()
        return self.chat.messages.filter(
            is_active=True,
            is_deleted=False,
            created_at__gt=self.last_read_at
        ).exclude(sender=self.user).count()
