-- =====================================================
-- 가드레일 데이터베이스 초기화 스크립트
-- 생성일: 2026-01-14
-- 수정일: 2026-01-14 (미사용 테이블 13개 제거)
-- 대상: guardrails_db
-- 테이블 수: 9개
-- =====================================================

-- 데이터베이스 생성 (필요시)
-- CREATE DATABASE guardrails_db WITH ENCODING 'UTF8';

-- =====================================================
-- 1. 트리거 함수 생성
-- =====================================================
CREATE OR REPLACE FUNCTION update_master_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 2. 기본 테이블 생성 (5개)
-- =====================================================

-- 2.1 guardrail_keywords: 키워드 관리
CREATE TABLE IF NOT EXISTS guardrail_keywords (
    id SERIAL PRIMARY KEY,
    text VARCHAR(255) NOT NULL,
    category VARCHAR(50) DEFAULT 'basic',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_keywords_category ON guardrail_keywords(category);
CREATE INDEX IF NOT EXISTS idx_keywords_enabled ON guardrail_keywords(enabled);

-- 2.2 guardrail_settings: 전역 설정
CREATE TABLE IF NOT EXISTS guardrail_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2.3 guardrail_logs: 실행 로그
CREATE TABLE IF NOT EXISTS guardrail_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_text TEXT NOT NULL,
    is_safe BOOLEAN NOT NULL,
    blocked_keywords VARCHAR[],
    blocked_categories VARCHAR[],
    confidence_score NUMERIC(3,2),
    action_taken VARCHAR(20),
    sensitivity NUMERIC(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON guardrail_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_logs_is_safe ON guardrail_logs(is_safe);

-- 2.4 guardrail_policies: 정책 정의
CREATE TABLE IF NOT EXISTS guardrail_policies (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT true,
    severity VARCHAR(20) DEFAULT 'medium',
    rules JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filter_type VARCHAR(30) DEFAULT 'input_filter',
    action_type VARCHAR(20) DEFAULT 'block'
);
CREATE INDEX IF NOT EXISTS idx_policies_category ON guardrail_policies(category);
CREATE INDEX IF NOT EXISTS idx_policies_enabled ON guardrail_policies(enabled);
CREATE INDEX IF NOT EXISTS idx_policies_severity ON guardrail_policies(severity);

-- 2.5 guardrail_check_logs: 상세 체크 로그
CREATE TABLE IF NOT EXISTS guardrail_check_logs (
    id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(100),
    session_id VARCHAR(100),
    user_id VARCHAR(255),
    user_email VARCHAR(255),
    check_type VARCHAR(30) NOT NULL DEFAULT 'input',
    model_id VARCHAR(100),
    original_text TEXT,
    processed_text TEXT,
    text_length INTEGER,
    policy_id VARCHAR(100),
    policy_name VARCHAR(100),
    check_result VARCHAR(30) NOT NULL DEFAULT 'pass',
    detection_score NUMERIC(5,4),
    detected_categories JSONB,
    detected_keywords TEXT[],
    detection_details JSONB,
    action_taken VARCHAR(30),
    action_reason TEXT,
    processing_time_ms INTEGER,
    client_ip VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_check_logs_created_at ON guardrail_check_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_check_logs_user_id ON guardrail_check_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_check_logs_result ON guardrail_check_logs(check_result);
CREATE INDEX IF NOT EXISTS idx_check_logs_policy_id ON guardrail_check_logs(policy_id);
CREATE INDEX IF NOT EXISTS idx_check_logs_date_result ON guardrail_check_logs(DATE(created_at), check_result);

-- =====================================================
-- 3. 마스터 테이블 생성 (4개)
-- =====================================================

-- 3.1 guardrail_master_policy_types: 정책 유형 마스터
CREATE TABLE IF NOT EXISTS guardrail_master_policy_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    type_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_master_policy_types_code ON guardrail_master_policy_types(code);
CREATE INDEX IF NOT EXISTS idx_master_policy_types_type_id ON guardrail_master_policy_types(type_id);

-- 3.2 guardrail_master_filter_types: 필터 유형 마스터
CREATE TABLE IF NOT EXISTS guardrail_master_filter_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    type_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_master_filter_types_code ON guardrail_master_filter_types(code);
CREATE INDEX IF NOT EXISTS idx_master_filter_types_type_id ON guardrail_master_filter_types(type_id);

-- 3.3 guardrail_master_severity_levels: 심각도 마스터
CREATE TABLE IF NOT EXISTS guardrail_master_severity_levels (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    level_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(20),
    priority INTEGER DEFAULT 0,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_master_severity_levels_code ON guardrail_master_severity_levels(code);
CREATE INDEX IF NOT EXISTS idx_master_severity_levels_level_id ON guardrail_master_severity_levels(level_id);

-- 3.4 guardrail_master_action_types: 조치 유형 마스터
CREATE TABLE IF NOT EXISTS guardrail_master_action_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    action_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_master_action_types_code ON guardrail_master_action_types(code);
CREATE INDEX IF NOT EXISTS idx_master_action_types_action_id ON guardrail_master_action_types(action_id);

-- =====================================================
-- 4. 트리거 생성
-- =====================================================

-- 마스터 테이블 업데이트 트리거
DROP TRIGGER IF EXISTS update_policy_types_updated_at ON guardrail_master_policy_types;
CREATE TRIGGER update_policy_types_updated_at
    BEFORE UPDATE ON guardrail_master_policy_types
    FOR EACH ROW EXECUTE FUNCTION update_master_updated_at();

DROP TRIGGER IF EXISTS update_filter_types_updated_at ON guardrail_master_filter_types;
CREATE TRIGGER update_filter_types_updated_at
    BEFORE UPDATE ON guardrail_master_filter_types
    FOR EACH ROW EXECUTE FUNCTION update_master_updated_at();

DROP TRIGGER IF EXISTS update_severity_levels_updated_at ON guardrail_master_severity_levels;
CREATE TRIGGER update_severity_levels_updated_at
    BEFORE UPDATE ON guardrail_master_severity_levels
    FOR EACH ROW EXECUTE FUNCTION update_master_updated_at();

DROP TRIGGER IF EXISTS update_action_types_updated_at ON guardrail_master_action_types;
CREATE TRIGGER update_action_types_updated_at
    BEFORE UPDATE ON guardrail_master_action_types
    FOR EACH ROW EXECUTE FUNCTION update_master_updated_at();

-- =====================================================
-- 5. 초기 데이터 삽입
-- =====================================================

-- 5.1 guardrail_settings: 전역 설정
INSERT INTO guardrail_settings (setting_key, setting_value, description) VALUES
('guardrails_enabled', 'true', '기본 가드레일 활성화 여부'),
('korean_guardrails_enabled', 'true', '한국어 가드레일 활성화 여부'),
('global_sensitivity', '0.7', '전역 민감도 설정 (0.0-1.0)'),
('auto_block', 'true', '자동 차단 기능 활성화 여부'),
('logging_enabled', 'true', '로깅 기능 활성화 여부')
ON CONFLICT (setting_key) DO NOTHING;

-- 5.2 guardrail_master_policy_types: 정책 유형 마스터
INSERT INTO guardrail_master_policy_types (code, type_id, name, description, is_active, sort_order) VALUES
('PT001', 'company', '회사정보 (Company)', '회사 관련 정보 보호 정책', true, 1),
('PT002', 'compliance', '규정준수 (Compliance)', '법률 및 규정 준수 관련 정책', true, 2),
('PT003', 'content', '콘텐츠 (Content)', '콘텐츠 품질 및 적합성 관련 정책', true, 3),
('PT004', 'privacy', '개인정보 (Privacy)', '개인정보 보호 관련 정책', true, 4),
('PT005', 'security', '보안 (Security)', '시스템 보안 관련 정책', true, 5)
ON CONFLICT (code) DO NOTHING;

-- 5.3 guardrail_master_filter_types: 필터 유형 마스터
INSERT INTO guardrail_master_filter_types (code, type_id, name, description, is_active, sort_order) VALUES
('FT001', 'input_filter', '입력 필터', '사용자 입력 검증 필터', true, 1),
('FT002', 'output_filter', '출력 필터', 'AI 응답 출력 검증 필터', true, 2),
('FT003', 'pii_detection', 'PII 탐지', '개인식별정보 탐지 필터', true, 3),
('FT004', 'toxicity', '유해성 탐지', '유해 콘텐츠 탐지 필터', true, 4),
('FT005', 'custom', '커스텀', '사용자 정의 필터', true, 5)
ON CONFLICT (code) DO NOTHING;

-- 5.4 guardrail_master_severity_levels: 심각도 마스터
INSERT INTO guardrail_master_severity_levels (code, level_id, name, color, priority, description, is_active, sort_order) VALUES
('SV001', 'critical', 'Critical (치명적)', '#dc2626', 100, '즉시 조치 필요, 시스템 중단 가능', true, 1),
('SV002', 'high', 'High (높음)', '#ea580c', 75, '빠른 조치 필요', true, 2),
('SV003', 'medium', 'Medium (중간)', '#ca8a04', 50, '주의 필요, 모니터링 대상', true, 3),
('SV004', 'low', 'Low (낮음)', '#16a34a', 25, '경미한 이슈, 참고용', true, 4)
ON CONFLICT (code) DO NOTHING;

-- 5.5 guardrail_master_action_types: 조치 유형 마스터
INSERT INTO guardrail_master_action_types (code, action_id, name, description, is_active, sort_order) VALUES
('AT001', 'block', '차단 (Block)', '요청을 완전히 차단하고 에러 응답 반환', true, 1),
('AT002', 'warn', '경고 (Warn)', '경고 메시지와 함께 처리 계속', true, 2),
('AT003', 'log_only', '로그만 (Log Only)', '로그만 기록하고 처리 계속', true, 3),
('AT004', 'replace', '대체 (Replace)', '민감 정보를 마스킹/대체 후 처리', true, 4)
ON CONFLICT (code) DO NOTHING;

-- 5.6 guardrail_keywords: 키워드 (243개)
INSERT INTO guardrail_keywords (text, category, enabled) VALUES
-- basic 카테고리 (욕설/비속어)
('욕설', 'basic', true),
('비속어', 'basic', true),
('씨발', 'basic', true),
('개새끼', 'basic', true),
('병신', 'basic', true),
('미친놈', 'basic', true),
('죽어', 'basic', true),
('꺼져', 'basic', true),
('닥쳐', 'basic', true),
('지랄', 'basic', true),
('새끼', 'basic', true),
('년', 'basic', true),
('놈', 'basic', true),
('바보', 'basic', true),
('멍청이', 'basic', true),
('등신', 'basic', true),
('찐따', 'basic', true),
('좆', 'basic', true),
('애미', 'basic', true),
('애비', 'basic', true),
('썅', 'basic', true),
('시발', 'basic', true),
('ㅅㅂ', 'basic', true),
('ㅂㅅ', 'basic', true),
('ㅈㄹ', 'basic', true),
('ㅆㅂ', 'basic', true),
('존나', 'basic', true),
('빡치', 'basic', true),
('엿먹어', 'basic', true),
('뒤져', 'basic', true),
('죽여버린다', 'basic', true),
('찢어버린다', 'basic', true),
('패버린다', 'basic', true),
('때려죽인다', 'basic', true),
('개같은', 'basic', true),
('돼지', 'basic', true),
('쓰레기', 'basic', true),
('쓰래기', 'basic', true),
('한심', 'basic', true),
('못난이', 'basic', true),
-- personal 카테고리 (개인정보)
('주민번호', 'personal', true),
('주민등록번호', 'personal', true),
('신용카드', 'personal', true),
('카드번호', 'personal', true),
('계좌번호', 'personal', true),
('비밀번호', 'personal', true),
('여권번호', 'personal', true),
('운전면허', 'personal', true),
('휴대폰번호', 'personal', true),
('전화번호', 'personal', true),
('핸드폰', 'personal', true),
('휴대전화', 'personal', true),
('생년월일', 'personal', true),
('주소', 'personal', true),
('집주소', 'personal', true),
('회사주소', 'personal', true),
('이메일', 'personal', true),
('email', 'personal', true),
('건강보험번호', 'personal', true),
('의료보험', 'personal', true),
('외국인등록번호', 'personal', true),
('사업자등록번호', 'personal', true),
('법인등록번호', 'personal', true),
('IP주소', 'personal', true),
('MAC주소', 'personal', true),
('GPS좌표', 'personal', true),
('위치정보', 'personal', true),
('차량번호', 'personal', true),
('자동차번호', 'personal', true),
('통장번호', 'personal', true),
('은행계좌', 'personal', true),
('CVC', 'personal', true),
('CVV', 'personal', true),
('유효기간', 'personal', true),
('PIN번호', 'personal', true),
('비번', 'personal', true),
('패스워드', 'personal', true),
('password', 'personal', true),
('암호', 'personal', true),
('인증번호', 'personal', true),
-- blacklist 카테고리 (보안/불법)
('해킹', 'blacklist', true),
('악성코드', 'blacklist', true),
('malware', 'blacklist', true),
('ransomware', 'blacklist', true),
('피싱', 'blacklist', true),
('스팸', 'blacklist', true),
('불법', 'blacklist', true),
('마약', 'blacklist', true),
('도박', 'blacklist', true),
('음란물', 'blacklist', true),
('virus', 'blacklist', true),
('trojan', 'blacklist', true),
('backdoor', 'blacklist', true),
('rootkit', 'blacklist', true),
('keylogger', 'blacklist', true),
('spyware', 'blacklist', true),
('SQL인젝션', 'blacklist', true),
('XSS공격', 'blacklist', true),
('DDoS', 'blacklist', true),
('botnet', 'blacklist', true),
('exploit', 'blacklist', true),
('shellcode', 'blacklist', true),
('reverse shell', 'blacklist', true),
('metasploit', 'blacklist', true),
('nmap', 'blacklist', true),
('burpsuite', 'blacklist', true),
('password cracker', 'blacklist', true),
('hashcat', 'blacklist', true),
('zero-day', 'blacklist', true),
('취약점', 'blacklist', true),
('암호화폐채굴', 'blacklist', true),
('cryptominer', 'blacklist', true),
('피라미드', 'blacklist', true),
('다단계', 'blacklist', true),
('폰지사기', 'blacklist', true),
('보이스피싱', 'blacklist', true),
('스미싱', 'blacklist', true),
('성매매', 'blacklist', true),
('원조교제', 'blacklist', true),
('불법촬영', 'blacklist', true),
-- whitelist 카테고리 (허용 키워드)
('도움말', 'whitelist', true),
('안녕하세요', 'whitelist', true),
('감사합니다', 'whitelist', true),
('질문', 'whitelist', true),
('문의', 'whitelist', true),
('요청', 'whitelist', true),
('설명', 'whitelist', true),
('정보', 'whitelist', true),
('검색', 'whitelist', true),
('확인', 'whitelist', true),
('안녕', 'whitelist', true),
('반갑습니다', 'whitelist', true),
('고맙습니다', 'whitelist', true),
('부탁드립니다', 'whitelist', true),
('알려주세요', 'whitelist', true),
('도와주세요', 'whitelist', true),
('가르쳐주세요', 'whitelist', true),
('문서', 'whitelist', true),
('자료', 'whitelist', true),
('데이터', 'whitelist', true),
('보고서', 'whitelist', true),
('분석', 'whitelist', true),
('통계', 'whitelist', true),
('결과', 'whitelist', true),
('요약', 'whitelist', true),
('정리', 'whitelist', true),
('목록', 'whitelist', true),
('리스트', 'whitelist', true),
('차트', 'whitelist', true),
('그래프', 'whitelist', true),
('표', 'whitelist', true),
('테이블', 'whitelist', true),
('작성', 'whitelist', true),
('생성', 'whitelist', true),
('만들기', 'whitelist', true),
('수정', 'whitelist', true),
('변경', 'whitelist', true),
('업데이트', 'whitelist', true),
('삭제', 'whitelist', true),
('제거', 'whitelist', true),
-- corporate 카테고리 (기업 정보)
('기밀문서', 'corporate', true),
('대외비', 'corporate', true),
('사내비밀', 'corporate', true),
('영업비밀', 'corporate', true),
('기업비밀', 'corporate', true),
('내부정보', 'corporate', true),
('미공개정보', 'corporate', true),
('인사정보', 'corporate', true),
('급여정보', 'corporate', true),
('연봉', 'corporate', true),
('성과급', 'corporate', true),
('보너스', 'corporate', true),
('인센티브', 'corporate', true),
('퇴직금', 'corporate', true),
('승진', 'corporate', true),
('인사발령', 'corporate', true),
('구조조정', 'corporate', true),
('해고', 'corporate', true),
('권고사직', 'corporate', true),
('감봉', 'corporate', true),
('징계', 'corporate', true),
('경고장', 'corporate', true),
('시말서', 'corporate', true),
('매출액', 'corporate', true),
('영업이익', 'corporate', true),
('순이익', 'corporate', true),
('재무제표', 'corporate', true),
('손익계산서', 'corporate', true),
('대차대조표', 'corporate', true),
('IR자료', 'corporate', true),
('투자계획', 'corporate', true),
('M&A', 'corporate', true),
('인수합병', 'corporate', true),
('계약서', 'corporate', true),
('견적서', 'corporate', true),
('입찰가격', 'corporate', true),
('원가정보', 'corporate', true),
('거래처목록', 'corporate', true),
('고객명단', 'corporate', true),
('특허기술', 'corporate', true),
('대표이사', 'corporate', true),
('CEO', 'corporate', true),
('사장', 'corporate', true),
('부사장', 'corporate', true),
('전무', 'corporate', true),
('상무', 'corporate', true),
('이사', 'corporate', true),
('감사', 'corporate', true),
('임원', 'corporate', true),
('경영진', 'corporate', true),
('이사회', 'corporate', true),
('주주총회', 'corporate', true),
('대주주', 'corporate', true),
('최대주주', 'corporate', true),
('지분율', 'corporate', true),
('스톡옵션', 'corporate', true),
('임원보수', 'corporate', true),
('퇴직위로금', 'corporate', true),
('경영권', 'corporate', true),
('의결권', 'corporate', true),
('조직도', 'corporate', true),
('조직구조', 'corporate', true),
('부서현황', 'corporate', true),
('인원현황', 'corporate', true),
('직원수', 'corporate', true),
('정원', 'corporate', true),
('TO', 'corporate', true),
('계약직', 'corporate', true),
('파견직', 'corporate', true),
('인턴', 'corporate', true),
('수습', 'corporate', true),
-- toxicity 카테고리 (유해 콘텐츠)
('폭력', 'toxicity', true),
('살인', 'toxicity', true),
('자살', 'toxicity', true),
('테러', 'toxicity', true),
('혐오발언', 'toxicity', true),
('인종차별', 'toxicity', true),
('성차별', 'toxicity', true),
('왕따', 'toxicity', true),
('괴롭힘', 'toxicity', true),
('협박', 'toxicity', true),
('사이버폭력', 'toxicity', true),
('명예훼손', 'toxicity', true)
ON CONFLICT DO NOTHING;

-- =====================================================
-- 완료 메시지
-- =====================================================
SELECT '가드레일 9개 테이블 및 초기 데이터 생성 완료' AS result;
