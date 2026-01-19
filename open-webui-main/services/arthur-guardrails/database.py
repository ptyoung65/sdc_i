"""
PostgreSQL Database Connection and Models for Arthur AI Guardrails
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Text, Integer, DECIMAL, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import select, insert, update, delete, text
import uuid
import logging

logger = logging.getLogger(__name__)

# Database configuration from environment variables
# DB_HOST를 우선 사용, 없으면 HOST_IP 사용
DB_HOST = os.getenv("DB_HOST") or os.getenv("HOST_IP")
if not DB_HOST:
    raise ValueError("❌ DB_HOST 또는 HOST_IP 환경변수가 설정되지 않았습니다. podman-start-remote.sh에서 -e DB_HOST 설정을 확인하세요.")

DB_PORT = os.getenv("DB_PORT", "5433")
DB_USER = os.getenv("DB_USER", "sdc_dev_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "sdc_dev_pass_2025")
DB_NAME = os.getenv("DB_NAME", "guardrails_db")

# DATABASE_URL을 asyncpg 드라이버로 구성
database_url_from_env = os.getenv("DATABASE_URL", f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
# postgresql://를 postgresql+asyncpg://로 변경
DATABASE_URL = database_url_from_env.replace("postgresql://", "postgresql+asyncpg://")
logger.info(f"Database URL: postgresql+asyncpg://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class for all models
Base = declarative_base()

class GuardrailKeyword(Base):
    """가드레일 키워드 모델"""
    __tablename__ = "guardrail_keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, default='basic')  # 'basic', 'personal', 'blacklist', 'whitelist', 'corporate', 'toxicity'
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class GuardrailSettings(Base):
    """가드레일 전역 설정 모델"""
    __tablename__ = "guardrail_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class GuardrailLog(Base):
    """가드레일 실행 로그 모델"""
    __tablename__ = "guardrail_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_text = Column(Text, nullable=False)
    is_safe = Column(Boolean, nullable=False)
    blocked_keywords = Column(ARRAY(String))
    blocked_categories = Column(ARRAY(String))
    confidence_score = Column(DECIMAL(3, 2))
    action_taken = Column(String(20))  # 'allowed', 'blocked', 'flagged'
    sensitivity = Column(DECIMAL(3, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DatabaseManager:
    """데이터베이스 작업을 관리하는 클래스"""

    @staticmethod
    async def init_database():
        """
        제102원칙: Mock 금지 - 테이블 검증만 수행, 생성 안 함

        테이블은 manual-start-all-services.sh의 create_all_tables.sql에서 생성됨
        """
        try:
            # 3개 Guardrails 테이블 존재 확인
            required_tables = ['guardrail_keywords', 'guardrail_settings', 'guardrail_logs']
            async with engine.begin() as conn:
                for table in required_tables:
                    result = await conn.execute(text(f"SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = '{table}')"))
                    table_exists = result.scalar()
                    if not table_exists:
                        error_msg = (
                            f"❌ 필수 테이블 '{table}'이 존재하지 않습니다 (제102원칙 위반)\n"
                            f"테이블은 manual-start-all-services.sh 실행 시 생성되어야 합니다.\n"
                            f"create_all_tables.sql을 먼저 실행하세요."
                        )
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)

            logger.info("✅ Guardrails tables verified successfully (3 tables)")
            await DatabaseManager.init_default_data()
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    @staticmethod
    async def init_default_data():
        """기본 데이터 초기화"""
        try:
            async with async_session() as session:
                # 키워드가 이미 존재하는지 확인
                result = await session.execute(select(GuardrailKeyword))
                existing_keywords = result.fetchall()

                if not existing_keywords:
                    # 기본 키워드 데이터
                    default_keywords = [
                        {"id": "1", "text": "욕설/비속어", "category": "basic", "enabled": True},
                        {"id": "2", "text": "성적 콘텐츠", "category": "basic", "enabled": True},
                        {"id": "3", "text": "폭력적 콘텐츠", "category": "basic", "enabled": True},
                        {"id": "4", "text": "개인정보", "category": "basic", "enabled": True},
                        {"id": "5", "text": "유해한 지시사항", "category": "basic", "enabled": True},
                        {"id": "6", "text": "허성 키워드입", "category": "personal", "enabled": True},
                        {"id": "7", "text": "블랙리스트", "category": "blacklist", "enabled": False},
                        {"id": "8", "text": "화이트리스트", "category": "whitelist", "enabled": True}
                    ]

                    for kw_data in default_keywords:
                        keyword = GuardrailKeyword(**kw_data)
                        session.add(keyword)

                    logger.info(f"✅ Added {len(default_keywords)} default keywords")

                # 설정이 이미 존재하는지 확인
                result = await session.execute(select(GuardrailSettings))
                existing_settings = result.fetchall()

                if not existing_settings:
                    # 기본 설정 데이터
                    default_settings = [
                        {"setting_key": "guardrails_enabled", "setting_value": "true", "description": "기본 가드레일 활성화 여부"},
                        {"setting_key": "korean_guardrails_enabled", "setting_value": "true", "description": "한국어 가드레일 활성화 여부"},
                        {"setting_key": "global_sensitivity", "setting_value": "0.7", "description": "전역 민감도 설정 (0.0-1.0)"},
                        {"setting_key": "auto_block", "setting_value": "true", "description": "자동 차단 기능 활성화 여부"},
                        {"setting_key": "logging_enabled", "setting_value": "true", "description": "로깅 기능 활성화 여부"}
                    ]

                    for setting_data in default_settings:
                        setting = GuardrailSettings(**setting_data)
                        session.add(setting)

                    logger.info(f"✅ Added {len(default_settings)} default settings")

                await session.commit()

        except Exception as e:
            logger.error(f"❌ Default data initialization failed: {e}")
            raise

    @staticmethod
    async def get_all_keywords() -> List[Dict[str, Any]]:
        """모든 키워드 조회"""
        async with async_session() as session:
            result = await session.execute(select(GuardrailKeyword))
            keywords = result.scalars().all()
            return [
                {
                    "id": kw.id,
                    "text": kw.text,
                    "category": kw.category,
                    "enabled": kw.enabled,
                    "created_at": kw.created_at.isoformat() if kw.created_at else None,
                    "updated_at": kw.updated_at.isoformat() if kw.updated_at else None
                }
                for kw in keywords
            ]

    @staticmethod
    async def get_keywords_by_category(category: str) -> List[Dict[str, Any]]:
        """카테고리별 키워드 조회"""
        async with async_session() as session:
            result = await session.execute(
                select(GuardrailKeyword).where(GuardrailKeyword.category == category)
            )
            keywords = result.scalars().all()
            return [
                {
                    "id": kw.id,
                    "text": kw.text,
                    "category": kw.category,
                    "enabled": kw.enabled,
                    "created_at": kw.created_at.isoformat() if kw.created_at else None,
                    "updated_at": kw.updated_at.isoformat() if kw.updated_at else None
                }
                for kw in keywords
            ]

    @staticmethod
    async def get_all_categories() -> List[str]:
        """모든 고유 카테고리 조회 (동적 가드레일 검사용)"""
        async with async_session() as session:
            result = await session.execute(
                text("SELECT DISTINCT category FROM guardrail_keywords WHERE enabled = true ORDER BY category")
            )
            categories = result.fetchall()
            return [row[0] for row in categories if row[0]]

    @staticmethod
    async def get_keyword_by_id(keyword_id: str) -> Optional[Dict[str, Any]]:
        """ID로 키워드 조회"""
        async with async_session() as session:
            result = await session.execute(
                select(GuardrailKeyword).where(GuardrailKeyword.id == keyword_id)
            )
            keyword = result.scalar_one_or_none()

            if not keyword:
                return None

            return {
                "id": keyword.id,
                "text": keyword.text,
                "category": keyword.category,
                "enabled": keyword.enabled,
                "created_at": keyword.created_at.isoformat() if keyword.created_at else None,
                "updated_at": keyword.updated_at.isoformat() if keyword.updated_at else None
            }

    @staticmethod
    async def add_keyword(keyword_data: Dict[str, Any]) -> Dict[str, Any]:
        """새 키워드 추가 - id는 자동 생성 (Integer autoincrement)"""
        async with async_session() as session:
            keyword = GuardrailKeyword(
                text=keyword_data["text"],
                category=keyword_data.get("category", "basic"),
                enabled=keyword_data.get("enabled", True)
            )
            session.add(keyword)
            await session.commit()
            await session.refresh(keyword)

            return {
                "id": keyword.id,
                "text": keyword.text,
                "category": keyword.category,
                "enabled": keyword.enabled,
                "created_at": keyword.created_at.isoformat() if keyword.created_at else None,
                "updated_at": keyword.updated_at.isoformat() if keyword.updated_at else None
            }

    @staticmethod
    async def update_keyword(keyword_id: str, keyword_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """키워드 업데이트"""
        async with async_session() as session:
            result = await session.execute(
                select(GuardrailKeyword).where(GuardrailKeyword.id == keyword_id)
            )
            keyword = result.scalar_one_or_none()

            if not keyword:
                return None

            keyword.text = keyword_data.get("text", keyword.text)
            keyword.category = keyword_data.get("category", keyword.category)
            keyword.enabled = keyword_data.get("enabled", keyword.enabled)
            keyword.updated_at = datetime.now()

            await session.commit()
            await session.refresh(keyword)

            return {
                "id": keyword.id,
                "text": keyword.text,
                "category": keyword.category,
                "enabled": keyword.enabled,
                "created_at": keyword.created_at.isoformat() if keyword.created_at else None,
                "updated_at": keyword.updated_at.isoformat() if keyword.updated_at else None
            }

    @staticmethod
    async def delete_keyword(keyword_id: str) -> bool:
        """키워드 삭제"""
        async with async_session() as session:
            result = await session.execute(
                select(GuardrailKeyword).where(GuardrailKeyword.id == keyword_id)
            )
            keyword = result.scalar_one_or_none()

            if not keyword:
                return False

            await session.delete(keyword)
            await session.commit()
            return True

    @staticmethod
    async def get_settings() -> Dict[str, str]:
        """모든 설정 조회"""
        async with async_session() as session:
            result = await session.execute(select(GuardrailSettings))
            settings = result.scalars().all()
            return {setting.setting_key: setting.setting_value for setting in settings}

    @staticmethod
    async def update_setting(key: str, value: str) -> bool:
        """설정 업데이트"""
        async with async_session() as session:
            result = await session.execute(
                select(GuardrailSettings).where(GuardrailSettings.setting_key == key)
            )
            setting = result.scalar_one_or_none()

            if setting:
                setting.setting_value = value
                setting.updated_at = datetime.now()
            else:
                setting = GuardrailSettings(setting_key=key, setting_value=value)
                session.add(setting)

            await session.commit()
            return True

    @staticmethod
    async def log_test_result(log_data: Dict[str, Any]) -> str:
        """테스트 결과 로그 저장 - guardrail_logs와 guardrail_check_logs 양쪽에 저장"""
        import uuid
        import json
        async with async_session() as session:
            # 1. 기존 guardrail_logs 테이블에 저장
            action = log_data.get("action", log_data.get("action_taken", "unknown"))
            log = GuardrailLog(
                test_text=log_data["test_text"],
                is_safe=log_data["is_safe"],
                blocked_keywords=log_data.get("blocked_keywords", []),
                blocked_categories=log_data.get("blocked_categories", []),
                confidence_score=log_data.get("confidence_score", 0.0),
                action_taken=action,
                sensitivity=log_data.get("sensitivity", 0.7)
            )
            session.add(log)
            await session.commit()
            await session.refresh(log)

            # 2. 대시보드용 guardrail_check_logs 테이블에도 저장
            check_result = "block" if action == "block" else ("warn" if action == "warn" else "pass")

            check_log_query = text("""
                INSERT INTO guardrail_check_logs
                (request_id, user_id, check_type, original_text, text_length,
                 check_result, detection_score, detected_categories, detected_keywords,
                 action_taken, processing_time_ms, created_at)
                VALUES (:request_id, :user_id, :check_type, :original_text, :text_length,
                        :check_result, :detection_score, :detected_categories, :detected_keywords,
                        :action_taken, :processing_time_ms, NOW())
            """)

            await session.execute(
                check_log_query,
                {
                    "request_id": str(uuid.uuid4())[:8],
                    "user_id": log_data.get("user_id", "anonymous"),
                    "check_type": log_data.get("filter_type", "input"),
                    "original_text": log_data["test_text"][:500],
                    "text_length": len(log_data["test_text"]),
                    "check_result": check_result,
                    "detection_score": log_data.get("detection_score", 0.0),
                    "detected_categories": json.dumps(log_data.get("blocked_categories", [])),
                    "detected_keywords": log_data.get("blocked_keywords", []),
                    "action_taken": action,
                    "processing_time_ms": log_data.get("processing_time_ms", 0)
                }
            )
            await session.commit()

            return str(log.id)

    @staticmethod
    async def get_logs(
        limit: int = 50,
        offset: int = 0,
        filter_safe: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """로그 조회"""
        async with async_session() as session:
            query = select(GuardrailLog).order_by(GuardrailLog.created_at.desc())

            # 안전성 필터 적용
            if filter_safe is not None:
                query = query.where(GuardrailLog.is_safe == filter_safe)

            # 검색 필터 적용
            if search:
                query = query.where(GuardrailLog.test_text.ilike(f"%{search}%"))

            # 페이지네이션 적용
            query = query.offset(offset).limit(limit)

            result = await session.execute(query)
            logs = result.scalars().all()

            return [
                {
                    "id": str(log.id),
                    "test_text": log.test_text,
                    "is_safe": log.is_safe,
                    "blocked_keywords": log.blocked_keywords or [],
                    "blocked_categories": log.blocked_categories or [],
                    "confidence_score": float(log.confidence_score) if log.confidence_score else 0.0,
                    "action_taken": log.action_taken,
                    "sensitivity": float(log.sensitivity) if log.sensitivity else 0.0,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in logs
            ]

    @staticmethod
    async def get_logs_count(
        filter_safe: Optional[bool] = None,
        search: Optional[str] = None
    ) -> int:
        """로그 개수 조회"""
        async with async_session() as session:
            query = select(func.count(GuardrailLog.id))

            # 안전성 필터 적용
            if filter_safe is not None:
                query = query.where(GuardrailLog.is_safe == filter_safe)

            # 검색 필터 적용
            if search:
                query = query.where(GuardrailLog.test_text.ilike(f"%{search}%"))

            result = await session.execute(query)
            return result.scalar() or 0

    @staticmethod
    async def get_log_statistics() -> Dict[str, Any]:
        """로그 통계 조회"""
        async with async_session() as session:
            # 전체 로그 수
            total_logs = await session.execute(select(func.count(GuardrailLog.id)))
            total_count = total_logs.scalar() or 0

            # 차단된 로그 수
            blocked_logs = await session.execute(
                select(func.count(GuardrailLog.id)).where(GuardrailLog.is_safe == False)
            )
            blocked_count = blocked_logs.scalar() or 0

            # 허용된 로그 수
            allowed_count = total_count - blocked_count

            # 최근 24시간 통계
            yesterday = datetime.now() - timedelta(hours=24)
            recent_logs = await session.execute(
                select(func.count(GuardrailLog.id)).where(GuardrailLog.created_at >= yesterday)
            )
            recent_count = recent_logs.scalar() or 0

            recent_blocked = await session.execute(
                select(func.count(GuardrailLog.id))
                .where(GuardrailLog.created_at >= yesterday)
                .where(GuardrailLog.is_safe == False)
            )
            recent_blocked_count = recent_blocked.scalar() or 0

            # 차단 비율 계산
            block_rate = (blocked_count / total_count * 100) if total_count > 0 else 0.0
            recent_block_rate = (recent_blocked_count / recent_count * 100) if recent_count > 0 else 0.0

            return {
                "total_logs": total_count,
                "blocked_logs": blocked_count,
                "allowed_logs": allowed_count,
                "block_rate": round(block_rate, 2),
                "recent_24h": {
                    "total": recent_count,
                    "blocked": recent_blocked_count,
                    "block_rate": round(recent_block_rate, 2)
                },
                "last_updated": datetime.now().isoformat()
            }

# 전역 database manager 인스턴스
db_manager = DatabaseManager()


# ============================================
# Raw Query Executor (for complex queries)
# ============================================

async def execute_raw_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    """
    Raw SQL 쿼리 실행
    - 복잡한 조인이나 집계 쿼리에 사용
    - %s 파라미터를 :param_n 형식으로 변환
    """
    async with async_session() as session:
        try:
            # %s를 :param_n으로 변환
            if params:
                converted_query = query
                param_dict = {}
                for i, param in enumerate(params):
                    param_name = f"param_{i}"
                    converted_query = converted_query.replace("%s", f":{param_name}", 1)
                    param_dict[param_name] = param
                result = await session.execute(text(converted_query), param_dict)
            else:
                result = await session.execute(text(query))

            # INSERT/UPDATE/DELETE의 경우 commit 수행
            query_upper = query.strip().upper()
            if query_upper.startswith('INSERT') or query_upper.startswith('UPDATE') or query_upper.startswith('DELETE'):
                await session.commit()

            # 결과를 딕셔너리 리스트로 변환
            rows = result.fetchall()
            if not rows:
                return []

            # 컬럼 이름 가져오기
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"❌ Raw query execution error: {e}")
            await session.rollback()
            raise