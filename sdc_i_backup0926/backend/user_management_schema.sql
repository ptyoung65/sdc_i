-- SDC 사용자 관리 시스템 데이터베이스 스키마
-- Created: 2025-09-29
-- Purpose: 사용자 정보, 인증, 챗봇 히스토리 관리

-- 1. 사용자 기본 정보 테이블
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,           -- 사용자 ID (OIDC에서 받는 ID)
    employee_number VARCHAR(20) UNIQUE,        -- 사번
    name VARCHAR(100) NOT NULL,                -- 이름
    department VARCHAR(100),                   -- 부서
    phone_number VARCHAR(20),                  -- 전화번호
    email VARCHAR(255),                        -- 이메일
    position VARCHAR(100),                     -- 직책
    is_active BOOLEAN DEFAULT true,            -- 활성화 상태
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,                      -- 마지막 로그인 시간
    login_count INTEGER DEFAULT 0             -- 총 로그인 횟수
);

-- 2. 사용자 세션 테이블 (접속 이력 관리)
CREATE TABLE user_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(user_id),
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP,
    ip_address VARCHAR(45),                    -- IPv4/IPv6 지원
    user_agent TEXT,                           -- 브라우저 정보
    session_duration INTEGER,                  -- 세션 지속 시간(초)
    is_active BOOLEAN DEFAULT true
);

-- 3. 챗봇 대화 히스토리 테이블
CREATE TABLE chat_conversations (
    conversation_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(user_id),
    session_id VARCHAR(100) REFERENCES user_sessions(session_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    title VARCHAR(200),                        -- 대화 제목
    is_active BOOLEAN DEFAULT true
);

-- 4. 챗봇 메시지 테이블
CREATE TABLE chat_messages (
    message_id VARCHAR(100) PRIMARY KEY,
    conversation_id VARCHAR(100) REFERENCES chat_conversations(conversation_id),
    user_id VARCHAR(50) REFERENCES users(user_id),
    message_type VARCHAR(20) NOT NULL,         -- 'user' 또는 'assistant'
    content TEXT NOT NULL,                     -- 메시지 내용
    tokens_used INTEGER,                       -- 사용된 토큰 수
    model_used VARCHAR(100),                   -- 사용된 AI 모델
    response_time_ms INTEGER,                  -- 응답 시간 (밀리초)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB                             -- 추가 메타데이터 (JSON 형태)
);

-- 5. 문서 업로드 히스토리 테이블
CREATE TABLE document_uploads (
    upload_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(user_id),
    session_id VARCHAR(100) REFERENCES user_sessions(session_id),
    filename VARCHAR(255) NOT NULL,
    file_size INTEGER,                         -- 파일 크기 (bytes)
    file_type VARCHAR(50),                     -- 파일 형식
    processing_method VARCHAR(50),             -- 처리 방법 (docling/alternative/basic)
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(20) DEFAULT 'pending', -- pending/completed/failed
    error_message TEXT                         -- 오류 메시지 (있는 경우)
);

-- 6. 사용자 통계 뷰 (실시간 통계 조회용)
CREATE VIEW user_statistics AS
SELECT
    u.user_id,
    u.name,
    u.department,
    u.login_count,
    u.last_login,
    COUNT(DISTINCT us.session_id) as total_sessions,
    COUNT(DISTINCT cc.conversation_id) as total_conversations,
    COUNT(cm.message_id) as total_messages,
    COUNT(CASE WHEN cm.message_type = 'user' THEN 1 END) as user_messages,
    COUNT(CASE WHEN cm.message_type = 'assistant' THEN 1 END) as ai_responses,
    COUNT(du.upload_id) as total_uploads,
    COALESCE(SUM(cm.tokens_used), 0) as total_tokens_used,
    COALESCE(AVG(cm.response_time_ms), 0) as avg_response_time
FROM users u
LEFT JOIN user_sessions us ON u.user_id = us.user_id
LEFT JOIN chat_conversations cc ON u.user_id = cc.user_id
LEFT JOIN chat_messages cm ON cc.conversation_id = cm.conversation_id
LEFT JOIN document_uploads du ON u.user_id = du.user_id
GROUP BY u.user_id, u.name, u.department, u.login_count, u.last_login;

-- 인덱스 생성 (성능 최적화)
CREATE INDEX idx_users_department ON users(department);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_sessions_login_time ON user_sessions(login_time);
CREATE INDEX idx_conversations_user_id ON chat_conversations(user_id);
CREATE INDEX idx_conversations_created_at ON chat_conversations(created_at);
CREATE INDEX idx_messages_conversation_id ON chat_messages(conversation_id);
CREATE INDEX idx_messages_user_id ON chat_messages(user_id);
CREATE INDEX idx_messages_created_at ON chat_messages(created_at);
CREATE INDEX idx_uploads_user_id ON document_uploads(user_id);
CREATE INDEX idx_uploads_upload_time ON document_uploads(upload_time);

-- 개발용 Mock 사용자 데이터 삽입
INSERT INTO users (user_id, employee_number, name, department, phone_number, email, position) VALUES
('11111', 'EMP001', '홍길동', 'IT개발팀', '010-1111-1111', 'hong@company.com', '선임연구원'),
('22222', 'EMP002', '강감찬', '기획팀', '010-2222-2222', 'kang@company.com', '팀장'),
('33333', 'EMP003', '이순신', '보안팀', '010-3333-3333', 'lee@company.com', '책임연구원');

-- 개발용 샘플 데이터 (테스트용)
INSERT INTO user_sessions (session_id, user_id, ip_address, user_agent) VALUES
('sess_001', '11111', '192.168.1.100', 'Mozilla/5.0 Chrome/118.0.0.0'),
('sess_002', '22222', '192.168.1.101', 'Mozilla/5.0 Firefox/119.0'),
('sess_003', '33333', '192.168.1.102', 'Mozilla/5.0 Safari/17.0');

-- 권한 설정 (PostgreSQL용)
-- 운영 환경에서는 적절한 권한 관리 필요
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sdc_dev_user;
GRANT SELECT ON user_statistics TO sdc_dev_user;