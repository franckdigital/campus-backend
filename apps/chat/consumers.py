import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.room_group_name = f'chat_{self.chat_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        is_member = await self.check_membership()
        if not is_member:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        await self.update_last_read()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'message')

        if message_type == 'message':
            await self.handle_message(data)
        elif message_type == 'typing':
            await self.handle_typing(data)
        elif message_type == 'read':
            await self.handle_read()

    async def handle_message(self, data):
        content = data.get('content', '')
        msg_type = data.get('message_type', 'TEXT')
        reply_to_id = data.get('reply_to')

        if not content:
            return

        message = await self.save_message(content, msg_type, reply_to_id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': str(message.id),
                    'content': message.content,
                    'message_type': message.message_type,
                    'sender_id': str(self.user.id),
                    'sender_name': self.user.full_name,
                    'created_at': message.created_at.isoformat(),
                    'reply_to': str(reply_to_id) if reply_to_id else None
                }
            }
        )

    async def handle_typing(self, data):
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': str(self.user.id),
                'user_name': self.user.full_name,
                'is_typing': is_typing
            }
        )

    async def handle_read(self):
        await self.update_last_read()

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
        }))

    async def typing_indicator(self, event):
        if str(self.user.id) != event['user_id']:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'user_name': event['user_name'],
                'is_typing': event['is_typing']
            }))

    @database_sync_to_async
    def check_membership(self):
        from .models import ChatMember
        return ChatMember.objects.filter(
            chat_id=self.chat_id,
            user=self.user,
            is_active=True
        ).exists()

    @database_sync_to_async
    def save_message(self, content, message_type, reply_to_id):
        from .models import ClassChat, ChatMessage
        chat = ClassChat.objects.get(id=self.chat_id)
        
        reply_to = None
        if reply_to_id:
            try:
                reply_to = ChatMessage.objects.get(id=reply_to_id)
            except ChatMessage.DoesNotExist:
                pass
        
        return ChatMessage.objects.create(
            chat=chat,
            sender=self.user,
            message_type=message_type,
            content=content,
            reply_to=reply_to
        )

    @database_sync_to_async
    def update_last_read(self):
        from .models import ChatMember
        ChatMember.objects.filter(
            chat_id=self.chat_id,
            user=self.user
        ).update(last_read_at=timezone.now())
