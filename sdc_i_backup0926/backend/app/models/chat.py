"""
Chat related database models
"""
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(100))
    avatar = Column(String(255))
    role = Column(String(20), default="user")  # admin, user, moderator
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conversations = relationship("Conversation", back_populates="user")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived = Column(Boolean, default=False)
    tags = Column(JSON)  # Store as JSON array

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Message metadata (JSON field for flexible metadata storage)
    message_metadata = Column(JSON)  # Will store model, temperature, tokens, etc.

    # Document sources (for RAG responses)
    sources = Column(JSON)  # Will store document source information

    # Streaming and error handling
    is_streaming = Column(Boolean, default=False)
    error = Column(Text)
    rating = Column(Integer)  # User rating for AI responses

    # Dual provider support (for web mode)
    is_dual_provider = Column(Boolean, default=False)
    dual_provider_responses = Column(JSON)  # Store GPT and Perplexity responses

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User")

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(String(20), nullable=False)  # pdf, txt, docx, md, html
    size = Column(Integer, nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="ready")  # uploading, processing, ready, error

    # Document metadata
    document_metadata = Column(JSON)  # author, created_at, language, page_count, etc.

    # Processing information
    processing_method = Column(String(50))  # docling, alternative_processor, basic

    # Relationships
    uploader = relationship("User")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    start_index = Column(Integer, nullable=False)
    end_index = Column(Integer, nullable=False)

    # Vector embedding (stored as JSON array)
    embedding = Column(JSON)

    # Chunk metadata
    chunk_metadata = Column(JSON)  # page, section, title, etc.

    # Relationships
    document = relationship("Document", back_populates="chunks")