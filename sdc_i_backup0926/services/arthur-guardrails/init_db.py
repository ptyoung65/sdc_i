#!/usr/bin/env python3
"""
Initialize database for Arthur AI Guardrails
"""

import asyncio
import asyncpg
import os

async def create_database_and_tables():
    """데이터베이스 생성 및 테이블 초기화"""

    # 기본 연결로 데이터베이스 생성
    try:
        # postgres 데이터베이스에 연결하여 sdc_dev_db 생성
        conn = await asyncpg.connect(
            host="localhost",
            port=5433,
            user="sdc_dev_user",
            password="sdc_dev_pass_2025",
            database="postgres"  # 기본 데이터베이스에 연결
        )

        # 데이터베이스가 이미 존재하는지 확인
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'sdc_dev_db'"
        )

        if not db_exists:
            await conn.execute("CREATE DATABASE sdc_dev_db")
            print("✅ Database 'sdc_dev_db' created successfully")
        else:
            print("ℹ️ Database 'sdc_dev_db' already exists")

        await conn.close()

        # 이제 sdc_dev_db에 연결하여 테이블 생성
        conn = await asyncpg.connect(
            host="localhost",
            port=5433,
            user="sdc_dev_user",
            password="sdc_dev_pass_2025",
            database="sdc_dev_db"
        )

        # 스키마 적용
        schema_sql = """
        -- Arthur AI Guardrails PostgreSQL Schema

        -- 가드레일 키워드 테이블
        CREATE TABLE IF NOT EXISTS guardrail_keywords (
            id VARCHAR(50) PRIMARY KEY,
            text VARCHAR(255) NOT NULL,
            category VARCHAR(50) NOT NULL CHECK (category IN ('basic', 'personal', 'blacklist', 'whitelist')),
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- 가드레일 전역 설정 테이블
        CREATE TABLE IF NOT EXISTS guardrail_settings (
            id SERIAL PRIMARY KEY,
            setting_key VARCHAR(100) UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            description TEXT,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- 가드레일 로그 테이블 (테스트 및 실행 결과 저장)
        CREATE TABLE IF NOT EXISTS guardrail_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            test_text TEXT NOT NULL,
            is_safe BOOLEAN NOT NULL,
            blocked_keywords TEXT[], -- PostgreSQL array type
            blocked_categories TEXT[],
            confidence_score DECIMAL(3,2),
            action_taken VARCHAR(20) CHECK (action_taken IN ('allowed', 'blocked', 'flagged')),
            sensitivity DECIMAL(3,2),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- 인덱스 생성 (성능 최적화)
        CREATE INDEX IF NOT EXISTS idx_guardrail_keywords_category ON guardrail_keywords(category);
        CREATE INDEX IF NOT EXISTS idx_guardrail_keywords_enabled ON guardrail_keywords(enabled);
        CREATE INDEX IF NOT EXISTS idx_guardrail_logs_created_at ON guardrail_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_guardrail_logs_is_safe ON guardrail_logs(is_safe);
        """

        await conn.execute(schema_sql)
        print("✅ Tables and indexes created successfully")

        # 기본 데이터 삽입
        keywords_data = [
            ('1', '욕설/비속어', 'basic', True),
            ('2', '성적 콘텐츠', 'basic', True),
            ('3', '폭력적 콘텐츠', 'basic', True),
            ('4', '개인정보', 'basic', True),
            ('5', '유해한 지시사항', 'basic', True),
            ('6', '허성 키워드입', 'personal', True),
            ('7', '블랙리스트', 'blacklist', False),
            ('8', '화이트리스트', 'whitelist', True)
        ]

        # 키워드가 이미 존재하는지 확인
        existing_count = await conn.fetchval("SELECT COUNT(*) FROM guardrail_keywords")

        if existing_count == 0:
            await conn.executemany(
                "INSERT INTO guardrail_keywords (id, text, category, enabled) VALUES ($1, $2, $3, $4)",
                keywords_data
            )
            print(f"✅ Added {len(keywords_data)} default keywords")
        else:
            print(f"ℹ️ Keywords already exist ({existing_count} records)")

        # 설정 데이터 삽입
        settings_data = [
            ('guardrails_enabled', 'true', '기본 가드레일 활성화 여부'),
            ('korean_guardrails_enabled', 'true', '한국어 가드레일 활성화 여부'),
            ('global_sensitivity', '0.7', '전역 민감도 설정 (0.0-1.0)'),
            ('auto_block', 'true', '자동 차단 기능 활성화 여부'),
            ('logging_enabled', 'true', '로깅 기능 활성화 여부')
        ]

        # 설정이 이미 존재하는지 확인
        existing_settings = await conn.fetchval("SELECT COUNT(*) FROM guardrail_settings")

        if existing_settings == 0:
            await conn.executemany(
                "INSERT INTO guardrail_settings (setting_key, setting_value, description) VALUES ($1, $2, $3)",
                settings_data
            )
            print(f"✅ Added {len(settings_data)} default settings")
        else:
            print(f"ℹ️ Settings already exist ({existing_settings} records)")

        await conn.close()
        print("🛡️ Arthur AI Guardrails database initialization completed successfully!")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_database_and_tables())