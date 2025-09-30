"""
Service for managing internal server settings with PostgreSQL CRUD operations
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from ..models.server_settings import (
    InternalServerConfig,
    EmbeddingServerConfig,
    LLMServerConfig,
    LegacyServerSettings
)

class ServerSettingsService:
    """Internal Server Settings CRUD Service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_internal_server_settings(self) -> Optional[Dict[str, Any]]:
        """내부 서버 설정 조회"""
        try:
            # 최신 설정 조회
            result = await self.db.execute(
                select(InternalServerConfig)
                .options(
                    selectinload(InternalServerConfig.embedding_servers),
                    selectinload(InternalServerConfig.llm_servers)
                )
                .order_by(InternalServerConfig.updated_at.desc())
                .limit(1)
            )
            config = result.scalar_one_or_none()

            if not config:
                return None

            return {
                "internal_settings": {
                    "enable_internal_server": config.enable_internal_server,
                    "internal_server_mode": config.internal_server_mode,
                    "default_model": config.default_model
                },
                "embedding_servers": [
                    {
                        "id": server.server_id,
                        "name": server.name,
                        "url": server.url,
                        "api_key": server.api_key,
                        "status": server.status,
                        "is_primary": server.is_primary,
                        "chunk_size": server.chunk_size,
                        "chunk_overlap": server.chunk_overlap
                    }
                    for server in config.embedding_servers
                ],
                "llm_servers": [
                    {
                        "id": server.server_id,
                        "name": server.name,
                        "url": server.url,
                        "api_key": server.api_key,
                        "model": server.model,
                        "status": server.status,
                        "is_primary": server.is_primary,
                        "temperature": server.temperature,
                        "max_tokens": server.max_tokens
                    }
                    for server in config.llm_servers
                ]
            }
        except Exception as e:
            print(f"❌ [DB] Error getting internal server settings: {str(e)}")
            return None

    async def save_internal_server_settings(self, settings_data: Dict[str, Any]) -> bool:
        """내부 서버 설정 저장"""
        try:
            # 안전한 삭제를 위해 트랜잭션을 사용하여 순차적으로 삭제
            # 1. 자식 테이블들을 먼저 삭제
            await self.db.execute(delete(EmbeddingServerConfig))
            await self.db.execute(delete(LLMServerConfig))
            # 2. 부모 테이블 삭제
            await self.db.execute(delete(InternalServerConfig))

            # Flush하여 삭제가 완료되도록 함
            await self.db.flush()

            # 새 설정 생성
            internal_settings = settings_data.get("internal_settings", {})
            config = InternalServerConfig(
                enable_internal_server=internal_settings.get("enable_internal_server", True),
                internal_server_mode=internal_settings.get("internal_server_mode", "임베딩 서버만"),
                default_model=internal_settings.get("default_model", "모델을 입력")
            )
            self.db.add(config)
            await self.db.flush()  # config.id 확보

            # 임베딩 서버 저장
            for server_data in settings_data.get("embedding_servers", []):
                embedding_server = EmbeddingServerConfig(
                    config_id=config.id,
                    server_id=server_data.get("id"),
                    name=server_data.get("name"),
                    url=server_data.get("url"),
                    api_key=server_data.get("api_key"),
                    status=server_data.get("status", "inactive"),
                    is_primary=server_data.get("is_primary", False),
                    chunk_size=server_data.get("chunk_size", 1000),
                    chunk_overlap=server_data.get("chunk_overlap", 200)
                )
                self.db.add(embedding_server)

            # LLM 서버 저장
            for server_data in settings_data.get("llm_servers", []):
                llm_server = LLMServerConfig(
                    config_id=config.id,
                    server_id=server_data.get("id"),
                    name=server_data.get("name"),
                    url=server_data.get("url"),
                    api_key=server_data.get("api_key"),
                    model=server_data.get("model"),
                    status=server_data.get("status", "inactive"),
                    is_primary=server_data.get("is_primary", False),
                    temperature=server_data.get("temperature", 0.7),
                    max_tokens=server_data.get("max_tokens", 2048)
                )
                self.db.add(llm_server)

            await self.db.commit()
            print(f"✅ [DB] Internal server settings saved successfully")
            return True

        except Exception as e:
            await self.db.rollback()
            print(f"❌ [DB] Error saving internal server settings: {str(e)}")
            return False

    async def get_external_llm_settings(self) -> Optional[Dict[str, Any]]:
        """외부 LLM 설정 조회"""
        try:
            result = await self.db.execute(
                select(LegacyServerSettings)
                .order_by(LegacyServerSettings.updated_at.desc())
                .limit(1)
            )
            settings = result.scalar_one_or_none()

            if not settings:
                return None

            return {
                "api_url": settings.api_url,
                "ai_model": settings.ai_model,
                "temperature": settings.temperature,
                "max_tokens": settings.max_tokens,
                "embedding_model": settings.embedding_model,
                "chunk_size": settings.chunk_size,
                "chunk_overlap": settings.chunk_overlap,
                "enable_korean_processing": settings.enable_korean_processing,
                "debug_mode": settings.debug_mode
            }
        except Exception as e:
            print(f"❌ [DB] Error getting external LLM settings: {str(e)}")
            return None

    async def save_external_llm_settings(self, settings_data: Dict[str, Any]) -> bool:
        """외부 LLM 설정 저장"""
        try:
            # 기존 설정 삭제
            await self.db.execute(delete(LegacyServerSettings))

            # 새 설정 생성
            settings = LegacyServerSettings(
                api_url=settings_data.get("api_url", "http://localhost:8000"),
                ai_model=settings_data.get("ai_model", "gemini-1.5-pro"),
                temperature=settings_data.get("temperature", 0.7),
                max_tokens=settings_data.get("max_tokens", 2048),
                embedding_model=settings_data.get("embedding_model", "KURE-v1"),
                chunk_size=settings_data.get("chunk_size", 1000),
                chunk_overlap=settings_data.get("chunk_overlap", 200),
                enable_korean_processing=settings_data.get("enable_korean_processing", True),
                debug_mode=settings_data.get("debug_mode", False)
            )
            self.db.add(settings)
            await self.db.commit()

            print(f"✅ [DB] External LLM settings saved successfully")
            return True

        except Exception as e:
            await self.db.rollback()
            print(f"❌ [DB] Error saving external LLM settings: {str(e)}")
            return False