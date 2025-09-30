"""
Chat History Service for PostgreSQL storage
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.chat import User, Conversation, Message, Document


class ChatHistoryService:
    """Service for managing chat history in PostgreSQL"""

    async def get_or_create_user(
        self,
        db: AsyncSession,
        user_id: str = None,
        username: str = "anonymous",
        email: str = "anonymous@sdc.local"
    ) -> User:
        """Get existing user or create new one"""
        if user_id:
            # Try to get existing user
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                return user

        # Check if user exists by email
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            user = User(
                id=uuid.uuid4() if not user_id else user_id,
                username=username,
                email=email,
                display_name=username,
                role="user"
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        return user

    async def create_conversation(
        self,
        db: AsyncSession,
        user_id: str,
        title: str = "New Conversation"
    ) -> Conversation:
        """Create a new conversation"""
        conversation = Conversation(
            id=uuid.uuid4(),
            title=title,
            user_id=user_id
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation

    async def get_or_create_conversation(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: str = None,
        title: str = "New Conversation"
    ) -> Conversation:
        """Get existing conversation or create new one"""
        if conversation_id:
            # Try to get existing conversation
            stmt = select(Conversation).where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id
                )
            )
            result = await db.execute(stmt)
            conversation = result.scalar_one_or_none()
            if conversation:
                return conversation

        # Create new conversation
        return await self.create_conversation(db, user_id, title)

    async def save_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        content: str,
        role: str,
        metadata: Dict[str, Any] = None,
        sources: List[Dict[str, Any]] = None,
        is_dual_provider: bool = False,
        dual_provider_responses: Dict[str, str] = None
    ) -> Message:
        """Save a message to the database"""
        message = Message(
            id=uuid.uuid4(),
            content=content,
            role=role,
            conversation_id=conversation_id,
            user_id=user_id,
            message_metadata=metadata,
            sources=sources,
            is_dual_provider=is_dual_provider,
            dual_provider_responses=dual_provider_responses
        )

        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    async def get_conversation_messages(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Message]:
        """Get messages for a conversation"""
        stmt = (
            select(Message)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.user_id == user_id
                )
            )
            .order_by(Message.timestamp.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_user_conversations(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Conversation]:
        """Get conversations for a user"""
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(stmt)
        return result.scalars().all()

    async def update_conversation_title(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        new_title: str
    ) -> Optional[Conversation]:
        """Update conversation title"""
        stmt = select(Conversation).where(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if conversation:
            conversation.title = new_title
            conversation.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(conversation)

        return conversation

    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """Delete a conversation and all its messages"""
        stmt = select(Conversation).where(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if conversation:
            await db.delete(conversation)
            await db.commit()
            return True

        return False

    async def get_conversation_stats(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """Get conversation statistics for a user"""
        # Count conversations
        conv_stmt = select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
        conv_result = await db.execute(conv_stmt)
        conv_count = conv_result.scalar()

        # Count messages
        msg_stmt = select(func.count(Message.id)).where(Message.user_id == user_id)
        msg_result = await db.execute(msg_stmt)
        msg_count = msg_result.scalar()

        return {
            "total_conversations": conv_count,
            "total_messages": msg_count
        }


# Global instance
chat_history_service = ChatHistoryService()


async def get_chat_history_service() -> ChatHistoryService:
    """Dependency injection for chat history service"""
    return chat_history_service