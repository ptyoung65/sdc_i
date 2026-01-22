-- =============================================================================
-- [2026-01-22] 채팅 아카이브 테이블 스키마
-- =============================================================================
-- 목적: 2주 경과 채팅을 압축하여 별도 테이블에 보관
-- 실행: psql -h HOST -p PORT -U USER -d DATABASE -f schema.sql
-- =============================================================================

-- 채팅 아카이브 테이블
CREATE TABLE IF NOT EXISTS chat_archive (
    id VARCHAR(255) PRIMARY KEY,                    -- 원본 chat.id
    user_id VARCHAR(255) NOT NULL,                  -- 원본 chat.user_id
    title TEXT,                                     -- 원본 chat.title
    chat_data_compressed BYTEA,                     -- 압축된 채팅 데이터 (gzip)
    original_size INTEGER,                          -- 원본 데이터 크기 (bytes)
    compressed_size INTEGER,                        -- 압축 데이터 크기 (bytes)
    message_count INTEGER DEFAULT 0,                -- 메시지 수
    file_count INTEGER DEFAULT 0,                   -- 첨부 파일 수
    created_at BIGINT,                              -- 원본 생성 시간 (Unix timestamp)
    updated_at BIGINT,                              -- 원본 수정 시간 (Unix timestamp)
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,-- 아카이브 시간
    archived_by VARCHAR(255) DEFAULT 'system',      -- 아카이브 실행자 (system/manual)
    meta JSONB DEFAULT '{}'::jsonb                  -- 추가 메타데이터
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_chat_archive_user_id ON chat_archive(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_archive_created_at ON chat_archive(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_archive_archived_at ON chat_archive(archived_at);

-- 아카이브 로그 테이블 (실행 이력)
CREATE TABLE IF NOT EXISTS chat_archive_log (
    id SERIAL PRIMARY KEY,
    execution_type VARCHAR(50) NOT NULL,            -- 'auto' (자동) / 'manual' (수동)
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 시작 시간
    completed_at TIMESTAMP,                         -- 완료 시간
    chats_archived INTEGER DEFAULT 0,               -- 아카이브된 채팅 수
    chats_deleted INTEGER DEFAULT 0,                -- 삭제된 채팅 수
    files_deleted INTEGER DEFAULT 0,                -- 삭제된 파일 수
    total_size_before BIGINT DEFAULT 0,             -- 아카이브 전 총 크기
    total_size_after BIGINT DEFAULT 0,              -- 아카이브 후 총 크기 (압축)
    status VARCHAR(50) DEFAULT 'running',           -- 'running', 'completed', 'failed'
    error_message TEXT,                             -- 오류 메시지
    executed_by VARCHAR(255) DEFAULT 'system'       -- 실행자
);

-- 코멘트 추가
COMMENT ON TABLE chat_archive IS '[2026-01-22] 2주 경과 채팅 압축 보관 테이블';
COMMENT ON TABLE chat_archive_log IS '[2026-01-22] 채팅 아카이브 실행 로그';
COMMENT ON COLUMN chat_archive.chat_data_compressed IS 'gzip 압축된 원본 chat.chat JSON 데이터';
COMMENT ON COLUMN chat_archive.meta IS '추가 정보: 삭제된 파일 목록, 원본 모델 정보 등';
