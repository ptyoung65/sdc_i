"""
Database models for internal server settings
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class InternalServerConfig(Base):
    """내부 서버 전체 설정"""
    __tablename__ = "internal_server_config"

    id = Column(Integer, primary_key=True, index=True)
    enable_internal_server = Column(Boolean, default=True)
    internal_server_mode = Column(String(50), default="임베딩 서버만")
    default_model = Column(String(100), default="모델을 입력")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    embedding_servers = relationship("EmbeddingServerConfig", back_populates="config")
    llm_servers = relationship("LLMServerConfig", back_populates="config")

class EmbeddingServerConfig(Base):
    """임베딩 서버 설정"""
    __tablename__ = "embedding_server_config"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("internal_server_config.id"))
    server_id = Column(String(100), unique=True, index=True)
    name = Column(String(100), nullable=False)
    url = Column(String(200), nullable=False)
    api_key = Column(Text)
    status = Column(String(20), default="inactive")  # active, inactive, error
    is_primary = Column(Boolean, default=False)
    chunk_size = Column(Integer, default=1000)
    chunk_overlap = Column(Integer, default=200)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    config = relationship("InternalServerConfig", back_populates="embedding_servers")

class LLMServerConfig(Base):
    """LLM 서버 설정"""
    __tablename__ = "llm_server_config"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("internal_server_config.id"))
    server_id = Column(String(100), unique=True, index=True)
    name = Column(String(100), nullable=False)
    url = Column(String(200), nullable=False)
    api_key = Column(Text)
    model = Column(String(100), nullable=False)
    status = Column(String(20), default="inactive")  # active, inactive, error
    is_primary = Column(Boolean, default=False)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    config = relationship("InternalServerConfig", back_populates="llm_servers")

class LegacyServerSettings(Base):
    """기존 설정 (Legacy Settings)"""
    __tablename__ = "legacy_server_settings"

    id = Column(Integer, primary_key=True, index=True)
    api_url = Column(String(200), default="http://localhost:8000")
    ai_model = Column(String(50), default="gemini-1.5-pro")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)
    embedding_model = Column(String(50), default="KURE-v1")
    chunk_size = Column(Integer, default=1000)
    chunk_overlap = Column(Integer, default=200)
    enable_korean_processing = Column(Boolean, default=True)
    debug_mode = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)