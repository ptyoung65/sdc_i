-- Arthur AI Guardrails PostgreSQL Schema
-- 가드레일 키워드와 설정을 저장하기 위한 데이터베이스 스키마

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

-- 기본 키워드 데이터 삽입
INSERT INTO guardrail_keywords (id, text, category, enabled) VALUES
('1', '욕설/비속어', 'basic', TRUE),
('2', '성적 콘텐츠', 'basic', TRUE),
('3', '폭력적 콘텐츠', 'basic', TRUE),
('4', '개인정보', 'basic', TRUE),
('5', '유해한 지시사항', 'basic', TRUE),
('6', '허성 키워드입', 'personal', TRUE),
('7', '블랙리스트', 'blacklist', FALSE),
('8', '화이트리스트', 'whitelist', TRUE)
ON CONFLICT (id) DO NOTHING;

-- 기본 설정 값 삽입
INSERT INTO guardrail_settings (setting_key, setting_value, description) VALUES
('guardrails_enabled', 'true', '기본 가드레일 활성화 여부'),
('korean_guardrails_enabled', 'true', '한국어 가드레일 활성화 여부'),
('global_sensitivity', '0.7', '전역 민감도 설정 (0.0-1.0)'),
('auto_block', 'true', '자동 차단 기능 활성화 여부'),
('logging_enabled', 'true', '로깅 기능 활성화 여부')
ON CONFLICT (setting_key) DO NOTHING;

-- 업데이트 트리거 함수 (updated_at 자동 갱신)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 업데이트 트리거 생성
DROP TRIGGER IF EXISTS update_guardrail_keywords_updated_at ON guardrail_keywords;
CREATE TRIGGER update_guardrail_keywords_updated_at
    BEFORE UPDATE ON guardrail_keywords
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_guardrail_settings_updated_at ON guardrail_settings;
CREATE TRIGGER update_guardrail_settings_updated_at
    BEFORE UPDATE ON guardrail_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 권한 설정 (SDC 사용자에게 권한 부여)
GRANT ALL PRIVILEGES ON TABLE guardrail_keywords TO sdc_dev_user;
GRANT ALL PRIVILEGES ON TABLE guardrail_settings TO sdc_dev_user;
GRANT ALL PRIVILEGES ON TABLE guardrail_logs TO sdc_dev_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sdc_dev_user;