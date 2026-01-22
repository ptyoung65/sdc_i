"""
=============================================================================
[2026-01-22] 채팅 아카이브 서비스
=============================================================================
목적: 2주 경과 채팅을 압축하여 별도 테이블에 보관하고 원본 삭제
기능:
  - 2주 경과 채팅 자동 아카이브 (매일 자정)
  - 수동 아카이브 실행 API
  - 채팅 삭제 시 관련 벡터파일 자동 삭제
=============================================================================
"""

import os
import sys
import gzip
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import uvicorn

# ----- [2026-01-22] 로깅 설정 -----
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ----- [2026-01-22] 환경 변수 -----
DB_HOST = os.getenv('DB_HOST', '192.168.122.85')
DB_PORT = int(os.getenv('DB_PORT', 5433))
DB_USER = os.getenv('DB_USER', 'sdc_dev_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'sdc_dev_pass_2025')
DB_NAME = os.getenv('DB_NAME', 'sdc_dev')
ARCHIVE_DAYS = int(os.getenv('ARCHIVE_DAYS', 14))  # 아카이브 기준 일수 (기본 14일)
SERVICE_PORT = int(os.getenv('ARCHIVE_SERVICE_PORT', 3010))

# ----- [2026-01-22] 데이터베이스 연결 풀 -----
connection_pool = None

def init_db_pool():
    """데이터베이스 연결 풀 초기화"""
    global connection_pool
    try:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 10,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        logger.info(f"✅ PostgreSQL 연결 풀 초기화 성공 ({DB_HOST}:{DB_PORT}/{DB_NAME})")
        return True
    except Exception as e:
        logger.error(f"❌ PostgreSQL 연결 풀 초기화 실패: {e}")
        return False

def get_db_connection():
    """데이터베이스 연결 가져오기"""
    global connection_pool
    if connection_pool is None:
        init_db_pool()
    return connection_pool.getconn()

def release_db_connection(conn):
    """데이터베이스 연결 반환"""
    global connection_pool
    if connection_pool and conn:
        connection_pool.putconn(conn)

def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    """SQL 쿼리 실행"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        if cursor.description:
            results = cursor.fetchall()
            conn.commit()
            return [dict(row) for row in results]
        else:
            conn.commit()
            return []
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ 쿼리 실행 오류: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            release_db_connection(conn)

# ----- [2026-01-22] 아카이브 테이블 생성 -----
def ensure_archive_tables():
    """아카이브 테이블이 없으면 생성"""
    schema_sql = """
    -- 채팅 아카이브 테이블
    CREATE TABLE IF NOT EXISTS chat_archive (
        id VARCHAR(255) PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        title TEXT,
        chat_data_compressed BYTEA,
        original_size INTEGER,
        compressed_size INTEGER,
        message_count INTEGER DEFAULT 0,
        file_count INTEGER DEFAULT 0,
        created_at BIGINT,
        updated_at BIGINT,
        archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        archived_by VARCHAR(255) DEFAULT 'system',
        meta JSONB DEFAULT '{}'::jsonb
    );

    CREATE INDEX IF NOT EXISTS idx_chat_archive_user_id ON chat_archive(user_id);
    CREATE INDEX IF NOT EXISTS idx_chat_archive_created_at ON chat_archive(created_at);
    CREATE INDEX IF NOT EXISTS idx_chat_archive_archived_at ON chat_archive(archived_at);

    -- 아카이브 로그 테이블
    CREATE TABLE IF NOT EXISTS chat_archive_log (
        id SERIAL PRIMARY KEY,
        execution_type VARCHAR(50) NOT NULL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        chats_archived INTEGER DEFAULT 0,
        chats_deleted INTEGER DEFAULT 0,
        files_deleted INTEGER DEFAULT 0,
        total_size_before BIGINT DEFAULT 0,
        total_size_after BIGINT DEFAULT 0,
        status VARCHAR(50) DEFAULT 'running',
        error_message TEXT,
        executed_by VARCHAR(255) DEFAULT 'system'
    );
    """
    try:
        execute_query(schema_sql)
        logger.info("✅ 아카이브 테이블 확인/생성 완료")
        return True
    except Exception as e:
        logger.error(f"❌ 아카이브 테이블 생성 실패: {e}")
        return False

# ----- [2026-01-22] 채팅 데이터 압축 -----
def compress_chat_data(chat_data: dict) -> Tuple[bytes, int, int]:
    """
    채팅 데이터를 gzip으로 압축
    Returns: (압축된 데이터, 원본 크기, 압축 크기)
    """
    json_str = json.dumps(chat_data, ensure_ascii=False)
    original_bytes = json_str.encode('utf-8')
    original_size = len(original_bytes)

    compressed_bytes = gzip.compress(original_bytes)
    compressed_size = len(compressed_bytes)

    return compressed_bytes, original_size, compressed_size

def decompress_chat_data(compressed_data: bytes) -> dict:
    """압축된 채팅 데이터 복원"""
    decompressed_bytes = gzip.decompress(compressed_data)
    return json.loads(decompressed_bytes.decode('utf-8'))

# ----- [2026-01-22] 메시지에서 파일 ID 추출 -----
def extract_file_ids_from_chat(chat_data: dict) -> List[str]:
    """채팅 데이터에서 첨부된 파일 ID 목록 추출"""
    file_ids = []
    messages = chat_data.get('messages', [])

    for msg in messages:
        if isinstance(msg, dict) and 'files' in msg:
            files = msg.get('files', [])
            for f in (files or []):
                if isinstance(f, dict):
                    # file 객체 또는 직접 id
                    file_obj = f.get('file', f)
                    if isinstance(file_obj, dict):
                        file_id = file_obj.get('id')
                        if file_id:
                            file_ids.append(file_id)
                    elif isinstance(f.get('id'), str):
                        file_ids.append(f.get('id'))

    return list(set(file_ids))  # 중복 제거

# ----- [2026-01-22] 벡터파일 삭제 -----
def delete_vector_files(file_ids: List[str]) -> int:
    """
    파일 ID 목록에 해당하는 벡터파일 삭제
    Returns: 삭제된 파일 수
    """
    if not file_ids:
        return 0

    deleted_count = 0
    for file_id in file_ids:
        try:
            # file 테이블에서 삭제
            delete_query = "DELETE FROM file WHERE id = %s RETURNING id"
            result = execute_query(delete_query, (file_id,))
            if result:
                deleted_count += 1
                logger.debug(f"  - 파일 삭제: {file_id}")
        except Exception as e:
            logger.warning(f"  - 파일 삭제 실패 (id={file_id}): {e}")

    return deleted_count

# ----- [2026-01-22] 메인 아카이브 함수 -----
def run_archive(execution_type: str = 'auto', executed_by: str = 'system') -> Dict[str, Any]:
    """
    채팅 아카이브 실행

    Args:
        execution_type: 'auto' (자동) 또는 'manual' (수동)
        executed_by: 실행자 (system, admin 등)

    Returns:
        실행 결과 정보
    """
    logger.info(f"🚀 채팅 아카이브 시작 (type={execution_type}, by={executed_by})")

    # 아카이브 테이블 확인
    ensure_archive_tables()

    # 로그 레코드 생성
    log_query = """
        INSERT INTO chat_archive_log (execution_type, executed_by, status)
        VALUES (%s, %s, 'running')
        RETURNING id
    """
    log_result = execute_query(log_query, (execution_type, executed_by))
    log_id = log_result[0]['id'] if log_result else None

    result = {
        'log_id': log_id,
        'execution_type': execution_type,
        'executed_by': executed_by,
        'started_at': datetime.now().isoformat(),
        'chats_archived': 0,
        'chats_deleted': 0,
        'files_deleted': 0,
        'total_size_before': 0,
        'total_size_after': 0,
        'status': 'running',
        'errors': []
    }

    try:
        # 2주 경과 채팅 조회
        cutoff_timestamp = int((datetime.now() - timedelta(days=ARCHIVE_DAYS)).timestamp())

        query = """
            SELECT id, user_id, title, chat, created_at, updated_at
            FROM chat
            WHERE created_at < %s
              AND chat IS NOT NULL
            ORDER BY created_at ASC
        """
        old_chats = execute_query(query, (cutoff_timestamp,))

        logger.info(f"📋 아카이브 대상 채팅: {len(old_chats)}개 (기준: {ARCHIVE_DAYS}일 경과)")

        for chat_row in old_chats:
            chat_id = chat_row['id']
            user_id = chat_row['user_id']
            title = chat_row['title']
            chat_data = chat_row['chat']
            created_at = chat_row['created_at']
            updated_at = chat_row['updated_at']

            try:
                # 채팅 데이터 파싱
                if isinstance(chat_data, str):
                    chat_data = json.loads(chat_data)

                # 메시지 수 계산
                messages = chat_data.get('messages', [])
                message_count = len(messages)

                # 첨부 파일 ID 추출
                file_ids = extract_file_ids_from_chat(chat_data)
                file_count = len(file_ids)

                # 데이터 압축
                compressed_data, original_size, compressed_size = compress_chat_data(chat_data)
                result['total_size_before'] += original_size
                result['total_size_after'] += compressed_size

                # 메타데이터 생성
                meta = {
                    'archived_file_ids': file_ids,
                    'original_model': chat_data.get('models', []),
                    'archive_version': '1.0'
                }

                # 아카이브 테이블에 저장
                archive_query = """
                    INSERT INTO chat_archive
                    (id, user_id, title, chat_data_compressed, original_size, compressed_size,
                     message_count, file_count, created_at, updated_at, archived_by, meta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        chat_data_compressed = EXCLUDED.chat_data_compressed,
                        archived_at = CURRENT_TIMESTAMP
                """
                execute_query(archive_query, (
                    chat_id, user_id, title, compressed_data, original_size, compressed_size,
                    message_count, file_count, created_at, updated_at, executed_by, json.dumps(meta)
                ))
                result['chats_archived'] += 1

                # 벡터파일 삭제
                if file_ids:
                    deleted_files = delete_vector_files(file_ids)
                    result['files_deleted'] += deleted_files

                # 원본 채팅 삭제
                delete_chat_query = "DELETE FROM chat WHERE id = %s"
                execute_query(delete_chat_query, (chat_id,))
                result['chats_deleted'] += 1

                logger.info(f"  ✅ 아카이브 완료: {chat_id} (메시지: {message_count}, 파일: {file_count}, 압축률: {compressed_size/original_size*100:.1f}%)")

            except Exception as e:
                error_msg = f"채팅 아카이브 실패 (id={chat_id}): {e}"
                logger.error(f"  ❌ {error_msg}")
                result['errors'].append(error_msg)

        result['status'] = 'completed'
        result['completed_at'] = datetime.now().isoformat()

        # 로그 업데이트
        if log_id:
            update_log_query = """
                UPDATE chat_archive_log SET
                    completed_at = CURRENT_TIMESTAMP,
                    chats_archived = %s,
                    chats_deleted = %s,
                    files_deleted = %s,
                    total_size_before = %s,
                    total_size_after = %s,
                    status = %s,
                    error_message = %s
                WHERE id = %s
            """
            error_msg = '; '.join(result['errors']) if result['errors'] else None
            execute_query(update_log_query, (
                result['chats_archived'], result['chats_deleted'], result['files_deleted'],
                result['total_size_before'], result['total_size_after'],
                result['status'], error_msg, log_id
            ))

        logger.info(f"🎉 채팅 아카이브 완료: {result['chats_archived']}개 아카이브, {result['files_deleted']}개 파일 삭제")

    except Exception as e:
        result['status'] = 'failed'
        result['error_message'] = str(e)
        result['completed_at'] = datetime.now().isoformat()

        if log_id:
            execute_query(
                "UPDATE chat_archive_log SET status = 'failed', error_message = %s, completed_at = CURRENT_TIMESTAMP WHERE id = %s",
                (str(e), log_id)
            )

        logger.error(f"❌ 채팅 아카이브 실패: {e}")

    return result

# ----- [2026-01-22] FastAPI 앱 -----
app = FastAPI(
    title="Chat Archive Service",
    description="[2026-01-22] 채팅 아카이브 서비스 - 2주 경과 채팅 압축 보관",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 스케줄러
scheduler = BackgroundScheduler()

class ArchiveRequest(BaseModel):
    executed_by: str = 'admin'

class ArchiveResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화"""
    init_db_pool()
    ensure_archive_tables()

    # 매일 자정에 자동 아카이브 실행
    scheduler.add_job(
        lambda: run_archive('auto', 'scheduler'),
        CronTrigger(hour=0, minute=0),  # 매일 00:00
        id='daily_archive',
        replace_existing=True
    )
    scheduler.start()
    logger.info("✅ 채팅 아카이브 서비스 시작 (스케줄러: 매일 00:00)")

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 정리"""
    scheduler.shutdown()
    if connection_pool:
        connection_pool.closeall()
    logger.info("🛑 채팅 아카이브 서비스 종료")

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "service": "chat-archive"}

@app.post("/api/archive/run", response_model=ArchiveResponse)
async def run_archive_manual(request: ArchiveRequest, background_tasks: BackgroundTasks):
    """
    수동 아카이브 실행 API

    - 2주 경과 채팅을 압축하여 별도 테이블에 보관
    - 원본 채팅 및 관련 벡터파일 삭제
    """
    try:
        result = run_archive('manual', request.executed_by)
        return ArchiveResponse(
            success=result['status'] == 'completed',
            message=f"아카이브 완료: {result['chats_archived']}개 채팅, {result['files_deleted']}개 파일 처리",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/archive/status")
async def get_archive_status():
    """아카이브 상태 및 최근 실행 로그 조회"""
    try:
        # 최근 실행 로그
        logs = execute_query("""
            SELECT * FROM chat_archive_log
            ORDER BY started_at DESC
            LIMIT 10
        """)

        # 아카이브 통계
        stats = execute_query("""
            SELECT
                COUNT(*) as total_archived,
                SUM(message_count) as total_messages,
                SUM(file_count) as total_files,
                SUM(original_size) as total_original_size,
                SUM(compressed_size) as total_compressed_size,
                MIN(created_at) as oldest_chat,
                MAX(archived_at) as latest_archive
            FROM chat_archive
        """)

        # 스케줄러 상태
        next_run = None
        for job in scheduler.get_jobs():
            if job.id == 'daily_archive':
                next_run = job.next_run_time.isoformat() if job.next_run_time else None

        return {
            "scheduler": {
                "status": "running" if scheduler.running else "stopped",
                "next_run": next_run
            },
            "statistics": stats[0] if stats else {},
            "recent_logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/archive/logs")
async def get_archive_logs(limit: int = 20, offset: int = 0):
    """아카이브 실행 로그 조회"""
    try:
        logs = execute_query(f"""
            SELECT * FROM chat_archive_log
            ORDER BY started_at DESC
            LIMIT {limit} OFFSET {offset}
        """)

        total = execute_query("SELECT COUNT(*) as count FROM chat_archive_log")

        return {
            "logs": logs,
            "total": total[0]['count'] if total else 0,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/archive/search")
async def search_archived_chats(
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """아카이브된 채팅 검색"""
    try:
        conditions = ["1=1"]
        params = []

        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)

        if start_date:
            start_ts = int(datetime.fromisoformat(start_date.replace('Z', '+00:00')).timestamp())
            conditions.append("created_at >= %s")
            params.append(start_ts)

        if end_date:
            end_ts = int(datetime.fromisoformat(end_date.replace('Z', '+00:00')).timestamp())
            conditions.append("created_at <= %s")
            params.append(end_ts)

        where_clause = " AND ".join(conditions)

        # 압축 데이터 제외하고 메타정보만 조회
        query = f"""
            SELECT id, user_id, title, original_size, compressed_size,
                   message_count, file_count, created_at, updated_at,
                   archived_at, archived_by, meta
            FROM chat_archive
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        results = execute_query(query, tuple(params))

        count_query = f"SELECT COUNT(*) as count FROM chat_archive WHERE {where_clause}"
        total = execute_query(count_query, tuple(params[:-2]) if params[:-2] else None)

        return {
            "data": results,
            "total": total[0]['count'] if total else 0,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/archive/{chat_id}")
async def get_archived_chat(chat_id: str):
    """아카이브된 채팅 상세 조회 (압축 해제)"""
    try:
        result = execute_query(
            "SELECT * FROM chat_archive WHERE id = %s",
            (chat_id,)
        )

        if not result:
            raise HTTPException(status_code=404, detail="아카이브된 채팅을 찾을 수 없습니다")

        archive = result[0]

        # 압축 해제
        if archive.get('chat_data_compressed'):
            archive['chat_data'] = decompress_chat_data(bytes(archive['chat_data_compressed']))
            del archive['chat_data_compressed']  # 바이너리 데이터 제거

        return archive
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----- [2026-01-22] 메인 실행 -----
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Chat Archive Service')
    parser.add_argument('--run-now', action='store_true', help='즉시 아카이브 실행')
    parser.add_argument('--port', type=int, default=SERVICE_PORT, help='서비스 포트')
    args = parser.parse_args()

    if args.run_now:
        # 즉시 실행 모드
        init_db_pool()
        result = run_archive('manual', 'cli')
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        # 서버 모드
        uvicorn.run(
            "chat_archive_service:app",
            host="0.0.0.0",
            port=args.port,
            reload=False
        )
