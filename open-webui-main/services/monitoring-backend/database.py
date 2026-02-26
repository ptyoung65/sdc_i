"""
PostgreSQL 데이터베이스 연결 모듈
실시간 데이터베이스 연결만 사용 (목 데이터, 로컬 스토리지 사용 금지)
"""
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import logging

load_dotenv()

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 데이터베이스 연결 풀
connection_pool = None

def init_db_pool():
    """데이터베이스 연결 풀 초기화"""
    global connection_pool

    try:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1,  # 최소 연결 수
            10,  # 최대 연결 수
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5433)),
            user=os.getenv('DB_USER', 'sdc_dev_user'),
            password=os.getenv('DB_PASSWORD', 'sdc_dev_pass_2025'),
            database=os.getenv('DB_NAME', 'sdc_dev')
        )
        logger.info("✅ PostgreSQL 연결 풀 초기화 성공")
        return True
    except Exception as e:
        logger.error(f"❌ PostgreSQL 연결 풀 초기화 실패: {e}")
        return False

def get_db_connection():
    """데이터베이스 연결 가져오기"""
    global connection_pool

    if connection_pool is None:
        init_db_pool()

    try:
        conn = connection_pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        raise

def release_db_connection(conn):
    """데이터베이스 연결 반환"""
    global connection_pool

    if connection_pool and conn:
        connection_pool.putconn(conn)

def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    """
    SQL 쿼리 실행 및 결과 반환

    Args:
        query: SQL 쿼리문
        params: 쿼리 파라미터 (선택)

    Returns:
        쿼리 결과 (딕셔너리 리스트)
    """
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(query, params)

        # SELECT 쿼리 또는 RETURNING이 있는 쿼리인 경우 결과 반환
        if cursor.description:
            results = cursor.fetchall()
            # INSERT/UPDATE/DELETE with RETURNING인 경우 commit 필요
            conn.commit()
            # RealDictRow를 일반 dict로 변환
            return [dict(row) for row in results]
        else:
            conn.commit()
            return []

    except Exception as e:
        if conn:
            conn.rollback()

        # ----- [2026-02-26] 유니코드 서로게이트(Surrogate) JSON 파싱 오류 자동 복구 시작 -----
        # 원인: 채팅 메시지에 이모지/특수문자가 깨진 유니코드 서로게이트(\uD800-\uDFFF)로
        #       저장된 경우, PostgreSQL이 chat::jsonb 캐스팅 시 JSON 파싱 오류 발생
        #       에러: "Unicode low surrogate must follow a high surrogate"
        # 처리: 1) 에러 메시지에 'surrogate' 포함 여부 확인
        #       2) chat::jsonb를 regexp_replace(chat::text, 서로게이트패턴, '')::jsonb로 교체
        #       3) 서로게이트 문자 제거 후 JSONB 재파싱으로 자동 복구
        #       4) 정상 쿼리 시에는 기존 로직 그대로 실행 (성능 영향 없음)
        error_msg = str(e).lower()
        if 'surrogate' in error_msg and ('chat::jsonb' in query or 'chat::json' in query):
            safe_query = query.replace(
                'c.chat::jsonb',
                "regexp_replace(c.chat::text, '\\\\u[Dd][89A-Fa-f][0-9A-Fa-f]{2}', '', 'g')::jsonb"
            )
            safe_query = safe_query.replace(
                'chat::jsonb',
                "regexp_replace(chat::text, '\\\\u[Dd][89A-Fa-f][0-9A-Fa-f]{2}', '', 'g')::jsonb"
            )
            if safe_query != query:
                try:
                    logger.warning("⚠️ 유니코드 서로게이트 감지, 안전 쿼리로 재시도")
                    cursor2 = conn.cursor(cursor_factory=RealDictCursor)
                    cursor2.execute(safe_query, params)
                    if cursor2.description:
                        results = cursor2.fetchall()
                        conn.commit()
                        cursor2.close()
                        return [dict(row) for row in results]
                    else:
                        conn.commit()
                        cursor2.close()
                        return []
                except Exception as retry_e:
                    if conn:
                        conn.rollback()
                    logger.error(f"❌ 안전 쿼리도 실패: {retry_e}")
        # ----- [2026-02-26] 유니코드 서로게이트(Surrogate) JSON 파싱 오류 자동 복구 종료 -----

        logger.error(f"❌ 쿼리 실행 오류: {e}")
        logger.error(f"쿼리: {query}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            release_db_connection(conn)

def close_db_pool():
    """데이터베이스 연결 풀 종료"""
    global connection_pool

    if connection_pool:
        connection_pool.closeall()
        logger.info("✅ PostgreSQL 연결 풀 종료")
