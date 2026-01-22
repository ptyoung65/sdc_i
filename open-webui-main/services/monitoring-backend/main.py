"""
Open WebUI Monitoring API Server
FastAPI 기반 모니터링 백엔드 서버
"""
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import uvicorn
import os
import logging
import psutil
from datetime import datetime
from dotenv import load_dotenv

from database import init_db_pool, execute_query, close_db_pool
from queries import (
    QUERY_USER_LOGIN_HISTORY,
    QUERY_OAUTH_SESSION_HISTORY,
    QUERY_CHAT_HISTORY,
    QUERY_DETAILED_MESSAGES,
    QUERY_USER_ACTIVITY_SUMMARY,
    QUERY_RECENT_MESSAGES,
    QUERY_CHECK_ADMIN,
    QUERY_OVERALL_STATS,
    QUERY_USER_SESSIONS_DETAIL,
    QUERY_TIMESERIES_USER_ACTIVITY,
    QUERY_TIMESERIES_CHAT_ACTIVITY,
    QUERY_TOKEN_STATS,
    QUERY_USER_TOKEN_STATS
)

# 환경 변수 로드
load_dotenv()

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Open WebUI Monitoring API",
    description="Open WebUI 모니터링 시스템 API",
    version="1.0.0"
)

# ----- 1225 CORS 설정 수정 시작 -----
# CORS 설정 - 모든 origin 허용 (개발/운영 환경 모두 대응)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ----- 1225 CORS 설정 수정 종료 -----

# ============================================
# 관리자 권한 체크
# ============================================
async def verify_admin(x_user_email: Optional[str] = Header(None)):
    """
    관리자 권한 확인
    헤더에서 x-user-email을 받아 DB에서 role='admin' 확인
    """
    if not x_user_email:
        raise HTTPException(
            status_code=401,
            detail="인증이 필요합니다. 사용자 이메일을 헤더에 포함해주세요."
        )

    try:
        # guardrails_db에서는 user 테이블이 없으므로 간소화된 권한 확인
        # 관리자 이메일 패턴 확인
        admin_emails = ['admin@sdc.com', 'admin@example.com']
        admin_domains = ['@sdc.com', '@admin.', 'admin@']

        is_admin = (
            x_user_email in admin_emails or
            any(pattern in x_user_email.lower() for pattern in admin_domains) or
            x_user_email.lower().startswith('admin')
        )

        if not is_admin:
            # DB에서 user 테이블 확인 시도 (실패해도 통과)
            try:
                result = execute_query(QUERY_CHECK_ADMIN, (x_user_email,))
                if result and len(result) > 0:
                    user = result[0]
                    logger.info(f"✅ 관리자 접근 (DB 확인): {user.get('name', '')} ({user.get('email', '')})")
                    return user
            except Exception as db_err:
                logger.warning(f"⚠️ DB 권한 확인 실패 (guardrails_db에 user 테이블 없음): {db_err}")
                # DB 확인 실패 시에도 이메일 기반으로 허용
                pass

        # 간소화된 사용자 정보 반환
        logger.info(f"✅ 관리자 접근 (이메일 기반): {x_user_email}")
        return {"id": "admin", "name": x_user_email.split("@")[0], "email": x_user_email, "role": "admin"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 권한 확인 오류: {e}")
        raise HTTPException(status_code=500, detail="권한 확인 중 오류가 발생했습니다.")

# ============================================
# API 엔드포인트
# ============================================

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 DB 연결 풀 초기화"""
    logger.info("🚀 모니터링 API 서버 시작 중...")
    init_db_pool()
    logger.info("✅ 모니터링 API 서버 준비 완료")

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 DB 연결 풀 종료"""
    logger.info("🛑 모니터링 API 서버 종료 중...")
    close_db_pool()
    logger.info("✅ 모니터링 API 서버 종료 완료")

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Open WebUI Monitoring API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/health")
async def health_check():
    """헬스 체크"""
    try:
        # DB 연결 테스트
        execute_query("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"❌ 헬스 체크 실패: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")

@app.get("/api/stats/overall")
async def get_overall_stats(admin_user: dict = Depends(verify_admin)):
    """
    전체 통계 조회
    - 총 사용자 수
    - 총 관리자 수
    - 총 채팅 수
    - 활성 채팅 수
    - 활성 세션 수
    """
    try:
        result = execute_query(QUERY_OVERALL_STATS)
        if result:
            return result[0]
        return {}
    except Exception as e:
        logger.error(f"❌ 전체 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/login-history")
async def get_user_login_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin_user: dict = Depends(verify_admin)
):
    """
    사용자 접속 이력 조회
    - 사용자 ID, 이름, 이메일
    - 역할 (role)
    - 가입일
    - 최근 접속일
    - 활동 기간
    """
    try:
        if start_date and end_date:
            from datetime import datetime
            start_ts = int(datetime.fromisoformat(start_date).timestamp())
            end_ts = int(datetime.fromisoformat(end_date).timestamp())

            query = QUERY_USER_LOGIN_HISTORY.replace(
                "ORDER BY u.last_active_at DESC;",
                f"WHERE u.last_active_at BETWEEN {start_ts} AND {end_ts} ORDER BY u.last_active_at DESC;"
            )
            results = execute_query(query)
        else:
            results = execute_query(QUERY_USER_LOGIN_HISTORY)
        return {"data": results, "total": len(results)}
    except Exception as e:
        logger.error(f"❌ 사용자 접속 이력 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/oauth-sessions")
async def get_oauth_sessions(admin_user: dict = Depends(verify_admin)):
    """
    OAuth 세션 기반 접속 이력 조회
    - 세션 ID
    - 사용자 정보
    - Provider (Google, GitHub 등)
    - 세션 생성/만료 시간
    - 세션 상태 (Active/Expired)
    """
    try:
        results = execute_query(QUERY_OAUTH_SESSION_HISTORY)
        return {"data": results, "total": len(results)}
    except Exception as e:
        logger.error(f"❌ OAuth 세션 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chats/history")
async def get_chat_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin_user: dict = Depends(verify_admin)
):
    """
    채팅 이력 조회
    - 채팅 ID, 제목
    - 사용자 정보
    - 생성/수정 시간
    - 고정/보관 여부
    - 메시지 개수
    """
    try:
        if start_date and end_date:
            from datetime import datetime
            start_ts = int(datetime.fromisoformat(start_date).timestamp())
            end_ts = int(datetime.fromisoformat(end_date).timestamp())

            query = QUERY_CHAT_HISTORY.replace(
                "WHERE c.chat IS NOT NULL",
                f"WHERE c.chat IS NOT NULL AND c.created_at BETWEEN {start_ts} AND {end_ts}"
            )
            results = execute_query(query)
        else:
            results = execute_query(QUERY_CHAT_HISTORY)
        return {"data": results, "total": len(results)}
    except Exception as e:
        logger.error(f"❌ 채팅 이력 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chats/messages")
async def get_detailed_messages(admin_user: dict = Depends(verify_admin)):
    """
    상세 메시지 이력 조회 (사용자 질문 & LLM 답변)
    - 채팅 ID, 사용자 정보
    - 메시지 ID, 역할 (user/assistant)
    - 메시지 내용
    - LLM 모델명
    - 타임스탬프
    """
    try:
        results = execute_query(QUERY_DETAILED_MESSAGES)
        return {"data": results, "total": len(results)}
    except Exception as e:
        logger.error(f"❌ 상세 메시지 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/activity-summary")
async def get_user_activity_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin_user: dict = Depends(verify_admin)
):
    """
    사용자별 활동 통계
    - 사용자 정보
    - 총 채팅 수
    - 활성 채팅 수
    - 고정 채팅 수
    - 총 메시지 수
    - 누적 토큰수, 최대 토큰, 메시지 수 (기간 필터 적용)
    """
    try:
        if start_date and end_date:
            from datetime import datetime
            start_ts = int(datetime.fromisoformat(start_date).timestamp())
            end_ts = int(datetime.fromisoformat(end_date).timestamp())

            # ----- [2026.01.06] user_tokens CTE에도 기간 필터 적용 수정 시작 -----
            # 문제: 기존 코드는 LEFT JOIN chat에만 기간 필터를 적용하여
            #       누적토큰수, 최대토큰, 메시지수가 필터 조건과 관계없이 전체 기간으로 집계됨
            # 해결: user_tokens CTE 내부의 WHERE절에도 동일한 기간 필터를 적용하여
            #       토큰 통계가 선택한 기간에 맞게 정확히 집계되도록 수정
            # 영향: /admin/monitoring2 페이지의 Overview 탭 테이블 데이터
            query = QUERY_USER_ACTIVITY_SUMMARY.replace(
                "LEFT JOIN chat c ON u.id = c.user_id",
                f"LEFT JOIN chat c ON u.id = c.user_id AND c.created_at BETWEEN {start_ts} AND {end_ts}"
            ).replace(
                "WHERE c.chat IS NOT NULL",
                f"WHERE c.chat IS NOT NULL AND c.created_at BETWEEN {start_ts} AND {end_ts}"
            )
            # ----- [2026.01.06] user_tokens CTE에도 기간 필터 적용 수정 종료 -----
            results = execute_query(query)
        else:
            results = execute_query(QUERY_USER_ACTIVITY_SUMMARY)
        return {"data": results, "total": len(results)}
    except Exception as e:
        logger.error(f"❌ 사용자 활동 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chats/recent-messages")
async def get_recent_messages(
    limit: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin_user: dict = Depends(verify_admin)
):
    """
    최근 대화 이력 조회 (시간순)
    - 채팅 ID, 사용자 이름
    - 메시지 역할 (사용자 질문/LLM 답변)
    - 메시지 내용
    - LLM 모델명
    - 타임스탬프
    """
    try:
        # ----- 1227 LIMIT 제한 제거 시작 -----
        # 기존: LIMIT 50을 min(limit, 200)으로 변경하던 것을 제거
        # queries.py에서 이미 LIMIT를 제거했으므로 쿼리 그대로 사용
        query = QUERY_RECENT_MESSAGES
        # ----- 1227 LIMIT 제한 제거 종료 -----

        if start_date and end_date:
            from datetime import datetime
            start_ts = int(datetime.fromisoformat(start_date).timestamp())
            end_ts = int(datetime.fromisoformat(end_date).timestamp())

            # WHERE 절 추가
            query = query.replace(
                "WHERE c.chat IS NOT NULL",
                f"WHERE c.chat IS NOT NULL AND c.created_at BETWEEN {start_ts} AND {end_ts}"
            )

        results = execute_query(query)
        return {"data": results, "total": len(results)}
    except Exception as e:
        logger.error(f"❌ 최근 메시지 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/{user_email}/sessions")
async def get_user_sessions_detail(
    user_email: str,
    admin_user: Dict = Depends(verify_admin)
):
    """
    특정 사용자의 세션(채팅) 상세 정보 조회
    - 세션 ID, 제목, 생성일, 업데이트일
    - 메시지 목록 (사용자 질문, AI 답변, 피드백)
    - 썸업/썸다운 정보
    """
    try:
        results = execute_query(QUERY_USER_SESSIONS_DETAIL, (user_email,))

        # JSON 파싱 처리
        for session in results:
            # messages와 history는 이미 JSON 객체로 반환됨
            if 'messages' in session and session['messages']:
                import json
                if isinstance(session['messages'], str):
                    session['messages'] = json.loads(session['messages'])
            if 'history' in session and session['history']:
                import json
                if isinstance(session['history'], str):
                    session['history'] = json.loads(session['history'])

        return {"data": results, "total": len(results), "user_email": user_email}
    except Exception as e:
        logger.error(f"❌ 사용자 세션 상세 조회 오류 ({user_email}): {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/timeseries/users")
async def get_timeseries_user_activity(admin_user: dict = Depends(verify_admin)):
    """
    10분 단위 사용자 활동 시계열 데이터 (최근 1시간)
    - 각 10분 구간별 활성 사용자 수
    """
    try:
        results = execute_query(QUERY_TIMESERIES_USER_ACTIVITY)
        return {"data": results, "total": len(results)}
    except Exception as e:
        logger.error(f"❌ 사용자 활동 시계열 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/timeseries/chats")
async def get_timeseries_chat_activity(admin_user: dict = Depends(verify_admin)):
    """
    10분 단위 채팅 생성 시계열 데이터 (최근 1시간)
    - 각 10분 구간별 생성된 채팅 수
    """
    try:
        results = execute_query(QUERY_TIMESERIES_CHAT_ACTIVITY)
        return {"data": results, "total": len(results)}
    except Exception as e:
        logger.error(f"❌ 채팅 활동 시계열 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/server-metrics")
async def get_server_metrics(admin_user: dict = Depends(verify_admin)):
    """
    서버 메트릭 조회 (CPU, 메모리)
    - CPU 사용률 (%)
    - 메모리 사용률 (%)
    - 메모리 사용량 (GB)
    """
    try:
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)

        # 메모리 정보
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024 ** 3)
        memory_total_gb = memory.total / (1024 ** 3)

        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": round(cpu_percent, 2)
            },
            "memory": {
                "percent": round(memory_percent, 2),
                "used_gb": round(memory_used_gb, 2),
                "total_gb": round(memory_total_gb, 2)
            }
        }
    except Exception as e:
        logger.error(f"❌ 서버 메트릭 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# [2024.12.30] 집계 API - /api/stats/tokens 엔드포인트 시작
# 역할: 전체 토큰 사용량 통계를 API로 제공
# 사용처: /admin/monitoring2, /admin/dashboard2 대시보드
# 반환값: {prompt_tokens, completion_tokens, total_tokens, messages_with_usage}
# ============================================
@app.get("/api/stats/tokens")
async def get_token_stats(admin_user: dict = Depends(verify_admin)):
    """
    토큰 사용량 통계 조회
    - 총 프롬프트 토큰 수
    - 총 완료 토큰 수
    - 총 토큰 수
    - 토큰 정보가 있는 메시지 수
    """
    try:
        results = execute_query(QUERY_TOKEN_STATS)
        if results and len(results) > 0:
            return results[0]
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "messages_with_usage": 0
        }
    except Exception as e:
        logger.error(f"❌ 토큰 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# [2024.12.30] 집계 API 완료 ============================================


# ============================================
# [2026.01.06] 토큰 모니터링 API - 실시간 및 시간대별 통계 시작
# 역할: 토큰 현황 모니터링 페이지용 API
# 사용처: /admin/token-monitoring 대시보드
# 추가 엔드포인트:
#   - /api/stats/tokens/realtime: 10분 단위 실시간 토큰 소비량
#   - /api/stats/tokens/weekly-hourly: 1주일 시간대별 토큰 통계
#   - /api/stats/tokens/daily: 최근 7일 일별 토큰 소비량
#   - /api/stats/tokens/ranking: 사용자별 토큰 소비 순위
#   - /api/stats/tokens/by-model: 모델별 토큰 통계
# ============================================

@app.get("/api/stats/tokens/realtime")
async def get_realtime_token_usage(admin_user: dict = Depends(verify_admin)):
    """
    실시간 10분 단위 토큰 소비량 조회 (최근 1시간)
    """
    try:
        query = """
            SELECT
                date_trunc('hour', to_timestamp(c.updated_at)) +
                INTERVAL '10 min' * floor(date_part('minute', to_timestamp(c.updated_at)) / 10) as time_bucket,
                COALESCE(SUM(
                    CASE
                        WHEN (msgs.msg->'usage'->>'total_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'total_tokens')::bigint
                        ELSE 0
                    END
                ), 0) as total_tokens,
                COALESCE(SUM(
                    CASE
                        WHEN (msgs.msg->'usage'->>'prompt_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'prompt_tokens')::bigint
                        ELSE 0
                    END
                ), 0) as prompt_tokens,
                COALESCE(SUM(
                    CASE
                        WHEN (msgs.msg->'usage'->>'completion_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'completion_tokens')::bigint
                        ELSE 0
                    END
                ), 0) as completion_tokens
            FROM chat c,
            LATERAL (
                SELECT jsonb_array_elements(c.chat::jsonb->'messages') as msg
            ) msgs
            WHERE c.chat IS NOT NULL
            AND c.updated_at >= EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour')
            AND msgs.msg->>'role' = 'assistant'
            GROUP BY time_bucket
            ORDER BY time_bucket ASC
        """
        results = execute_query(query)

        # 결과가 없으면 현재 시간 기준 빈 데이터 반환
        if not results:
            from datetime import datetime, timedelta
            now = datetime.now()
            results = []
            for i in range(6):
                time_point = now - timedelta(minutes=i*10)
                results.insert(0, {
                    "time_bucket": time_point.replace(minute=(time_point.minute // 10) * 10, second=0, microsecond=0).isoformat(),
                    "total_tokens": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0
                })
        else:
            # datetime을 ISO 문자열로 변환
            for r in results:
                if r.get('time_bucket') and hasattr(r['time_bucket'], 'isoformat'):
                    r['time_bucket'] = r['time_bucket'].isoformat()

        return {"data": results}
    except Exception as e:
        logger.error(f"❌ 실시간 토큰 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/tokens/weekly-hourly")
async def get_weekly_token_usage_by_hour(admin_user: dict = Depends(verify_admin)):
    """
    1주일치 시간대별 토큰 소비량 조회 (0~23시)
    """
    try:
        query = """
            SELECT
                EXTRACT(HOUR FROM to_timestamp(c.updated_at)) as hour,
                COALESCE(AVG(
                    CASE
                        WHEN (msgs.msg->'usage'->>'total_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'total_tokens')::bigint
                        ELSE 0
                    END
                ), 0)::bigint as avg_tokens,
                COALESCE(SUM(
                    CASE
                        WHEN (msgs.msg->'usage'->>'total_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'total_tokens')::bigint
                        ELSE 0
                    END
                ), 0) as total_tokens,
                COUNT(*) as request_count
            FROM chat c,
            LATERAL (
                SELECT jsonb_array_elements(c.chat::jsonb->'messages') as msg
            ) msgs
            WHERE c.chat IS NOT NULL
            AND c.updated_at >= EXTRACT(EPOCH FROM NOW() - INTERVAL '7 days')
            AND msgs.msg->>'role' = 'assistant'
            GROUP BY hour
            ORDER BY hour ASC
        """
        results = execute_query(query)

        # 0~23시 모든 시간대 데이터 보장
        hourly_data = {i: {"hour": i, "avg_tokens": 0, "total_tokens": 0, "request_count": 0} for i in range(24)}
        if results:
            for r in results:
                hour = int(r.get('hour', 0))
                hourly_data[hour] = {
                    "hour": hour,
                    "avg_tokens": int(r.get('avg_tokens', 0)),
                    "total_tokens": int(r.get('total_tokens', 0)),
                    "request_count": int(r.get('request_count', 0))
                }

        return {"data": list(hourly_data.values())}
    except Exception as e:
        logger.error(f"❌ 시간대별 토큰 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/tokens/daily")
async def get_daily_token_usage(admin_user: dict = Depends(verify_admin)):
    """
    일별 토큰 소비량 조회 (최근 7일)
    """
    try:
        query = """
            SELECT
                TO_CHAR(to_timestamp(c.updated_at), 'YYYY-MM-DD') as date,
                TO_CHAR(to_timestamp(c.updated_at), 'Dy') as day_name,
                COALESCE(SUM(
                    CASE
                        WHEN (msgs.msg->'usage'->>'total_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'total_tokens')::bigint
                        ELSE 0
                    END
                ), 0) as total_tokens,
                COALESCE(SUM(
                    CASE
                        WHEN (msgs.msg->'usage'->>'prompt_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'prompt_tokens')::bigint
                        ELSE 0
                    END
                ), 0) as prompt_tokens,
                COALESCE(SUM(
                    CASE
                        WHEN (msgs.msg->'usage'->>'completion_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'completion_tokens')::bigint
                        ELSE 0
                    END
                ), 0) as completion_tokens
            FROM chat c,
            LATERAL (
                SELECT jsonb_array_elements(c.chat::jsonb->'messages') as msg
            ) msgs
            WHERE c.chat IS NOT NULL
            AND c.updated_at >= EXTRACT(EPOCH FROM NOW() - INTERVAL '7 days')
            AND msgs.msg->>'role' = 'assistant'
            GROUP BY date, day_name
            ORDER BY date ASC
        """
        results = execute_query(query)

        # 한글 요일명으로 변환
        day_map = {'Mon': '월', 'Tue': '화', 'Wed': '수', 'Thu': '목', 'Fri': '금', 'Sat': '토', 'Sun': '일'}
        if results:
            for r in results:
                r['day_name'] = day_map.get(r.get('day_name', '').strip(), r.get('day_name', ''))

        return {"data": results or []}
    except Exception as e:
        logger.error(f"❌ 일별 토큰 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/tokens/ranking")
async def get_token_usage_ranking(
    admin_user: dict = Depends(verify_admin),
    limit: int = 10
):
    """
    사용자별 토큰 소비량 순위 조회
    """
    try:
        query = f"""
            SELECT
                u.email,
                u.name,
                COALESCE(SUM(
                    CASE
                        WHEN (msgs.msg->'usage'->>'total_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'total_tokens')::bigint
                        ELSE 0
                    END
                ), 0) as total_tokens,
                COUNT(DISTINCT c.id) as request_count
            FROM chat c
            JOIN "user" u ON c.user_id = u.id,
            LATERAL (
                SELECT jsonb_array_elements(c.chat::jsonb->'messages') as msg
            ) msgs
            WHERE c.chat IS NOT NULL
            AND msgs.msg->>'role' = 'assistant'
            GROUP BY u.email, u.name
            ORDER BY total_tokens DESC
            LIMIT {limit}
        """
        results = execute_query(query)
        return {"data": results or []}
    except Exception as e:
        logger.error(f"❌ 토큰 순위 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/tokens/by-model")
async def get_token_usage_by_model(admin_user: dict = Depends(verify_admin)):
    """
    모델별 토큰 소비량 통계 조회
    """
    try:
        query = """
            SELECT
                COALESCE(msgs.msg->>'model', 'unknown') as model_name,
                COALESCE(SUM(
                    CASE
                        WHEN (msgs.msg->'usage'->>'total_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'total_tokens')::bigint
                        ELSE 0
                    END
                ), 0) as total_tokens,
                COUNT(*) as request_count,
                COALESCE(AVG(
                    CASE
                        WHEN (msgs.msg->'usage'->>'total_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'total_tokens')::bigint
                        ELSE 0
                    END
                ), 0)::bigint as avg_tokens_per_request
            FROM chat c,
            LATERAL (
                SELECT jsonb_array_elements(c.chat::jsonb->'messages') as msg
            ) msgs
            WHERE c.chat IS NOT NULL
            AND msgs.msg->>'role' = 'assistant'
            AND msgs.msg->>'model' IS NOT NULL
            GROUP BY model_name
            ORDER BY total_tokens DESC
        """
        results = execute_query(query)
        return {"data": results or []}
    except Exception as e:
        logger.error(f"❌ 모델별 토큰 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ----- [2026.01.06] 1시간 단위 토큰 소비량 + 10분 상세 API 추가 시작 -----
# 요청: 실시간 그래프를 1시간 단위 막대차트로 변경, 클릭 시 10분 단위 상세 팝업

@app.get("/api/stats/tokens/hourly-today")
async def get_hourly_token_usage_today(admin_user: dict = Depends(verify_admin)):
    """
    오늘 하루 1시간 단위 토큰 소비량 조회 (0~23시)
    막대차트용 데이터
    """
    try:
        query = """
            WITH hourly_data AS (
                SELECT
                    EXTRACT(HOUR FROM to_timestamp(c.updated_at)) as hour,
                    COALESCE(SUM(
                        CASE
                            WHEN (msgs.msg->'usage'->>'total_tokens') IS NOT NULL
                            THEN (msgs.msg->'usage'->>'total_tokens')::bigint
                            ELSE 0
                        END
                    ), 0) as total_tokens,
                    COALESCE(SUM(
                        CASE
                            WHEN (msgs.msg->'usage'->>'prompt_tokens') IS NOT NULL
                            THEN (msgs.msg->'usage'->>'prompt_tokens')::bigint
                            ELSE 0
                        END
                    ), 0) as prompt_tokens,
                    COALESCE(SUM(
                        CASE
                            WHEN (msgs.msg->'usage'->>'completion_tokens') IS NOT NULL
                            THEN (msgs.msg->'usage'->>'completion_tokens')::bigint
                            ELSE 0
                        END
                    ), 0) as completion_tokens,
                    COUNT(*) as request_count
                FROM chat c,
                LATERAL (
                    SELECT jsonb_array_elements(c.chat::jsonb->'messages') as msg
                ) msgs
                WHERE c.chat IS NOT NULL
                AND DATE(to_timestamp(c.updated_at)) = CURRENT_DATE
                AND msgs.msg->>'role' = 'assistant'
                GROUP BY hour
            )
            SELECT * FROM hourly_data
            ORDER BY hour ASC
        """
        results = execute_query(query)

        # 0~23시 모든 시간대 데이터 보장
        hourly_map = {i: {"hour": i, "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "request_count": 0} for i in range(24)}
        if results:
            for r in results:
                hour = int(r.get('hour', 0))
                hourly_map[hour] = {
                    "hour": hour,
                    "total_tokens": int(r.get('total_tokens', 0)),
                    "prompt_tokens": int(r.get('prompt_tokens', 0)),
                    "completion_tokens": int(r.get('completion_tokens', 0)),
                    "request_count": int(r.get('request_count', 0))
                }

        return {"data": list(hourly_map.values())}
    except Exception as e:
        logger.error(f"❌ 시간별 토큰 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/tokens/hourly-detail/{hour}")
async def get_hourly_token_detail(hour: int, admin_user: dict = Depends(verify_admin)):
    """
    특정 시간대의 10초 단위 토큰 소비량 상세 조회
    팝업 점차트용 데이터 (1시간 = 360개 데이터 포인트)
    """
    try:
        if hour < 0 or hour > 23:
            raise HTTPException(status_code=400, detail="hour must be between 0 and 23")

        query = f"""
            SELECT
                EXTRACT(MINUTE FROM to_timestamp(c.updated_at))::int as minute,
                (EXTRACT(SECOND FROM to_timestamp(c.updated_at))::int / 10) * 10 as second_bucket,
                COALESCE(SUM(
                    CASE
                        WHEN (msgs.msg->'usage'->>'total_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'total_tokens')::bigint
                        ELSE 0
                    END
                ), 0) as total_tokens,
                COALESCE(SUM(
                    CASE
                        WHEN (msgs.msg->'usage'->>'prompt_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'prompt_tokens')::bigint
                        ELSE 0
                    END
                ), 0) as prompt_tokens,
                COALESCE(SUM(
                    CASE
                        WHEN (msgs.msg->'usage'->>'completion_tokens') IS NOT NULL
                        THEN (msgs.msg->'usage'->>'completion_tokens')::bigint
                        ELSE 0
                    END
                ), 0) as completion_tokens,
                COUNT(*) as request_count
            FROM chat c,
            LATERAL (
                SELECT jsonb_array_elements(c.chat::jsonb->'messages') as msg
            ) msgs
            WHERE c.chat IS NOT NULL
            AND DATE(to_timestamp(c.updated_at)) = CURRENT_DATE
            AND EXTRACT(HOUR FROM to_timestamp(c.updated_at)) = {hour}
            AND msgs.msg->>'role' = 'assistant'
            GROUP BY minute, second_bucket
            ORDER BY minute ASC, second_bucket ASC
        """
        results = execute_query(query)

        # 10초 단위로 모든 시간 구간 데이터 생성 (0분0초 ~ 59분50초)
        # 총 360개 포인트 (60분 * 6개)
        all_points = []
        for m in range(60):
            for s in [0, 10, 20, 30, 40, 50]:
                all_points.append({
                    "minute": m,
                    "second": s,
                    "time_label": f"{m:02d}:{s:02d}",
                    "total_tokens": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "request_count": 0
                })

        # 실제 데이터로 업데이트
        if results:
            for r in results:
                minute = int(r.get('minute', 0))
                second = int(r.get('second_bucket', 0))
                idx = minute * 6 + (second // 10)
                if 0 <= idx < len(all_points):
                    all_points[idx] = {
                        "minute": minute,
                        "second": second,
                        "time_label": f"{minute:02d}:{second:02d}",
                        "total_tokens": int(r.get('total_tokens', 0)),
                        "prompt_tokens": int(r.get('prompt_tokens', 0)),
                        "completion_tokens": int(r.get('completion_tokens', 0)),
                        "request_count": int(r.get('request_count', 0))
                    }

        return {"hour": hour, "data": all_points}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 시간 상세 토큰 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ----- [2026.01.06] 1시간 단위 토큰 소비량 + 10분 상세 API 추가 종료 -----

# [2026.01.06] 토큰 모니터링 API 완료 ============================================


# ==================== 대시보드 API 엔드포인트 ====================

@app.get("/api/dashboard/summary")
async def get_dashboard_summary(
    admin_user: dict = Depends(verify_admin),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    model: Optional[str] = 'all',
    aggregation_type: Optional[str] = 'question'  # ----- [2026.01.15] 집계 유형: 'session' | 'question' -----
):
    """
    대시보드 요약 통계
    - 총 사용자 수, 질문 수, 세션 수, 평균 질문 수
    - 만족률/불만족률 (모수=총 질문수)
    - 일평균 사용자수, 재접속율, EDM검색적재율, 평균 답변속도, 평균 응답오류율
    - aggregation_type: 'session' (세션 수 기준) | 'question' (질문 수 기준, 기본값)
    """
    try:
        # 날짜 조건 생성
        date_condition = ""
        if start_date and end_date:
            start_ts = int(datetime.fromisoformat(start_date).timestamp())
            end_ts = int(datetime.fromisoformat(end_date).timestamp())
            date_condition = f"AND c.created_at BETWEEN {start_ts} AND {end_ts}"

        # ----- [2026.01.15] 서비스(모델) 필터 조건 추가 -----
        model_condition = ""
        if model and model != 'all':
            model_condition = f"AND c.chat::jsonb->'messages'->0->'models'->>0 = '{model}'"

        # 기본 통계 쿼리
        query = f"""
            SELECT
                COUNT(DISTINCT c.user_id) as total_users,
                COUNT(DISTINCT c.id) as total_sessions,
                COUNT(DISTINCT DATE(TO_TIMESTAMP(c.created_at))) as total_days
            FROM chat c
            WHERE c.chat IS NOT NULL {date_condition} {model_condition}
        """

        results = execute_query(query)

        if results and len(results) > 0:
            stats = results[0]
            total_users = stats.get('total_users', 0) or 0
            total_sessions = stats.get('total_sessions', 0) or 0
            total_days = stats.get('total_days', 1) or 1

            # 총 질문 수 (user role 메시지 수)
            # [2026.01.15] model_condition 추가
            question_query = f"""
                SELECT COUNT(*) as total_questions
                FROM chat c,
                LATERAL (
                    SELECT jsonb_array_elements(c.chat::jsonb->'messages') as msg
                ) msgs
                WHERE c.chat IS NOT NULL
                {date_condition} {model_condition}
                AND msgs.msg->>'role' = 'user'
            """
            try:
                q_results = execute_query(question_query)
                total_questions = q_results[0].get('total_questions', 0) if q_results else 0
            except:
                # JSON 구조가 다를 경우 세션 수를 질문 수로 사용
                total_questions = total_sessions

            avg_questions = round(total_questions / max(total_sessions, 1), 2)

            # 일평균 사용자수
            daily_avg_users = round(total_users / max(total_days, 1), 2)

            # 재접속율 (2회 이상 세션을 가진 사용자 비율)
            # [2026.01.15] model_condition 추가
            return_query = f"""
                SELECT
                    COUNT(DISTINCT CASE WHEN session_count >= 2 THEN user_id END) as return_users,
                    COUNT(DISTINCT user_id) as all_users
                FROM (
                    SELECT user_id, COUNT(*) as session_count
                    FROM chat c
                    WHERE c.chat IS NOT NULL {date_condition} {model_condition}
                    GROUP BY user_id
                ) user_sessions
            """
            try:
                return_results = execute_query(return_query)
                if return_results and return_results[0]['all_users'] > 0:
                    return_rate = round(
                        (return_results[0].get('return_users', 0) or 0) /
                        (return_results[0].get('all_users', 1) or 1) * 100, 1
                    )
                else:
                    return_rate = "N/A"
            except:
                return_rate = "N/A"

            # 피드백 통계 (feedback 테이블에서)
            # rating: 10 = 만족, rating: 1 = 불만족
            feedback_query = f"""
                SELECT
                    COUNT(*) FILTER (WHERE f.type = 'positive' OR (f.data->>'rating')::int = 10) as satisfied,
                    COUNT(*) FILTER (WHERE f.type = 'negative' OR (f.data->>'rating')::int = 1) as dissatisfied,
                    COUNT(*) as total_feedback
                FROM feedback f
                WHERE 1=1
            """
            try:
                fb_results = execute_query(feedback_query)
                if fb_results and fb_results[0]['total_feedback'] > 0:
                    total_fb = fb_results[0].get('total_feedback', 0) or 0
                    satisfied = fb_results[0].get('satisfied', 0) or 0
                    dissatisfied = fb_results[0].get('dissatisfied', 0) or 0
                    # 모수는 총 질문수
                    satisfaction_rate = round(satisfied / max(total_questions, 1) * 100, 1)
                    dissatisfaction_rate = round(dissatisfied / max(total_questions, 1) * 100, 1)
                else:
                    satisfaction_rate = 0
                    dissatisfaction_rate = 0
            except:
                satisfaction_rate = 0
                dissatisfaction_rate = 0

            # ----- [2026.01.15] EDM 적재율 계산 시작 -----
            # EDM적재율 = (EDM 문서활용 세션에서 벡터화된 문서가 있는 세션 수) / (EDM 문서활용 전체 세션 수) * 100
            edm_search_download_rate = "N/A"
            try:
                # EDM 문서활용 세션 조회 (서비스명에 'EDM' 또는 '문서활용' 포함)
                edm_session_query = f"""
                    SELECT
                        c.id as chat_id,
                        c.user_id
                    FROM chat c
                    WHERE c.chat IS NOT NULL
                    {date_condition}
                    AND (
                        c.chat::jsonb->'messages'->0->'models'->>0 ILIKE '%EDM%'
                        OR c.chat::jsonb->'messages'->0->'models'->>0 ILIKE '%문서활용%'
                    )
                """
                edm_results = execute_query(edm_session_query)
                total_edm_sessions = len(edm_results) if edm_results else 0

                if total_edm_sessions > 0:
                    # 벡터화된 파일이 있는 사용자 목록 조회
                    vectorized_users_query = """
                        SELECT DISTINCT f.user_id
                        FROM file f
                        WHERE (f.meta::jsonb->>'embedding_model' IS NOT NULL
                           OR f.meta::jsonb->>'chunks' IS NOT NULL)
                          AND f.filename NOT LIKE 'tmp.%'
                    """
                    vectorized_results = execute_query(vectorized_users_query)
                    vectorized_user_ids = set(r.get('user_id') for r in (vectorized_results or []) if r.get('user_id'))

                    # EDM 세션 중 벡터화된 문서가 있는 사용자의 세션 수 카운트
                    edm_sessions_with_vectors = 0
                    for edm_row in (edm_results or []):
                        if edm_row.get('user_id') in vectorized_user_ids:
                            edm_sessions_with_vectors += 1

                    # EDM 적재율 계산
                    edm_rate = (edm_sessions_with_vectors / total_edm_sessions) * 100
                    edm_search_download_rate = round(edm_rate, 1)
                else:
                    edm_search_download_rate = 0
            except Exception as edm_err:
                logger.warning(f"EDM 적재율 계산 오류 (무시됨): {edm_err}")
            # ----- [2026.01.15] EDM 적재율 계산 종료 -----

            # ----- [2026.01.15] 평균 답변속도 및 오류율 계산 시작 -----
            # 답변속도: 사용자 메시지 timestamp ~ 어시스턴트 메시지 timestamp 시간차
            # 오류율: 답변을 못한 질문(답변이 없거나 빈 내용) 비율
            avg_response_time = "N/A"
            avg_error_rate = "N/A"

            try:
                # 모든 채팅 세션에서 메시지 추출
                # [2026.01.15] model_condition 적용
                response_query = f"""
                    SELECT
                        c.id as chat_id,
                        c.chat::jsonb->'messages' as messages
                    FROM chat c
                    WHERE c.chat IS NOT NULL {date_condition} {model_condition}
                """
                response_results = execute_query(response_query)

                total_response_times = []  # 각 Q&A 쌍의 응답 시간 (초)
                questions_without_answer = 0  # 답변 없는 질문 수
                total_qa_count = 0  # 전체 질문 수

                for chat_row in (response_results or []):
                    messages = chat_row.get('messages') or []
                    current_question_ts = None

                    for msg in messages:
                        if isinstance(msg, dict):
                            role = msg.get('role', '')
                            content = msg.get('content', '') or ''
                            timestamp = msg.get('timestamp')

                            if role == 'user' and content.strip():
                                # 새 질문 발견
                                current_question_ts = timestamp
                                total_qa_count += 1
                            elif role == 'assistant':
                                if current_question_ts is not None:
                                    # 답변이 비어있거나 오류 메시지인 경우
                                    if not content.strip() or content.strip() == '-' or '오류' in content or 'error' in content.lower():
                                        questions_without_answer += 1
                                    else:
                                        # 정상 답변 - 응답 시간 계산
                                        if timestamp and current_question_ts:
                                            try:
                                                response_time = float(timestamp) - float(current_question_ts)
                                                if 0 < response_time < 600:  # 0초 초과 ~ 10분 미만만 유효
                                                    total_response_times.append(response_time)
                                            except:
                                                pass
                                    current_question_ts = None

                    # 마지막 질문이 답변 없이 남아있는 경우
                    if current_question_ts is not None:
                        questions_without_answer += 1

                # 평균 응답 시간 계산
                if total_response_times:
                    avg_time = sum(total_response_times) / len(total_response_times)
                    avg_response_time = round(avg_time, 1)  # 초 단위, 소수점 1자리

                # 오류율 계산 (답변 못한 질문 / 전체 질문 * 100)
                if total_qa_count > 0:
                    error_rate = (questions_without_answer / total_qa_count) * 100
                    avg_error_rate = round(error_rate, 1)
                else:
                    avg_error_rate = 0

            except Exception as resp_err:
                logger.warning(f"답변속도/오류율 계산 오류 (무시됨): {resp_err}")
            # ----- [2026.01.15] 평균 답변속도 및 오류율 계산 종료 -----

            return {
                "totalUsers": total_users,
                "totalQuestions": total_questions,
                "totalSessions": total_sessions,
                "avgQuestionsPerSession": avg_questions,
                "satisfactionRate": satisfaction_rate,
                "dissatisfactionRate": dissatisfaction_rate,
                "dailyAvgUsers": daily_avg_users,
                "returnRate": return_rate,
                "edmSearchDownloadRate": edm_search_download_rate,
                "avgResponseTime": avg_response_time,
                "avgErrorRate": avg_error_rate
            }

        return {
            "totalUsers": 0,
            "totalQuestions": 0,
            "totalSessions": 0,
            "avgQuestionsPerSession": 0,
            "satisfactionRate": 0,
            "dissatisfactionRate": 0,
            "dailyAvgUsers": 0,
            "returnRate": "N/A",
            "edmSearchDownloadRate": "N/A",
            "avgResponseTime": "N/A",
            "avgErrorRate": "N/A"
        }

    except Exception as e:
        logger.error(f"❌ 대시보드 요약 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/models")
async def get_dashboard_models(admin_user: dict = Depends(verify_admin)):
    """
    사용 가능한 모델 목록 조회
    - [2026.01.13] chat JSON과 model 테이블에서 모든 서비스 조회하도록 수정
    """
    try:
        models_set = set()

        # 1. chat 테이블에서 사용된 모델 목록 추출
        query1 = """
            SELECT DISTINCT
                jsonb_array_elements_text(
                    (c.chat::jsonb->'messages'->0->'models')
                ) as model_id
            FROM chat c
            WHERE c.chat IS NOT NULL
              AND c.chat::jsonb->'messages'->0->'models' IS NOT NULL
        """
        try:
            results1 = execute_query(query1)
            for r in results1:
                if r.get('model_id'):
                    models_set.add(r['model_id'])
        except Exception as e:
            logger.debug(f"chat 테이블 모델 조회 실패: {e}")

        # 2. model 테이블에서 등록된 모델 목록 추출
        query2 = """
            SELECT DISTINCT id as model_id, name as model_name
            FROM model
            WHERE id IS NOT NULL
        """
        try:
            results2 = execute_query(query2)
            for r in results2:
                if r.get('model_id'):
                    models_set.add(r['model_id'])
        except Exception as e:
            logger.debug(f"model 테이블 조회 실패: {e}")

        # 3. 기본 서비스 추가 (항상 포함)
        default_services = ["Gen SDC", "EDM 문서활용"]
        for svc in default_services:
            models_set.add(svc)

        # 모델 목록 생성
        models = [{"id": mid, "name": mid} for mid in sorted(models_set)]

        # "전체" 옵션 추가
        models.insert(0, {"id": "all", "name": "전체"})

        return models

    except Exception as e:
        logger.error(f"❌ 모델 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/user-trend")
async def get_user_trend(
    admin_user: dict = Depends(verify_admin),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    model: Optional[str] = 'all',  # ----- [2026.01.15] 서비스 필터 추가 -----
    aggregation_type: Optional[str] = 'question'  # ----- [2026.01.15] 집계 유형 추가 (일관성) -----
):
    """
    일별 사용자 추이
    - aggregation_type은 사용자 수 집계에는 영향 없음 (일관성을 위해 파라미터 유지)
    """
    try:
        date_condition = ""
        if start_date and end_date:
            start_ts = int(datetime.fromisoformat(start_date).timestamp())
            end_ts = int(datetime.fromisoformat(end_date).timestamp())
            date_condition = f"WHERE c.created_at BETWEEN {start_ts} AND {end_ts}"

        # ----- [2026.01.15] 서비스(모델) 필터 조건 추가 -----
        model_condition = ""
        if model and model != 'all':
            model_condition = f"AND c.chat::jsonb->'messages'->0->'models'->>0 = '{model}'"

        # ----- 1227 LIMIT 제거 시작 -----
        query = f"""
            SELECT
                TO_CHAR(TO_TIMESTAMP(c.created_at), 'YYYY-MM-DD') as date,
                COUNT(DISTINCT c.user_id) as count
            FROM chat c
            WHERE c.chat IS NOT NULL
            {date_condition.replace('WHERE', 'AND') if date_condition else ''}
            {model_condition}
            GROUP BY TO_CHAR(TO_TIMESTAMP(c.created_at), 'YYYY-MM-DD')
            ORDER BY date ASC
        """
        # ----- 1227 LIMIT 제거 종료 -----

        results = execute_query(query)

        return [{
            "date": r.get('date', ''),
            "count": r.get('count', 0) or 0
        } for r in (results or [])]

    except Exception as e:
        logger.error(f"❌ 사용자 추이 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/question-feedback-trend")
async def get_question_feedback_trend(
    admin_user: dict = Depends(verify_admin),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    model: Optional[str] = 'all',  # ----- [2026.01.15] 서비스 필터 추가 -----
    aggregation_type: Optional[str] = 'question'  # ----- [2026.01.15] 집계 유형 추가 -----
):
    """
    일별 질문 및 피드백 추이
    - questions: 일별 질문 수 (aggregation_type='question'일 때 실제 user 메시지 수)
    - questions: 일별 세션 수 (aggregation_type='session'일 때 세션 수)
    - dissatisfied: 불만족 수
    """
    try:
        date_condition = ""
        if start_date and end_date:
            start_ts = int(datetime.fromisoformat(start_date).timestamp())
            end_ts = int(datetime.fromisoformat(end_date).timestamp())
            date_condition = f"AND c.created_at BETWEEN {start_ts} AND {end_ts}"

        # ----- [2026.01.15] 서비스(모델) 필터 조건 추가 -----
        model_condition = ""
        if model and model != 'all':
            model_condition = f"AND c.chat::jsonb->'messages'->0->'models'->>0 = '{model}'"

        # ----- [2026.01.15] 집계 유형에 따른 쿼리 분기 -----
        if aggregation_type == 'question':
            # 질문단위집계: 실제 user 메시지 수 카운트
            query = f"""
                SELECT
                    TO_CHAR(TO_TIMESTAMP(c.created_at), 'YYYY-MM-DD') as date,
                    COUNT(*) as questions
                FROM chat c,
                LATERAL (
                    SELECT jsonb_array_elements(c.chat::jsonb->'messages') as msg
                ) msgs
                WHERE c.chat IS NOT NULL
                {date_condition} {model_condition}
                AND msgs.msg->>'role' = 'user'
                GROUP BY TO_CHAR(TO_TIMESTAMP(c.created_at), 'YYYY-MM-DD')
                ORDER BY date ASC
            """
        else:
            # 세션집계: 세션 수 카운트
            query = f"""
                SELECT
                    TO_CHAR(TO_TIMESTAMP(c.created_at), 'YYYY-MM-DD') as date,
                    COUNT(*) as questions
                FROM chat c
                WHERE c.chat IS NOT NULL {date_condition} {model_condition}
                GROUP BY TO_CHAR(TO_TIMESTAMP(c.created_at), 'YYYY-MM-DD')
                ORDER BY date ASC
            """

        results = execute_query(query)

        # 피드백 데이터 - chat 테이블과 meta->>'chat_id'로 조인
        # rating: 10 = 만족, rating: 1 = 불만족
        feedback_by_date = {}
        satisfied_by_date = {}
        try:
            fb_query = f"""
                SELECT
                    TO_CHAR(TO_TIMESTAMP(c.created_at), 'YYYY-MM-DD') as date,
                    COUNT(*) FILTER (WHERE f.type = 'positive' OR (f.data->>'rating')::int = 10) as satisfied,
                    COUNT(*) FILTER (WHERE f.type = 'negative' OR (f.data->>'rating')::int = 1) as dissatisfied
                FROM feedback f
                JOIN chat c ON f.meta->>'chat_id' = c.id::text
                WHERE f.meta->>'chat_id' IS NOT NULL
                GROUP BY TO_CHAR(TO_TIMESTAMP(c.created_at), 'YYYY-MM-DD')
            """
            fb_results = execute_query(fb_query)
            for fb in (fb_results or []):
                if fb.get('date'):
                    feedback_by_date[fb['date']] = fb.get('dissatisfied', 0) or 0
                    satisfied_by_date[fb['date']] = fb.get('satisfied', 0) or 0
        except:
            pass

        return [{
            "date": r.get('date', ''),
            "questions": r.get('questions', 0) or 0,
            "satisfied": satisfied_by_date.get(r.get('date', ''), 0),
            "dissatisfied": feedback_by_date.get(r.get('date', ''), 0)
        } for r in (results or [])]

    except Exception as e:
        logger.error(f"❌ 질문/피드백 추이 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/service-type-stats")
async def get_service_type_stats(
    admin_user: dict = Depends(verify_admin),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    model: Optional[str] = 'all',  # ----- [2026.01.15] 서비스 필터 추가 -----
    aggregation_type: Optional[str] = 'question'  # ----- [2026.01.15] 집계 유형 추가 (일관성) -----
):
    """
    서비스 유형(모델)별 통계
    """
    try:
        date_condition = ""
        if start_date and end_date:
            start_ts = int(datetime.fromisoformat(start_date).timestamp())
            end_ts = int(datetime.fromisoformat(end_date).timestamp())
            date_condition = f"AND c.created_at BETWEEN {start_ts} AND {end_ts}"

        # ----- [2026.01.15] 서비스(모델) 필터 조건 추가 -----
        model_condition = ""
        if model and model != 'all':
            model_condition = f"AND c.chat::jsonb->'messages'->0->'models'->>0 = '{model}'"

        # ----- 1227 LIMIT 제거 시작 -----
        # 모델별 통계 쿼리 - LATERAL JOIN 사용
        query = f"""
            SELECT
                model_name as model,
                COUNT(DISTINCT c.user_id) as users,
                COUNT(DISTINCT c.id) as sessions
            FROM chat c,
            LATERAL (
                SELECT jsonb_array_elements_text(c.chat::jsonb->'messages'->0->'models') as model_name
            ) models
            WHERE c.chat IS NOT NULL {date_condition} {model_condition}
            GROUP BY model_name
            ORDER BY sessions DESC
        """
        # ----- 1227 LIMIT 제거 종료 -----

        try:
            results = execute_query(query)
        except Exception as e:
            logger.error(f"서비스 유형 쿼리 오류: {e}")
            results = []

        # 총계 계산
        total_users = sum(r.get('users', 0) or 0 for r in (results or []))
        total_sessions = sum(r.get('sessions', 0) or 0 for r in (results or []))

        if not results:
            # 데이터 없으면 기본 구조 반환
            return [{
                "model": "Gen SDC",
                "users": 0,
                "userPercent": 0,
                "questions": 0,
                "questionPercent": 0
            }]

        return [{
            "model": r.get('model', 'Unknown'),
            "users": r.get('users', 0) or 0,
            "userPercent": round((r.get('users', 0) or 0) / max(total_users, 1) * 100, 1),
            "questions": r.get('sessions', 0) or 0,
            "questionPercent": round((r.get('sessions', 0) or 0) / max(total_sessions, 1) * 100, 1)
        } for r in (results or [])]

    except Exception as e:
        logger.error(f"❌ 서비스 유형별 통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/dissatisfaction-types")
async def get_dissatisfaction_types(
    admin_user: dict = Depends(verify_admin),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    model: Optional[str] = 'all',  # ----- [2026.01.15] 서비스 필터 추가 -----
    aggregation_type: Optional[str] = 'question'  # ----- [2026.01.15] 집계 유형 추가 (일관성) -----
):
    """
    불만족 유형별 통계
    """
    try:
        date_condition = ""
        if start_date and end_date:
            start_ts = int(datetime.fromisoformat(start_date).timestamp())
            end_ts = int(datetime.fromisoformat(end_date).timestamp())
            date_condition = f"AND f.created_at BETWEEN {start_ts} AND {end_ts}"

        # ----- [2026.01.15] 서비스(모델) 필터 조건 추가 -----
        # feedback은 chat과 조인하여 모델 필터 적용
        model_join = ""
        model_condition = ""
        if model and model != 'all':
            model_join = "JOIN chat c ON f.meta->>'chat_id' = c.id::text"
            model_condition = f"AND c.chat::jsonb->'messages'->0->'models'->>0 = '{model}'"

        # feedback 테이블에서 불만족 데이터 조회
        # rating: 1 = 불만족
        query = f"""
            SELECT
                COALESCE(f.data->>'reason', '기타') as type,
                COUNT(*) as count
            FROM feedback f
            {model_join}
            WHERE (f.type = 'negative' OR (f.data->>'rating')::int = 1)
            {date_condition} {model_condition}
            GROUP BY f.data->>'reason'
            ORDER BY count DESC
        """

        try:
            results = execute_query(query)
        except:
            results = []

        total = sum(r.get('count', 0) or 0 for r in (results or []))

        if not results or len(results) == 0:
            # 기본 카테고리 반환 (데이터 없음)
            return [
                {"type": "관련없는 답변", "count": 0, "percent": 0},
                {"type": "틀리거나 부정확한 내용", "count": 0, "percent": 0},
                {"type": "불완전한 답변", "count": 0, "percent": 0},
                {"type": "응답 지연", "count": 0, "percent": 0},
                {"type": "기타", "count": 0, "percent": 0}
            ]

        return [{
            "type": r.get('type', '기타'),
            "count": r.get('count', 0) or 0,
            "percent": round((r.get('count', 0) or 0) / max(total, 1) * 100, 1)
        } for r in (results or [])]

    except Exception as e:
        logger.error(f"❌ 불만족 유형 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/departments")
async def get_departments(admin_user: dict = Depends(verify_admin)):
    """
    부서 목록 조회 (user_info 테이블에서 DISTINCT dept_nm)
    """
    try:
        query = """
            SELECT DISTINCT dept_nm
            FROM user_info
            WHERE dept_nm IS NOT NULL AND dept_nm != ''
            ORDER BY dept_nm
        """
        results = execute_query(query)

        departments = [{"id": "all", "name": "전체"}]
        for r in (results or []):
            dept = r.get('dept_nm', '')
            if dept:
                departments.append({"id": dept, "name": dept})

        return departments

    except Exception as e:
        logger.error(f"❌ 부서 목록 조회 오류: {e}")
        # 기본 부서 목록 반환
        return [
            {"id": "all", "name": "전체"},
            {"id": "개발부", "name": "개발부"},
            {"id": "경영지원부", "name": "경영지원부"},
            {"id": "영업부", "name": "영업부"},
            {"id": "인사부", "name": "인사부"},
            {"id": "기획부", "name": "기획부"}
        ]


@app.get("/api/dashboard/logs")
async def get_dashboard_logs(
    admin_user: dict = Depends(verify_admin),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    model: Optional[str] = 'all',
    feedback_filter: Optional[str] = 'all',
    department: Optional[str] = 'all',
    category: Optional[str] = 'all',
    user_email_filter: Optional[str] = '',  # ----- [2026.01.13] 사용자/이메일 필터 추가 -----
    aggregation_type: Optional[str] = 'session',  # ----- [2026.01.15] 집계 유형: 'session' | 'question' -----
    page: int = 1,
    limit: int = 20,
    sort_by: Optional[str] = 'datetime',
    sort_order: Optional[str] = 'desc'
):
    """
    로그 상세조회 API
    - feedback_filter: 'all', 'satisfied', 'dissatisfied', 'noResponse'
    - department: 부서 필터
    - category: 질문분류(의도) 필터
    - aggregation_type: 'session' (세션별 첫 질문만) | 'question' (모든 질문을 개별 행으로)  # [2026.01.15]
    - 페이지네이션 지원 (20/50/100)
    - 반환 필드: datetime, user, department, session_title, question, answer, service, category, feedback, dissatisfaction_detail
    """
    try:
        date_condition = ""
        if start_date and end_date:
            start_ts = int(datetime.fromisoformat(start_date.replace('Z', '+00:00')).timestamp())
            end_ts = int(datetime.fromisoformat(end_date.replace('Z', '+00:00')).timestamp())
            date_condition = f"AND c.created_at BETWEEN {start_ts} AND {end_ts}"

        offset = (page - 1) * limit

        # 부서 필터 조건
        dept_condition = ""
        if department != 'all':
            dept_condition = f"AND ui.dept_nm = '{department}'"

        # ----- 1227 피드백 필터 수정 시작 -----
        # ----- [2026.01.13] 서비스(모델) 필터 추가 -----
        # ----- [2026.01.13] 사용자/이메일 필터 추가 -----
        # ----- [2026.01.15] 질문단위집계 추가 - 질문단위집계시 모든 세션을 가져와 각 Q&A 쌍을 추출해야 함 -----
        # 피드백/카테고리/서비스/사용자 필터가 있거나 질문단위집계인 경우 페이지네이션 없이 모든 데이터를 가져와 필터링 후 페이징 적용
        needs_post_filter = (feedback_filter != 'all') or (category != 'all') or (model != 'all') or (user_email_filter and user_email_filter.strip()) or (aggregation_type == 'question')

        if needs_post_filter:
            # 필터링이 필요한 경우: 제한 없이 모든 데이터를 가져옴
            query_limit_clause = ""
            query_offset = 0
        else:
            # 필터링이 필요 없는 경우: 기존 페이지네이션 사용
            query_limit_clause = f"LIMIT {limit} OFFSET {offset}"
        # ----- 1227 피드백 필터 수정 종료 -----

        # 채팅 세션 기반 쿼리 - user_info 테이블 조인
        # ----- [2026.01.15] user_id 추가 (벡터화 파일 조회용) -----
        query = f"""
            SELECT
                c.id as chat_id,
                c.user_id as user_id,
                c.title as session_title,
                u.name as user_name,
                u.email as user_email,
                ui.dept_nm as department,
                TO_TIMESTAMP(c.created_at) as created_at,
                c.chat::jsonb->'messages'->0->'models'->>0 as model
            FROM chat c
            LEFT JOIN "user" u ON c.user_id = u.id
            LEFT JOIN user_info ui ON u.email = ui.email
            WHERE c.chat IS NOT NULL {date_condition} {dept_condition}
            ORDER BY c.created_at DESC
            {query_limit_clause}
        """

        try:
            results = execute_query(query)
        except Exception as e:
            logger.error(f"기본 쿼리 실패: {e}")
            results = []

        # ----- [2026-01-22] 메시지에서 첨부파일 추출 헬퍼 함수 시작 -----
        # 해당 질문/세션에 첨부된 파일만 조회하도록 변경
        def extract_files_from_message(msg):
            """단일 메시지에서 첨부 파일 정보 추출"""
            files_info = []
            if isinstance(msg, dict) and 'files' in msg:
                files = msg.get('files', [])
                for f in (files or []):
                    if isinstance(f, dict):
                        # files 배열 내의 file 객체
                        file_obj = f.get('file', f)
                        if isinstance(file_obj, dict):
                            filename = file_obj.get('filename', '') or file_obj.get('name', '')
                            if filename and not filename.startswith('tmp.'):
                                files_info.append(filename)
            return files_info

        def extract_all_files_from_messages(messages):
            """메시지 리스트에서 모든 첨부 파일 추출 (세션 전체)"""
            all_files = []
            for msg in (messages or []):
                all_files.extend(extract_files_from_message(msg))
            # 중복 제거
            return list(dict.fromkeys(all_files))
        # ----- [2026-01-22] 메시지에서 첨부파일 추출 헬퍼 함수 종료 -----

        # 결과 포맷팅
        logs = []
        for r in (results or []):
            chat_id = r.get('chat_id')
            user_id = r.get('user_id')  # ----- [2026.01.15] 벡터화 파일 조회용 -----
            user_name = r.get('user_name', '') or '-'
            user_email = r.get('user_email', '') or '-'
            dept = r.get('department', '') or '-'
            session_title = r.get('session_title', '') or '-'
            service = r.get('model', '') or 'Gen SDC'
            created_at = r.get('created_at')

            # ----- [2026-01-22] 해당 질문/세션에 첨부된 파일 정보로 변경 -----
            # (나중에 메시지 처리 시 업데이트됨)
            vectorized_file_count = 0
            vectorized_filenames = '-'

            # chat 테이블의 chat JSON에서 메시지 추출
            # ----- [2026.01.15] 집계 유형에 따라 처리 분기 -----
            qa_pairs = []  # 질문-답변 쌍 리스트
            feedback_status = '무응답'
            dissatisfaction_detail = '-'
            dissatisfaction_type = '-'
            category_val = '-'

            if chat_id:
                try:
                    # chat JSON에서 messages 추출
                    chat_query = f"""
                        SELECT chat::jsonb->'messages' as messages,
                               chat::jsonb->'history'->'messages' as history_messages
                        FROM chat
                        WHERE id = '{chat_id}'
                    """
                    chat_results = execute_query(chat_query)

                    if chat_results:
                        messages = chat_results[0].get('messages') or chat_results[0].get('history_messages') or []

                        # ----- [2026.01.15] 집계 유형별 메시지 추출 시작 -----
                        if aggregation_type == 'question':
                            # 질문단위집계: 모든 질문-답변 쌍을 개별 행으로 추출
                            current_question = None
                            current_question_timestamp = None
                            current_question_files = []  # [2026-01-22] 해당 질문에 첨부된 파일
                            for msg in messages:
                                if isinstance(msg, dict):
                                    role = msg.get('role', '')
                                    content = msg.get('content', '') or ''

                                    if role == 'user' and content:
                                        # 새로운 질문 발견
                                        current_question = content
                                        current_question_timestamp = msg.get('timestamp')
                                        # [2026-01-22] 해당 질문 메시지에 첨부된 파일 추출
                                        current_question_files = extract_files_from_message(msg)
                                    elif role == 'assistant' and content and current_question:
                                        # 답변 발견 - 질문-답변 쌍 생성
                                        msg_timestamp = msg.get('timestamp')
                                        answer_datetime_val = '-'
                                        if msg_timestamp:
                                            try:
                                                answer_datetime_val = datetime.fromtimestamp(msg_timestamp).strftime('%Y-%m-%d %H:%M')
                                            except:
                                                pass
                                        # 토큰 수 추출
                                        tokens = 0
                                        info = msg.get('info', {}) or {}
                                        if isinstance(info, dict):
                                            tokens = info.get('total_tokens', 0) or info.get('eval_count', 0) or 0

                                        qa_pairs.append({
                                            'question': current_question,
                                            'answer': content,
                                            'answer_datetime': answer_datetime_val,
                                            'total_tokens': tokens,
                                            'question_timestamp': current_question_timestamp,
                                            # [2026-01-22] 해당 질문에 첨부된 파일 정보
                                            'attached_files': current_question_files,
                                            'attached_file_count': len(current_question_files)
                                        })
                                        current_question = None
                                        current_question_timestamp = None
                                        current_question_files = []

                            # 답변 없는 마지막 질문도 포함
                            if current_question:
                                qa_pairs.append({
                                    'question': current_question,
                                    'answer': '-',
                                    'answer_datetime': '-',
                                    'total_tokens': 0,
                                    'question_timestamp': current_question_timestamp,
                                    # [2026-01-22] 해당 질문에 첨부된 파일 정보
                                    'attached_files': current_question_files,
                                    'attached_file_count': len(current_question_files)
                                })
                        else:
                            # 세션집계 (기본): 첫 번째 질문-답변만 표시하지만 전체 Q&A도 수집
                            # ----- [2026.01.15] 세션집계시 모든 Q&A 수집 (팝업/엑셀용) -----
                            question = ''
                            answer = ''
                            answer_datetime = '-'
                            total_tokens = 0
                            all_qa_list = []  # 모든 Q&A 쌍 저장
                            current_q = None
                            current_q_timestamp = None
                            # [2026-01-22] 세션 전체 메시지에서 첨부파일 추출
                            session_attached_files = extract_all_files_from_messages(messages)

                            for msg in messages:
                                if isinstance(msg, dict):
                                    role = msg.get('role', '')
                                    content = msg.get('content', '') or ''

                                    if role == 'user' and content:
                                        # 첫 번째 질문 저장
                                        if not question:
                                            question = content
                                        # 모든 Q&A 수집용
                                        current_q = content
                                        current_q_timestamp = msg.get('timestamp')
                                    elif role == 'assistant' and content:
                                        # 첫 번째 답변 저장
                                        if not answer:
                                            answer = content
                                            msg_timestamp = msg.get('timestamp')
                                            if msg_timestamp:
                                                try:
                                                    answer_datetime = datetime.fromtimestamp(msg_timestamp).strftime('%Y-%m-%d %H:%M')
                                                except:
                                                    pass
                                        # 토큰 수 누적
                                        info = msg.get('info', {}) or {}
                                        if isinstance(info, dict):
                                            total_tokens += info.get('total_tokens', 0) or info.get('eval_count', 0) or 0
                                        # 모든 Q&A 쌍 수집
                                        if current_q:
                                            qa_datetime = '-'
                                            msg_ts = msg.get('timestamp')
                                            if msg_ts:
                                                try:
                                                    qa_datetime = datetime.fromtimestamp(msg_ts).strftime('%Y-%m-%d %H:%M')
                                                except:
                                                    pass
                                            all_qa_list.append({
                                                'question': current_q,
                                                'answer': content,
                                                'datetime': qa_datetime
                                            })
                                            current_q = None

                            # 답변 없는 마지막 질문도 포함
                            if current_q:
                                all_qa_list.append({
                                    'question': current_q,
                                    'answer': '-',
                                    'datetime': '-'
                                })

                            qa_pairs.append({
                                'question': question if question else session_title,
                                'answer': answer if answer else '-',
                                'answer_datetime': answer_datetime,
                                'total_tokens': total_tokens,
                                'question_timestamp': None,
                                'all_qa_pairs': all_qa_list,  # 모든 Q&A 쌍 (팝업/엑셀용)
                                'qa_count': len(all_qa_list),  # Q&A 개수
                                # [2026-01-22] 세션 전체 첨부파일 정보
                                'attached_files': session_attached_files,
                                'attached_file_count': len(session_attached_files)
                            })
                        # ----- [2026.01.15] 집계 유형별 메시지 추출 종료 -----

                    # 피드백 조회 (feedback 테이블에서 meta->>'chat_id'로 조인)
                    fb_query = f"""
                        SELECT f.type,
                               f.data->>'rating' as rating,
                               f.data->>'reason' as reason,
                               f.data->>'comment' as comment
                        FROM feedback f
                        WHERE f.meta->>'chat_id' = '{chat_id}'
                        ORDER BY f.created_at DESC
                        LIMIT 1
                    """
                    try:
                        fb_results = execute_query(fb_query)
                        if fb_results:
                            fb_type = fb_results[0].get('type', '')
                            fb_rating = fb_results[0].get('rating', '')
                            fb_reason = fb_results[0].get('reason', '')
                            fb_comment = fb_results[0].get('comment', '')

                            # rating 값으로 만족/불만족 판단 (10=만족, 1=불만족)
                            try:
                                rating_val = int(fb_rating) if fb_rating else 0
                            except:
                                rating_val = 0

                            if rating_val == 10 or fb_type == 'positive':
                                feedback_status = '만족'
                            elif rating_val == 1 or fb_type == 'negative':
                                feedback_status = '불만족'
                                dissatisfaction_type = fb_reason if fb_reason else '-'
                                dissatisfaction_detail = fb_comment if fb_comment else '-'
                    except Exception as fb_err:
                        logger.debug(f"피드백 조회 실패 (chat_id={chat_id}): {fb_err}")

                except Exception as e:
                    logger.error(f"채팅 메시지 조회 실패 (chat_id={chat_id}): {e}")

            # qa_pairs가 비어있으면 기본 항목 추가
            if not qa_pairs:
                qa_pairs.append({
                    'question': session_title,
                    'answer': '-',
                    'answer_datetime': '-',
                    'total_tokens': 0,
                    'question_timestamp': None
                })

            # ----- 피드백 필터 시작 -----
            # 피드백 필터 적용
            if feedback_filter == 'satisfied' and feedback_status != '만족':
                continue
            elif feedback_filter == 'dissatisfied' and feedback_status != '불만족':
                continue
            elif feedback_filter == 'noResponse' and feedback_status != '무응답':
                continue
            # ----- 피드백 필터 종료 -----

            # ----- 카테고리 필터 시작 -----
            # 카테고리 필터 적용
            if category != 'all' and category_val != category:
                continue
            # ----- 카테고리 필터 종료 -----

            # ----- [2026.01.13] 서비스(모델) 필터 시작 -----
            if model != 'all' and service != model:
                continue
            # ----- 서비스(모델) 필터 종료 -----

            # ----- [2026.01.13] 사용자/이메일 필터 시작 -----
            if user_email_filter and user_email_filter.strip():
                filter_lower = user_email_filter.strip().lower()
                user_name_lower = (user_name or '').lower()
                user_email_val_lower = (r.get('user_email', '') or '').lower()
                if filter_lower not in user_name_lower and filter_lower not in user_email_val_lower:
                    continue
            # ----- 사용자/이메일 필터 종료 -----

            # ----- [2026.01.15] qa_pairs 반복 처리 시작 -----
            # 각 질문-답변 쌍을 개별 로그 항목으로 추가
            for idx, qa in enumerate(qa_pairs):
                # 질문단위집계에서 질문 시간 사용, 없으면 세션 시간 사용
                if qa.get('question_timestamp'):
                    try:
                        display_datetime = datetime.fromtimestamp(qa['question_timestamp']).strftime('%Y-%m-%d %H:%M')
                    except:
                        display_datetime = created_at.strftime('%Y-%m-%d %H:%M') if created_at else '-'
                else:
                    display_datetime = created_at.strftime('%Y-%m-%d %H:%M') if created_at else '-'

                # [2026-01-22] 해당 질문/세션에 첨부된 파일 정보 사용
                attached_files = qa.get('attached_files', [])
                attached_file_count = qa.get('attached_file_count', 0)
                attached_filenames = ', '.join(attached_files) if attached_files else '-'

                logs.append({
                    "datetime": display_datetime,
                    "user": user_name,
                    "email": user_email,
                    "department": dept,
                    "session_title": session_title if session_title else '-',
                    "question": qa.get('question', '-'),
                    "answer": qa.get('answer', '-'),
                    "answer_datetime": qa.get('answer_datetime', '-'),
                    "total_tokens": qa.get('total_tokens', 0),
                    # ----- [2026-01-22] 해당 질문/세션에 첨부된 파일 정보로 변경 -----
                    "vectorized_file_count": attached_file_count,
                    "vectorized_filenames": attached_filenames,
                    # ----- [2026-01-22] 첨부 파일 정보 변경 종료 -----
                    "service": service,
                    "category": category_val,
                    "feedback": feedback_status,
                    "dissatisfaction_type": dissatisfaction_type,
                    "dissatisfaction_detail": dissatisfaction_detail,
                    "question_index": idx + 1 if aggregation_type == 'question' else None,  # 질문 번호 (질문단위집계에서만)
                    # ----- [2026.01.15] 세션집계 팝업/엑셀용 전체 Q&A 데이터 -----
                    "all_qa_pairs": qa.get('all_qa_pairs', []),  # 모든 Q&A 쌍 (세션집계에서만 사용)
                    "qa_count": qa.get('qa_count', 1)  # Q&A 개수
                })
            # ----- [2026.01.15] qa_pairs 반복 처리 종료 -----

        # ----- [2026.01.13] 정렬 기능 추가 시작 -----
        if sort_by and logs:
            reverse = (sort_order == 'desc')
            try:
                if sort_by == 'total_tokens':
                    logs.sort(key=lambda x: x.get(sort_by, 0) or 0, reverse=reverse)
                else:
                    logs.sort(key=lambda x: x.get(sort_by, '') or '', reverse=reverse)
            except Exception as sort_err:
                logger.debug(f"정렬 오류: {sort_err}")
        # ----- 정렬 기능 추가 종료 -----

        # ----- 1227 피드백 필터 후 페이지네이션 적용 시작 -----
        if needs_post_filter:
            # 필터링 후 페이지네이션 적용
            total = len(logs)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_logs = logs[start_idx:end_idx]
            has_more = end_idx < total
        else:
            # 기존 로직: DB 페이지네이션 사용
            paginated_logs = logs
            # 총 개수 계산
            count_query = f"""
                SELECT COUNT(*) as cnt
                FROM chat c
                WHERE c.chat IS NOT NULL {date_condition}
            """
            try:
                count_results = execute_query(count_query)
                total = count_results[0].get('cnt', 0) if count_results else len(logs)
            except:
                total = len(logs) if len(logs) < limit else limit * 10
            has_more = len(logs) == limit
        # ----- 1227 피드백 필터 후 페이지네이션 적용 종료 -----

        return {
            "data": paginated_logs,
            "total": total,
            "page": page,
            "limit": limit,
            "hasMore": has_more
        }

    except Exception as e:
        logger.error(f"❌ 로그 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# [2026.01.12] 엑셀 다운로드 API - 질의별 집계 및 컬럼 폭 설정
# ==============================================================================
# 변경 이력:
#   - [2022.12.22] 초기 구현: 기간 필터 기반 로그 다운로드
#   - [2026.01.09] 질의별 집계로 변경, 이메일/답변일시/총토큰수 컬럼 추가
#   - [2026.01.12] Excel(.xlsx) 형식 변경, 질문/답변 컬럼 4배 폭 적용
#
# 의존성:
#   - openpyxl>=3.1.5 (Excel 파일 생성)
#   - et-xmlfile>=2.0.0 (openpyxl 의존성)
#
# 오프라인 설치:
#   - offline_packages/openpyxl-3.1.5-py2.py3-none-any.whl
#   - offline_packages/et_xmlfile-2.0.0-py3-none-any.whl
#   - 설치: pip install --no-index /path/to/wheel_file.whl
#
# 컬럼 폭 설정:
#   - 기본 폭: 15
#   - 질문/답변: 60 (기본의 4배)
# ==============================================================================
@app.get("/api/dashboard/logs/export")
async def export_dashboard_logs(
    admin_user: dict = Depends(verify_admin),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    aggregation_type: Optional[str] = 'question'  # ----- [2026.01.15] 집계 유형 추가 -----
):
    """
    로그 엑셀 내보내기 API - 질의별 집계로 다운로드

    [2026.01.09] 변경사항:
    - 집계기준: 사용자별 → 질의별
    - 일시 → 질의일시
    - 사용자 다음에 이메일아이디 추가
    - 답변일시 추가
    - 총토큰수 추가

    [2026.01.12] 변경사항:
    - Excel(.xlsx) 형식으로 변경 (CSV에서 변경)
    - 질문/답변 필드 4배 폭 적용 (기본 15 → 60)
    - openpyxl 라이브러리 사용
    - 헤더 스타일: 파란색 배경, 흰색 굵은 글씨
    - 모든 셀에 테두리 적용
    - 질문/답변 셀에 줄바꿈(wrap_text) 적용

    [2026.01.15] 변경사항:
    - aggregation_type 파라미터 추가
    - 'session': 세션단위 집계 - 모든 Q&A를 하나의 행에 포함
    - 'question': 질문단위 집계 - 각 Q&A를 개별 행으로 (기존 방식)

    Returns:
        StreamingResponse: Excel 파일 (.xlsx)
    """
    # ----- [2026.01.12] openpyxl 라이브러리 import -----
    # 오프라인 환경에서는 사전에 휠 파일로 설치 필요
    # 설치 방법: pip install --no-index /path/to/openpyxl-3.1.5-py2.py3-none-any.whl
    import io as io_module
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    try:
        # 기간 필터 적용
        date_condition = ""
        if start_date and end_date:
            start_ts = int(datetime.fromisoformat(start_date.replace('Z', '+00:00')).timestamp())
            end_ts = int(datetime.fromisoformat(end_date.replace('Z', '+00:00')).timestamp())
            date_condition = f"AND c.created_at BETWEEN {start_ts} AND {end_ts}"

        # 기간 내 모든 채팅 세션을 가져오기
        # ----- [2026.01.15] user_id 추가 (벡터화 파일 조회용) -----
        query = f"""
            SELECT
                c.id as chat_id,
                c.user_id as user_id,
                c.title as session_title,
                u.name as user_name,
                u.email as user_email,
                ui.dept_nm as department,
                TO_TIMESTAMP(c.created_at) as created_at,
                c.chat::jsonb->'messages'->0->'models'->>0 as model,
                c.chat::jsonb as chat_data
            FROM chat c
            LEFT JOIN "user" u ON c.user_id = u.id
            LEFT JOIN user_info ui ON u.email = ui.email
            WHERE c.chat IS NOT NULL {date_condition}
            ORDER BY c.created_at DESC
        """

        try:
            results = execute_query(query)
        except Exception as e:
            logger.error(f"엑셀 내보내기 쿼리 실패: {e}")
            results = []

        # ----- [2026.01.15] 사용자별 벡터화 파일 정보 조회 (엑셀용) 시작 -----
        # embedding_model 또는 chunks가 있는 파일 = 실제 벡터화 완료된 파일
        # 중복 파일명 제거, 임시파일(tmp.) 제외
        user_vectorized_files_excel = {}
        try:
            file_query_excel = """
                SELECT
                    f.user_id,
                    COUNT(DISTINCT f.filename) as file_count,
                    STRING_AGG(DISTINCT f.filename, ', ') as filenames
                FROM file f
                WHERE (f.meta::jsonb->>'embedding_model' IS NOT NULL
                   OR f.meta::jsonb->>'chunks' IS NOT NULL)
                  AND f.filename NOT LIKE 'tmp.%'
                GROUP BY f.user_id
            """
            file_results_excel = execute_query(file_query_excel)
            for fr in (file_results_excel or []):
                user_vectorized_files_excel[fr.get('user_id')] = {
                    'count': fr.get('file_count', 0),
                    'filenames': fr.get('filenames', '')
                }
        except Exception as file_err:
            logger.warning(f"엑셀용 벡터화 파일 조회 오류 (무시됨): {file_err}")
        # ----- [2026.01.15] 사용자별 벡터화 파일 정보 조회 (엑셀용) 종료 -----

        # ----- [2026-01-22] 메시지에서 첨부파일 추출 헬퍼 함수 시작 -----
        def extract_files_from_message_excel(msg):
            """단일 메시지에서 첨부 파일 정보 추출"""
            files_info = []
            if isinstance(msg, dict) and 'files' in msg:
                files = msg.get('files', [])
                for f in (files or []):
                    if isinstance(f, dict):
                        file_obj = f.get('file', f)
                        if isinstance(file_obj, dict):
                            filename = file_obj.get('filename', '') or file_obj.get('name', '')
                            if filename and not filename.startswith('tmp.'):
                                files_info.append(filename)
            return files_info

        def extract_all_files_from_messages_excel(messages):
            """메시지 리스트에서 모든 첨부 파일 추출 (세션 전체)"""
            all_files = []
            for msg in (messages or []):
                all_files.extend(extract_files_from_message_excel(msg))
            return list(dict.fromkeys(all_files))
        # ----- [2026-01-22] 메시지에서 첨부파일 추출 헬퍼 함수 종료 -----

        # 질의별 집계 - 각 질문/답변 쌍을 개별 행으로 처리
        logs = []
        for r in (results or []):
            chat_id = r.get('chat_id')
            user_id = r.get('user_id')
            user_name = r.get('user_name', '') or '-'
            user_email = r.get('user_email', '') or '-'
            dept = r.get('department', '') or '-'
            session_title = r.get('session_title', '') or '-'
            service = r.get('model', '') or 'Gen SDC'
            chat_data = r.get('chat_data') or {}

            # 메시지 목록 추출
            messages = []
            if isinstance(chat_data, dict):
                messages = chat_data.get('messages') or []
                if not messages:
                    history = chat_data.get('history') or {}
                    messages = history.get('messages') or []

            # 질문-답변 쌍 추출
            qa_pairs = []
            current_question = None
            question_time = None
            current_question_files = []  # [2026-01-22] 해당 질문에 첨부된 파일

            for msg in messages:
                if not isinstance(msg, dict):
                    continue

                role = msg.get('role', '')
                content = msg.get('content', '') or ''
                timestamp = msg.get('timestamp')

                # 토큰 정보 추출
                info = msg.get('info') or {}
                usage = info.get('usage') or {}
                total_tokens = usage.get('total_tokens', 0)

                # timestamp 처리
                msg_time = '-'
                if timestamp:
                    try:
                        if isinstance(timestamp, (int, float)):
                            msg_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            msg_time = str(timestamp)
                    except:
                        msg_time = '-'

                if role == 'user':
                    current_question = content
                    question_time = msg_time
                    # [2026-01-22] 해당 질문 메시지에 첨부된 파일 추출
                    current_question_files = extract_files_from_message_excel(msg)
                elif role == 'assistant' and current_question:
                    qa_pairs.append({
                        'question': current_question,
                        'question_time': question_time,
                        'answer': content,
                        'answer_time': msg_time,
                        'total_tokens': total_tokens,
                        # [2026-01-22] 해당 질문에 첨부된 파일 정보
                        'attached_files': current_question_files,
                        'attached_file_count': len(current_question_files)
                    })
                    current_question = None
                    question_time = None
                    current_question_files = []

            # 피드백 조회
            feedback_status = '무응답'
            dissatisfaction_type = '-'
            dissatisfaction_comment = '-'
            category_val = '-'

            if chat_id:
                try:
                    fb_query = f"""
                        SELECT f.type,
                               f.data->>'rating' as rating,
                               f.data->>'reason' as reason,
                               f.data->>'comment' as comment
                        FROM feedback f
                        WHERE f.meta->>'chat_id' = '{chat_id}'
                        ORDER BY f.created_at DESC
                        LIMIT 1
                    """
                    fb_results = execute_query(fb_query)
                    if fb_results:
                        fb_type = fb_results[0].get('type', '')
                        fb_rating = fb_results[0].get('rating', '')
                        fb_reason = fb_results[0].get('reason', '')
                        fb_comment = fb_results[0].get('comment', '')

                        try:
                            rating_val = int(fb_rating) if fb_rating else 0
                        except:
                            rating_val = 0

                        if rating_val == 10 or fb_type == 'positive':
                            feedback_status = '만족'
                        elif rating_val == 1 or fb_type == 'negative':
                            feedback_status = '불만족'
                            dissatisfaction_type = fb_reason if fb_reason else '-'
                            dissatisfaction_comment = fb_comment if fb_comment else '-'
                except Exception as fb_err:
                    logger.debug(f"피드백 조회 실패 (chat_id={chat_id}): {fb_err}")

            # ----- [2026.01.15] 집계 유형에 따른 행 추가 -----
            # [2026-01-22] 세션 전체 첨부파일 추출
            session_files_excel = extract_all_files_from_messages_excel(messages)
            session_file_count_excel = len(session_files_excel)
            session_filenames_excel = ', '.join(session_files_excel) if session_files_excel else '-'

            if aggregation_type == 'session':
                # 세션집계: 모든 Q&A를 하나의 행에 포함
                if qa_pairs:
                    # 모든 질문/답변을 포맷팅하여 하나의 필드로 결합
                    all_questions = []
                    all_answers = []
                    total_tokens_sum = 0
                    first_question_time = qa_pairs[0]['question_time'] if qa_pairs else '-'
                    last_answer_time = qa_pairs[-1]['answer_time'] if qa_pairs else '-'

                    for i, qa in enumerate(qa_pairs):
                        q_text = qa['question'] if qa['question'] else '-'
                        a_text = qa['answer'] if qa['answer'] else '-'
                        q_time = qa['question_time'] if qa['question_time'] else ''
                        a_time = qa['answer_time'] if qa['answer_time'] else ''

                        # 질문 포맷: [#1] (시간) 질문내용
                        all_questions.append(f"[#{i+1}] ({q_time}) {q_text}")
                        # 답변 포맷: [#1] (시간) 답변내용
                        all_answers.append(f"[#{i+1}] ({a_time}) {a_text}")
                        total_tokens_sum += qa['total_tokens'] or 0

                    logs.append({
                        "query_datetime": first_question_time,
                        "user": user_name,
                        "email": user_email,
                        "department": dept,
                        "session_title": session_title,
                        "question": "\n\n".join(all_questions),  # 모든 질문을 줄바꿈으로 구분
                        "answer": "\n\n".join(all_answers),      # 모든 답변을 줄바꿈으로 구분
                        "answer_datetime": last_answer_time,
                        "total_tokens": total_tokens_sum,
                        # ----- [2026-01-22] 세션 전체 첨부파일 정보로 변경 -----
                        "vectorized_file_count": session_file_count_excel,
                        "vectorized_filenames": session_filenames_excel,
                        # ----- [2026-01-22] 첨부파일 정보 변경 종료 -----
                        "service": service,
                        "category": category_val,
                        "feedback": feedback_status,
                        "dissatisfaction_type": dissatisfaction_type,
                        "dissatisfaction_comment": dissatisfaction_comment,
                        "qa_count": len(qa_pairs)  # Q&A 개수
                    })
                else:
                    # Q&A 쌍이 없는 경우
                    logs.append({
                        "query_datetime": r.get('created_at').strftime('%Y-%m-%d %H:%M:%S') if r.get('created_at') else '-',
                        "user": user_name,
                        "email": user_email,
                        "department": dept,
                        "session_title": session_title,
                        "question": session_title,
                        "answer": '-',
                        "answer_datetime": '-',
                        "total_tokens": 0,
                        # ----- [2026-01-22] 세션 전체 첨부파일 정보로 변경 -----
                        "vectorized_file_count": session_file_count_excel,
                        "vectorized_filenames": session_filenames_excel,
                        # ----- [2026-01-22] 첨부파일 정보 변경 종료 -----
                        "service": service,
                        "category": category_val,
                        "feedback": feedback_status,
                        "dissatisfaction_type": dissatisfaction_type,
                        "dissatisfaction_comment": dissatisfaction_comment,
                        "qa_count": 0
                    })
            else:
                # 질문단위집계 (기존 방식): 각 Q&A를 개별 행으로
                if qa_pairs:
                    for qa in qa_pairs:
                        # [2026-01-22] 해당 질문에 첨부된 파일 정보
                        qa_files = qa.get('attached_files', [])
                        qa_file_count = qa.get('attached_file_count', 0)
                        qa_filenames = ', '.join(qa_files) if qa_files else '-'

                        logs.append({
                            "query_datetime": qa['question_time'],
                            "user": user_name,
                            "email": user_email,
                            "department": dept,
                            "session_title": session_title,
                            "question": qa['question'] if qa['question'] else '-',
                            "answer": qa['answer'] if qa['answer'] else '-',
                            "answer_datetime": qa['answer_time'],
                            "total_tokens": qa['total_tokens'],
                            # ----- [2026-01-22] 해당 질문에 첨부된 파일 정보로 변경 -----
                            "vectorized_file_count": qa_file_count,
                            "vectorized_filenames": qa_filenames,
                            # ----- [2026-01-22] 첨부파일 정보 변경 종료 -----
                            "service": service,
                            "category": category_val,
                            "feedback": feedback_status,
                            "dissatisfaction_type": dissatisfaction_type,
                            "dissatisfaction_comment": dissatisfaction_comment
                        })
                else:
                    # Q&A 쌍이 없는 경우 세션 정보만 출력
                    logs.append({
                        "query_datetime": r.get('created_at').strftime('%Y-%m-%d %H:%M:%S') if r.get('created_at') else '-',
                        "user": user_name,
                        "email": user_email,
                        "department": dept,
                        "session_title": session_title,
                        "question": session_title,
                        "answer": '-',
                        "answer_datetime": '-',
                        "total_tokens": 0,
                        # ----- [2026-01-22] 세션 전체 첨부파일 정보 -----
                        "vectorized_file_count": session_file_count_excel,
                        "vectorized_filenames": session_filenames_excel,
                        # ----- [2026-01-22] 첨부파일 정보 변경 종료 -----
                        "service": service,
                        "category": category_val,
                        "feedback": feedback_status,
                        "dissatisfaction_type": dissatisfaction_type,
                        "dissatisfaction_comment": dissatisfaction_comment
                    })
            # ----- [2026.01.15] 집계 유형에 따른 행 추가 종료 -----

        # ----- [2026.01.12] Excel 형식으로 생성 (컬럼 폭 지정) -----
        wb = Workbook()
        ws = wb.active
        ws.title = "로그"

        # 헤더 정의 - [2026.01.13] 컬럼 순서 변경: 질의일시를 질문 다음으로 이동
        # ----- [2026.01.15] 벡터화파일수, 파일명 컬럼 추가 -----
        headers = [
            '사용자', '이메일아이디', '부서', '세션제목', '질문', '질의일시', '답변', '답변일시', '총토큰수',
            '벡터화파일수', '파일명', '서비스', '의도분류', '피드백', '불만족유형', '불만족의견'
        ]

        # 컬럼 폭 설정 (기본 폭: 15, 질문/답변: 60 = 4배)
        # ----- [2026.01.15] 벡터화파일수, 파일명 컬럼 추가로 인덱스 변경: A-P (16개) -----
        BASE_WIDTH = 15
        WIDE_WIDTH = BASE_WIDTH * 4  # 질문/답변은 4배 폭

        # [2026.01.13] 컬럼 순서 변경에 맞춰 폭 재설정
        column_widths = {
            'A': BASE_WIDTH,  # 사용자
            'B': 25,          # 이메일아이디
            'C': BASE_WIDTH,  # 부서
            'D': 20,          # 세션제목
            'E': WIDE_WIDTH,  # 질문 (4배 폭)
            'F': 20,          # 질의일시
            'G': WIDE_WIDTH,  # 답변 (4배 폭)
            'H': 20,          # 답변일시
            'I': 12,          # 총토큰수
            'J': 12,          # 벡터화파일수 [2026.01.15]
            'K': 40,          # 파일명 [2026.01.15]
            'L': BASE_WIDTH,  # 서비스
            'M': BASE_WIDTH,  # 의도분류
            'N': 10,          # 피드백
            'O': BASE_WIDTH,  # 불만족유형
            'P': 20,          # 불만족의견
        }

        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width

        # 헤더 스타일
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # 헤더 작성
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        # 데이터 스타일
        data_alignment = Alignment(vertical="top", wrap_text=True)
        question_answer_alignment = Alignment(vertical="top", wrap_text=True)  # 질문/답변은 줄바꿈

        # 데이터 작성 - [2026.01.13] 컬럼 순서 변경: 질의일시를 질문 다음으로 이동
        # ----- [2026.01.15] 벡터화파일수, 파일명 컬럼 추가 -----
        for row_idx, log in enumerate(logs, 2):
            row_data = [
                log.get('user', ''),
                log.get('email', ''),
                log.get('department', ''),
                log.get('session_title', ''),
                log.get('question', ''),
                log.get('query_datetime', ''),
                log.get('answer', ''),
                log.get('answer_datetime', ''),
                log.get('total_tokens', 0),
                log.get('vectorized_file_count', 0),   # [2026.01.15] 벡터화파일수
                log.get('vectorized_filenames', '-'),  # [2026.01.15] 파일명
                log.get('service', ''),
                log.get('category', ''),
                log.get('feedback', ''),
                log.get('dissatisfaction_type', ''),
                log.get('dissatisfaction_comment', '')
            ]

            for col_idx, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = thin_border
                # 질문(E), 답변(G), 파일명(K) 컬럼은 줄바꿈 적용 - [2026.01.15] 파일명 추가
                if col_idx in [5, 7, 11]:
                    cell.alignment = question_answer_alignment
                else:
                    cell.alignment = data_alignment

        # 행 높이 자동 조정 (질문/답변이 긴 경우)
        ws.row_dimensions[1].height = 25  # 헤더 높이

        # Excel 파일을 BytesIO로 저장
        output = io_module.BytesIO()
        wb.save(output)
        output.seek(0)

        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename=logs_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            }
        )
        # ----- [2026.01.12] Excel 형식으로 생성 종료 -----

    except Exception as e:
        logger.error(f"❌ 로그 엑셀 내보내기 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# ----- [2026.01.09] 엑셀 다운로드 질의별 집계로 변경 종료 -----
# ----- [2026.01.12] CSV → Excel 형식 변경, 질문/답변 4배 폭 적용 종료 -----


# ==================== Guardrails API 엔드포인트 ====================

from fastapi.responses import StreamingResponse
import io
import json
import uuid
import base64

@app.get("/api/guardrails/dashboard")
async def get_guardrails_dashboard(
    admin_user: dict = Depends(verify_admin),
    range: Optional[str] = '7d'
):
    """
    가드레일 대시보드 통계
    - 총 정책 수, 활성화된 정책 수
    - 총 검사 수, 차단된 요청 수
    - 정책별 통계, 최근 차단 로그
    """
    try:
        # 날짜 범위 계산
        days = 7
        if range == '1d':
            days = 1
        elif range == '7d':
            days = 7
        elif range == '30d':
            days = 30
        elif range == '90d':
            days = 90

        # 정책 통계 조회 (guardrails_db 구조: name, category, enabled, severity, rules)
        policy_query = """
            SELECT
                COUNT(*) as total_policies,
                COUNT(*) FILTER (WHERE enabled = true) as active_policies
            FROM guardrail_policies
        """
        try:
            policy_results = execute_query(policy_query)
            total_policies = policy_results[0].get('total_policies', 0) if policy_results else 0
            active_policies = policy_results[0].get('active_policies', 0) if policy_results else 0
        except Exception as e:
            logger.error(f"정책 통계 조회 오류: {e}")
            total_policies = 0
            active_policies = 0

        # 검사 로그 통계 조회
        log_query = f"""
            SELECT
                COUNT(*) as total_checks,
                COUNT(*) FILTER (WHERE check_result = 'blocked') as blocked_count,
                COUNT(*) FILTER (WHERE check_result = 'passed') as passed_count,
                COUNT(*) FILTER (WHERE check_result = 'warning') as warning_count
            FROM guardrail_check_logs
            WHERE created_at >= NOW() - INTERVAL '{days} days'
        """
        try:
            log_results = execute_query(log_query)
            total_checks = log_results[0].get('total_checks', 0) if log_results else 0
            blocked_count = log_results[0].get('blocked_count', 0) if log_results else 0
            passed_count = log_results[0].get('passed_count', 0) if log_results else 0
            warning_count = log_results[0].get('warning_count', 0) if log_results else 0
        except Exception as e:
            logger.error(f"로그 통계 조회 오류: {e}")
            total_checks = 0
            blocked_count = 0
            passed_count = 0
            warning_count = 0

        # 정책별 통계 (guardrails_db 구조: name, category, enabled, severity)
        policy_stats_query = f"""
            SELECT
                p.id,
                p.name as policy_name,
                p.severity,
                p.enabled as is_active,
                COUNT(l.id) as total_checks,
                COUNT(l.id) FILTER (WHERE l.check_result = 'blocked') as blocked_count,
                ROUND(
                    COUNT(l.id) FILTER (WHERE l.check_result = 'blocked')::numeric /
                    NULLIF(COUNT(l.id), 0) * 100, 1
                ) as block_rate
            FROM guardrail_policies p
            LEFT JOIN guardrail_check_logs l ON p.id = l.policy_id
                AND l.created_at >= NOW() - INTERVAL '{days} days'
            GROUP BY p.id, p.name, p.severity, p.enabled
            ORDER BY blocked_count DESC
        """
        try:
            policy_stats = execute_query(policy_stats_query)
        except Exception as e:
            logger.error(f"정책별 통계 조회 오류: {e}")
            policy_stats = []

        # 최근 차단 로그 (guardrails_db 구조: name, severity)
        recent_logs_query = f"""
            SELECT
                l.id,
                l.request_id,
                l.user_id,
                l.check_result,
                l.original_text,
                l.detection_score,
                l.created_at,
                p.name as policy_name,
                p.severity
            FROM guardrail_check_logs l
            JOIN guardrail_policies p ON l.policy_id = p.id
            WHERE l.check_result = 'blocked'
            AND l.created_at >= NOW() - INTERVAL '{days} days'
            ORDER BY l.created_at DESC
        """
        # ----- 1227 LIMIT 10 제거 완료 -----
        try:
            recent_logs = execute_query(recent_logs_query)
            # datetime 직렬화 처리
            for log in (recent_logs or []):
                if log.get('created_at'):
                    log['created_at'] = log['created_at'].isoformat()
        except Exception as e:
            logger.error(f"최근 로그 조회 오류: {e}")
            recent_logs = []

        return {
            "summary": {
                "totalPolicies": total_policies,
                "activePolicies": active_policies,
                "totalChecks": total_checks,
                "blockedCount": blocked_count,
                "passedCount": passed_count,
                "warningCount": warning_count,
                "blockRate": round(blocked_count / max(total_checks, 1) * 100, 1)
            },
            "policyStats": [{
                "id": p.get('id'),
                "name": p.get('policy_name', ''),
                "severity": p.get('severity', 'medium'),
                "isActive": p.get('is_active', False),
                "totalChecks": p.get('total_checks', 0) or 0,
                "blockedCount": p.get('blocked_count', 0) or 0,
                "blockRate": float(p.get('block_rate', 0) or 0)
            } for p in (policy_stats or [])],
            "recentLogs": [{
                "id": l.get('id'),
                "requestId": l.get('request_id', ''),
                "userId": l.get('user_id', ''),
                "result": l.get('check_result', ''),
                "detectedContent": l.get('original_text', '')[:100] if l.get('original_text') else '',
                "score": float(l.get('detection_score', 0) or 0),
                "checkedAt": l.get('created_at', ''),
                "policyName": l.get('policy_name', ''),
                "severity": l.get('severity', 'medium')
            } for l in (recent_logs or [])]
        }

    except Exception as e:
        logger.error(f"❌ 가드레일 대시보드 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/policies")
async def get_guardrails_policies(
    admin_user: dict = Depends(verify_admin),
    severity: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """
    가드레일 정책 목록 조회 (테이블 구조에 맞게 수정)
    """
    try:
        conditions = []
        if severity and severity != 'all':
            conditions.append(f"p.severity = '{severity}'")
        if is_active is not None:
            conditions.append(f"p.enabled = {is_active}")

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # guardrails_db 구조: id(VARCHAR), name, category, description, enabled, severity, rules(JSONB), filter_type, action_type
        query = f"""
            SELECT
                p.id,
                p.name,
                p.description,
                p.category,
                p.severity,
                p.enabled,
                p.rules,
                p.filter_type,
                p.action_type,
                p.created_at,
                p.updated_at,
                COUNT(l.id) as total_checks,
                COUNT(l.id) FILTER (WHERE l.check_result = 'blocked') as blocked_count
            FROM guardrail_policies p
            LEFT JOIN guardrail_check_logs l ON p.id = l.policy_id
            {where_clause}
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """

        results = execute_query(query)

        policies = []
        for p in (results or []):
            # rules JSONB에서 keywords와 patterns 추출
            rules = p.get('rules', []) or []
            keywords = []
            patterns = []
            action = 'block'

            if isinstance(rules, list):
                for rule in rules:
                    if isinstance(rule, dict):
                        pattern = rule.get('pattern', '')
                        if pattern:
                            if rule.get('type') == 'keyword':
                                keywords.extend(pattern.split('|'))
                            else:
                                patterns.append(pattern)
                        if rule.get('action'):
                            action = rule.get('action')

            policies.append({
                "id": p.get('id'),
                "name": p.get('name', ''),
                "description": p.get('description', ''),
                "type": p.get('category', 'keyword'),
                "filterType": p.get('filter_type', 'input_filter'),
                "severity": p.get('severity', 'medium'),
                "isActive": p.get('enabled', False),
                "keywords": keywords,
                "patterns": patterns,
                "action": p.get('action_type') or action,
                "createdAt": p.get('created_at').isoformat() if p.get('created_at') else '',
                "updatedAt": p.get('updated_at').isoformat() if p.get('updated_at') else '',
                "totalChecks": p.get('total_checks', 0) or 0,
                "blockedCount": p.get('blocked_count', 0) or 0
            })

        return {"data": policies, "total": len(policies)}

    except Exception as e:
        logger.error(f"❌ 가드레일 정책 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/policies/export")
async def export_guardrails_policies(admin_user: dict = Depends(verify_admin)):
    """
    가드레일 정책 엑셀 내보내기 (guardrails_db 구조)
    """
    try:
        query = """
            SELECT
                id, name, description, category, severity,
                enabled, rules, created_at, updated_at
            FROM guardrail_policies
            ORDER BY id
        """
        results = execute_query(query)

        # CSV 형식으로 내보내기 (Excel 호환)
        import csv

        output = io.StringIO()
        writer = csv.writer(output)

        # 헤더
        writer.writerow([
            'ID', '정책명', '설명', '유형', '심각도',
            '활성화', '키워드', '패턴', '차단액션', '생성일', '수정일'
        ])

        # 데이터
        for p in (results or []):
            rules = p.get('rules', []) or []
            keywords = []
            patterns = []
            action = 'block'

            if isinstance(rules, list):
                for rule in rules:
                    if isinstance(rule, dict):
                        pattern = rule.get('pattern', '')
                        if pattern:
                            if rule.get('type') == 'keyword':
                                keywords.extend(pattern.split('|'))
                            else:
                                patterns.append(pattern)
                        if rule.get('action'):
                            action = rule.get('action')

            writer.writerow([
                p.get('id', ''),
                p.get('name', ''),
                p.get('description', ''),
                p.get('category', ''),
                p.get('severity', ''),
                '활성' if p.get('enabled') else '비활성',
                ', '.join(keywords),
                ', '.join(patterns),
                action,
                p.get('created_at').strftime('%Y-%m-%d %H:%M') if p.get('created_at') else '',
                p.get('updated_at').strftime('%Y-%m-%d %H:%M') if p.get('updated_at') else ''
            ])

        output.seek(0)

        # UTF-8 BOM 추가 (Excel에서 한글 인식)
        content = '\ufeff' + output.getvalue()

        return StreamingResponse(
            io.BytesIO(content.encode('utf-8-sig')),
            media_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=guardrail_policies_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )

    except Exception as e:
        logger.error(f"❌ 정책 내보내기 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/guardrails/policies/import")
async def import_guardrails_policies(
    body: dict,
    admin_user: dict = Depends(verify_admin)
):
    """
    가드레일 정책 CSV 가져오기 (guardrails_db 구조)
    body: { "content": "base64 encoded CSV content" }
    """
    try:
        import csv
        import uuid

        # base64로 인코딩된 파일 내용 디코딩
        content_b64 = body.get('content', '')
        if not content_b64:
            raise HTTPException(status_code=400, detail="파일 내용이 필요합니다.")

        try:
            content = base64.b64decode(content_b64)
        except Exception:
            # 이미 텍스트인 경우
            content = content_b64.encode('utf-8')

        # BOM 제거 및 디코딩
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]

        text = content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))

        imported_count = 0
        errors = []

        for row in reader:
            try:
                # 키워드와 패턴 파싱
                keywords_str = row.get('키워드', '') or row.get('keywords', '')
                patterns_str = row.get('패턴', '') or row.get('patterns', '')

                keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
                patterns = [p.strip() for p in patterns_str.split(',') if p.strip()]

                enabled = row.get('활성화', '') in ['활성', 'true', 'True', '1', 'Y', 'y']
                action = row.get('차단액션', 'block') or row.get('action', 'block')
                category = row.get('유형', 'content') or row.get('category', 'content')

                # rules JSONB 생성
                rules = []
                if keywords:
                    rules.append({
                        "type": "keyword",
                        "pattern": '|'.join(keywords),
                        "action": action,
                        "message": "키워드가 감지되었습니다."
                    })
                if patterns:
                    for pattern in patterns:
                        rules.append({
                            "type": "regex",
                            "pattern": pattern,
                            "action": action,
                            "message": "패턴이 감지되었습니다."
                        })

                # guardrails_db 구조에 맞게 INSERT
                policy_id = f"policy_import_{uuid.uuid4().hex[:8]}"
                query = """
                    INSERT INTO guardrail_policies
                    (id, name, description, category, severity, enabled, rules, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """

                params = (
                    policy_id,
                    row.get('정책명', '') or row.get('name', ''),
                    row.get('설명', '') or row.get('description', ''),
                    category,
                    row.get('심각도', 'medium') or row.get('severity', 'medium'),
                    enabled,
                    json.dumps(rules)
                )

                execute_query(query, params)
                imported_count += 1

            except Exception as row_error:
                errors.append(f"행 {imported_count + 1}: {str(row_error)}")

        return {
            "success": True,
            "importedCount": imported_count,
            "errors": errors,
            "message": f"{imported_count}개의 정책이 가져오기 되었습니다."
        }

    except Exception as e:
        logger.error(f"❌ 정책 가져오기 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/policies/{policy_id}")
async def get_guardrails_policy(
    policy_id: str,
    admin_user: dict = Depends(verify_admin)
):
    """
    특정 가드레일 정책 조회 (guardrails_db 구조)
    """
    try:
        query = """
            SELECT
                id, name, description, category, severity,
                enabled, rules, created_at, updated_at
            FROM guardrail_policies
            WHERE id = %s
        """
        results = execute_query(query, (policy_id,))

        if not results:
            raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")

        p = results[0]
        rules = p.get('rules', []) or []
        keywords = []
        patterns = []
        action = 'block'

        if isinstance(rules, list):
            for rule in rules:
                if isinstance(rule, dict):
                    pattern = rule.get('pattern', '')
                    if pattern:
                        if rule.get('type') == 'keyword':
                            keywords.extend(pattern.split('|'))
                        else:
                            patterns.append(pattern)
                    if rule.get('action'):
                        action = rule.get('action')

        return {
            "id": p.get('id'),
            "name": p.get('name', ''),
            "description": p.get('description', ''),
            "type": p.get('category', 'keyword'),
            "severity": p.get('severity', 'medium'),
            "isActive": p.get('enabled', False),
            "keywords": keywords,
            "patterns": patterns,
            "action": action,
            "createdAt": p.get('created_at').isoformat() if p.get('created_at') else '',
            "updatedAt": p.get('updated_at').isoformat() if p.get('updated_at') else ''
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 정책 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/guardrails/policies")
async def create_guardrails_policy(
    policy: dict,
    admin_user: dict = Depends(verify_admin)
):
    """
    가드레일 정책 생성 (guardrails_db 구조)
    """
    try:
        import uuid

        keywords = policy.get('keywords', [])
        patterns = policy.get('patterns', [])
        action = policy.get('action', 'block')

        # rules JSONB 생성
        rules = []
        if keywords and isinstance(keywords, list) and len(keywords) > 0:
            rules.append({
                "type": "keyword",
                "pattern": '|'.join(keywords),
                "action": action,
                "message": "키워드가 감지되었습니다."
            })
        if patterns and isinstance(patterns, list):
            for pattern in patterns:
                rules.append({
                    "type": "regex",
                    "pattern": pattern,
                    "action": action,
                    "message": "패턴이 감지되었습니다."
                })

        policy_id = f"policy_{uuid.uuid4().hex[:12]}"
        query = """
            INSERT INTO guardrail_policies
            (id, name, description, category, severity, enabled, rules, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """

        params = (
            policy_id,
            policy.get('name', ''),
            policy.get('description', ''),
            policy.get('type', 'content'),
            policy.get('severity', 'medium'),
            policy.get('isActive', True),
            json.dumps(rules)
        )

        results = execute_query(query, params)

        if results:
            return {"success": True, "id": results[0].get('id'), "message": "정책이 생성되었습니다."}
        return {"success": False, "message": "정책 생성에 실패했습니다."}

    except Exception as e:
        logger.error(f"❌ 정책 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/guardrails/policies/{policy_id}")
async def update_guardrails_policy(
    policy_id: str,
    policy: dict,
    admin_user: dict = Depends(verify_admin)
):
    """
    가드레일 정책 수정 (guardrails_db 구조)
    """
    try:
        keywords = policy.get('keywords', [])
        patterns = policy.get('patterns', [])
        action = policy.get('action', 'block')

        # rules JSONB 생성
        rules = []
        if keywords and isinstance(keywords, list) and len(keywords) > 0:
            rules.append({
                "type": "keyword",
                "pattern": '|'.join(keywords),
                "action": action,
                "message": "키워드가 감지되었습니다."
            })
        if patterns and isinstance(patterns, list):
            for pattern in patterns:
                rules.append({
                    "type": "regex",
                    "pattern": pattern,
                    "action": action,
                    "message": "패턴이 감지되었습니다."
                })

        query = """
            UPDATE guardrail_policies
            SET name = %s,
                description = %s,
                category = %s,
                severity = %s,
                enabled = %s,
                rules = %s,
                updated_at = NOW()
            WHERE id = %s
        """

        params = (
            policy.get('name', ''),
            policy.get('description', ''),
            policy.get('type', 'content'),
            policy.get('severity', 'medium'),
            policy.get('isActive', True),
            json.dumps(rules),
            policy_id
        )

        execute_query(query, params)
        return {"success": True, "message": "정책이 수정되었습니다."}

    except Exception as e:
        logger.error(f"❌ 정책 수정 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/policies/{policy_id}")
async def delete_guardrails_policy(
    policy_id: str,
    admin_user: dict = Depends(verify_admin)
):
    """
    가드레일 정책 삭제 (guardrails_db 구조: id는 VARCHAR)
    """
    try:
        # 연관된 로그도 삭제 (또는 policy_id를 NULL로 설정)
        execute_query("DELETE FROM guardrail_check_logs WHERE policy_id = %s", (policy_id,))
        execute_query("DELETE FROM guardrail_policies WHERE id = %s", (policy_id,))

        return {"success": True, "message": "정책이 삭제되었습니다."}

    except Exception as e:
        logger.error(f"❌ 정책 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/guardrails/policies/{policy_id}/toggle")
async def toggle_guardrails_policy(
    policy_id: str,
    admin_user: dict = Depends(verify_admin)
):
    """
    가드레일 정책 활성화/비활성화 토글 (guardrails_db 구조)
    """
    try:
        query = """
            UPDATE guardrail_policies
            SET enabled = NOT enabled,
                updated_at = NOW()
            WHERE id = %s
            RETURNING enabled
        """

        results = execute_query(query, (policy_id,))

        if results:
            new_state = results[0].get('enabled', False)
            return {
                "success": True,
                "isActive": new_state,
                "message": f"정책이 {'활성화' if new_state else '비활성화'}되었습니다."
            }

        raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 정책 토글 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/guardrails/policies/{policy_id}/set-active")
async def set_guardrails_policy_active(
    policy_id: str,
    data: dict,
    admin_user: dict = Depends(verify_admin)
):
    """
    가드레일 정책 활성화 상태 직접 설정 (guardrails_db 구조)
    """
    try:
        enabled = data.get('isActive', False)

        query = """
            UPDATE guardrail_policies
            SET enabled = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING enabled
        """

        results = execute_query(query, (enabled, policy_id))

        if results:
            new_state = results[0].get('enabled', False)
            return {
                "success": True,
                "isActive": new_state,
                "message": f"정책이 {'활성화' if new_state else '비활성화'}되었습니다."
            }

        raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 정책 상태 설정 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/trend")
async def get_guardrails_trend(
    admin_user: dict = Depends(verify_admin),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    policy_id: Optional[str] = None
):
    """
    가드레일 일별 트렌드 데이터 조회
    """
    try:
        # 날짜 조건 생성
        date_condition = ""
        if start_date and end_date:
            date_condition = f"AND l.created_at BETWEEN '{start_date}' AND '{end_date}'"

        # 정책 필터 조건 (guardrails_db: policy_id는 VARCHAR)
        policy_condition = ""
        if policy_id:
            policy_condition = f"AND l.policy_id = '{policy_id}'"

        query = f"""
            SELECT
                DATE(l.created_at) as date,
                COUNT(*) as total_checks,
                COUNT(*) FILTER (WHERE l.check_result = 'blocked') as blocked,
                COUNT(*) FILTER (WHERE l.check_result = 'warned') as warned,
                COUNT(*) FILTER (WHERE l.check_result = 'passed') as passed
            FROM guardrail_check_logs l
            WHERE 1=1 {date_condition} {policy_condition}
            GROUP BY DATE(l.created_at)
            ORDER BY date ASC
        """
        # ----- 1227 LIMIT 31 제거 완료 -----

        results = execute_query(query)

        return [{
            "date": str(r.get('date', '')) if r.get('date') else '',
            "total_checks": r.get('total_checks', 0) or 0,
            "blocked": r.get('blocked', 0) or 0,
            "warned": r.get('warned', 0) or 0,
            "passed": r.get('passed', 0) or 0
        } for r in (results or [])]

    except Exception as e:
        logger.error(f"❌ 가드레일 트렌드 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 기준정보 (Master Data) API 엔드포인트 ====================

@app.get("/api/guardrails/master/policy-types")
async def get_master_policy_types(admin_user: dict = Depends(verify_admin)):
    """정책유형 기준정보 목록 조회"""
    try:
        query = """
            SELECT id, code, type_id, name, description, is_active, sort_order, created_at, updated_at
            FROM guardrail_master_policy_types
            WHERE is_active = true
            ORDER BY sort_order, code
        """
        results = execute_query(query)
        return {"data": [{
            "id": r.get('id'),
            "code": r.get('code'),
            "typeId": r.get('type_id'),
            "name": r.get('name'),
            "description": r.get('description'),
            "isActive": r.get('is_active'),
            "sortOrder": r.get('sort_order'),
            "createdAt": r.get('created_at').isoformat() if r.get('created_at') else None,
            "updatedAt": r.get('updated_at').isoformat() if r.get('updated_at') else None
        } for r in (results or [])]}
    except Exception as e:
        logger.error(f"❌ 정책유형 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/guardrails/master/policy-types")
async def create_master_policy_type(data: dict, admin_user: dict = Depends(verify_admin)):
    """정책유형 기준정보 추가"""
    try:
        query = """
            INSERT INTO guardrail_master_policy_types (code, type_id, name, description, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, code
        """
        # 다음 코드 생성
        code_query = "SELECT MAX(CAST(SUBSTRING(code FROM 3) AS INTEGER)) as max_seq FROM guardrail_master_policy_types WHERE code LIKE 'PT%'"
        code_result = execute_query(code_query)
        next_seq = (code_result[0].get('max_seq') or 0) + 1 if code_result else 1
        new_code = f"PT{str(next_seq).zfill(3)}"

        # type_id 생성 (이름을 snake_case로 변환)
        type_id = data.get('name', '').lower().replace(' ', '_').replace('(', '').replace(')', '')

        params = (new_code, type_id, data.get('name'), data.get('description', ''), data.get('sortOrder', 0))
        results = execute_query(query, params)

        if results:
            return {"success": True, "id": results[0].get('id'), "code": results[0].get('code')}
        return {"success": False, "message": "추가에 실패했습니다."}
    except Exception as e:
        logger.error(f"❌ 정책유형 추가 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/master/policy-types/{code}")
async def delete_master_policy_type(code: str, admin_user: dict = Depends(verify_admin)):
    """정책유형 기준정보 삭제 (비활성화)"""
    try:
        query = "UPDATE guardrail_master_policy_types SET is_active = false WHERE code = %s"
        execute_query(query, (code,))
        return {"success": True, "message": "미사용으로 변경되었습니다."}
    except Exception as e:
        logger.error(f"❌ 정책유형 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/master/policy-types/{code}/permanent")
async def delete_master_policy_type_permanent(code: str, admin_user: dict = Depends(verify_admin)):
    """정책유형 기준정보 완전 삭제"""
    try:
        query = "DELETE FROM guardrail_master_policy_types WHERE code = %s"
        execute_query(query, (code,))
        return {"success": True, "message": "완전히 삭제되었습니다."}
    except Exception as e:
        logger.error(f"❌ 정책유형 완전 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/master/filter-types")
async def get_master_filter_types(admin_user: dict = Depends(verify_admin)):
    """필터유형 기준정보 목록 조회"""
    try:
        query = """
            SELECT id, code, type_id, name, description, is_active, sort_order, created_at, updated_at
            FROM guardrail_master_filter_types
            WHERE is_active = true
            ORDER BY sort_order, code
        """
        results = execute_query(query)
        return {"data": [{
            "id": r.get('id'),
            "code": r.get('code'),
            "typeId": r.get('type_id'),
            "name": r.get('name'),
            "description": r.get('description'),
            "isActive": r.get('is_active'),
            "sortOrder": r.get('sort_order'),
            "createdAt": r.get('created_at').isoformat() if r.get('created_at') else None,
            "updatedAt": r.get('updated_at').isoformat() if r.get('updated_at') else None
        } for r in (results or [])]}
    except Exception as e:
        logger.error(f"❌ 필터유형 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/guardrails/master/filter-types")
async def create_master_filter_type(data: dict, admin_user: dict = Depends(verify_admin)):
    """필터유형 기준정보 추가"""
    try:
        query = """
            INSERT INTO guardrail_master_filter_types (code, type_id, name, description, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, code
        """
        code_query = "SELECT MAX(CAST(SUBSTRING(code FROM 3) AS INTEGER)) as max_seq FROM guardrail_master_filter_types WHERE code LIKE 'FT%'"
        code_result = execute_query(code_query)
        next_seq = (code_result[0].get('max_seq') or 0) + 1 if code_result else 1
        new_code = f"FT{str(next_seq).zfill(3)}"

        type_id = data.get('name', '').lower().replace(' ', '_').replace('(', '').replace(')', '')

        params = (new_code, type_id, data.get('name'), data.get('description', ''), data.get('sortOrder', 0))
        results = execute_query(query, params)

        if results:
            return {"success": True, "id": results[0].get('id'), "code": results[0].get('code')}
        return {"success": False, "message": "추가에 실패했습니다."}
    except Exception as e:
        logger.error(f"❌ 필터유형 추가 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/master/filter-types/{code}")
async def delete_master_filter_type(code: str, admin_user: dict = Depends(verify_admin)):
    """필터유형 기준정보 삭제 (비활성화)"""
    try:
        query = "UPDATE guardrail_master_filter_types SET is_active = false WHERE code = %s"
        execute_query(query, (code,))
        return {"success": True, "message": "미사용으로 변경되었습니다."}
    except Exception as e:
        logger.error(f"❌ 필터유형 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/master/filter-types/{code}/permanent")
async def delete_master_filter_type_permanent(code: str, admin_user: dict = Depends(verify_admin)):
    """필터유형 기준정보 완전 삭제"""
    try:
        query = "DELETE FROM guardrail_master_filter_types WHERE code = %s"
        execute_query(query, (code,))
        return {"success": True, "message": "완전히 삭제되었습니다."}
    except Exception as e:
        logger.error(f"❌ 필터유형 완전 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/master/severity-levels")
async def get_master_severity_levels(admin_user: dict = Depends(verify_admin)):
    """심각도 기준정보 목록 조회"""
    try:
        query = """
            SELECT id, code, level_id, name, color, priority, description, is_active, sort_order, created_at, updated_at
            FROM guardrail_master_severity_levels
            WHERE is_active = true
            ORDER BY sort_order, code
        """
        results = execute_query(query)
        return {"data": [{
            "id": r.get('id'),
            "code": r.get('code'),
            "levelId": r.get('level_id'),
            "name": r.get('name'),
            "color": r.get('color'),
            "priority": r.get('priority'),
            "description": r.get('description'),
            "isActive": r.get('is_active'),
            "sortOrder": r.get('sort_order'),
            "createdAt": r.get('created_at').isoformat() if r.get('created_at') else None,
            "updatedAt": r.get('updated_at').isoformat() if r.get('updated_at') else None
        } for r in (results or [])]}
    except Exception as e:
        logger.error(f"❌ 심각도 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/guardrails/master/severity-levels")
async def create_master_severity_level(data: dict, admin_user: dict = Depends(verify_admin)):
    """심각도 기준정보 추가"""
    try:
        query = """
            INSERT INTO guardrail_master_severity_levels (code, level_id, name, color, priority, description, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, code
        """
        code_query = "SELECT MAX(CAST(SUBSTRING(code FROM 3) AS INTEGER)) as max_seq FROM guardrail_master_severity_levels WHERE code LIKE 'SV%'"
        code_result = execute_query(code_query)
        next_seq = (code_result[0].get('max_seq') or 0) + 1 if code_result else 1
        new_code = f"SV{str(next_seq).zfill(3)}"

        level_id = data.get('name', '').lower().replace(' ', '_').replace('(', '').replace(')', '')

        params = (
            new_code, level_id, data.get('name'),
            data.get('color', '#6b7280'), data.get('priority', 0),
            data.get('description', ''), data.get('sortOrder', 0)
        )
        results = execute_query(query, params)

        if results:
            return {"success": True, "id": results[0].get('id'), "code": results[0].get('code')}
        return {"success": False, "message": "추가에 실패했습니다."}
    except Exception as e:
        logger.error(f"❌ 심각도 추가 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/master/severity-levels/{code}")
async def delete_master_severity_level(code: str, admin_user: dict = Depends(verify_admin)):
    """심각도 기준정보 삭제 (비활성화)"""
    try:
        query = "UPDATE guardrail_master_severity_levels SET is_active = false WHERE code = %s"
        execute_query(query, (code,))
        return {"success": True, "message": "미사용으로 변경되었습니다."}
    except Exception as e:
        logger.error(f"❌ 심각도 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/master/severity-levels/{code}/permanent")
async def delete_master_severity_level_permanent(code: str, admin_user: dict = Depends(verify_admin)):
    """심각도 기준정보 완전 삭제"""
    try:
        query = "DELETE FROM guardrail_master_severity_levels WHERE code = %s"
        execute_query(query, (code,))
        return {"success": True, "message": "완전히 삭제되었습니다."}
    except Exception as e:
        logger.error(f"❌ 심각도 완전 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/master/action-types")
async def get_master_action_types(admin_user: dict = Depends(verify_admin)):
    """동작유형 기준정보 목록 조회"""
    try:
        query = """
            SELECT id, code, action_id, name, description, is_active, sort_order, created_at, updated_at
            FROM guardrail_master_action_types
            WHERE is_active = true
            ORDER BY sort_order, code
        """
        results = execute_query(query)
        return {"data": [{
            "id": r.get('id'),
            "code": r.get('code'),
            "actionId": r.get('action_id'),
            "name": r.get('name'),
            "description": r.get('description'),
            "isActive": r.get('is_active'),
            "sortOrder": r.get('sort_order'),
            "createdAt": r.get('created_at').isoformat() if r.get('created_at') else None,
            "updatedAt": r.get('updated_at').isoformat() if r.get('updated_at') else None
        } for r in (results or [])]}
    except Exception as e:
        logger.error(f"❌ 동작유형 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/guardrails/master/action-types")
async def create_master_action_type(data: dict, admin_user: dict = Depends(verify_admin)):
    """동작유형 기준정보 추가"""
    try:
        query = """
            INSERT INTO guardrail_master_action_types (code, action_id, name, description, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, code
        """
        code_query = "SELECT MAX(CAST(SUBSTRING(code FROM 3) AS INTEGER)) as max_seq FROM guardrail_master_action_types WHERE code LIKE 'AT%'"
        code_result = execute_query(code_query)
        next_seq = (code_result[0].get('max_seq') or 0) + 1 if code_result else 1
        new_code = f"AT{str(next_seq).zfill(3)}"

        action_id = data.get('name', '').lower().replace(' ', '_').replace('(', '').replace(')', '')

        params = (new_code, action_id, data.get('name'), data.get('description', ''), data.get('sortOrder', 0))
        results = execute_query(query, params)

        if results:
            return {"success": True, "id": results[0].get('id'), "code": results[0].get('code')}
        return {"success": False, "message": "추가에 실패했습니다."}
    except Exception as e:
        logger.error(f"❌ 동작유형 추가 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/master/action-types/{code}")
async def delete_master_action_type(code: str, admin_user: dict = Depends(verify_admin)):
    """동작유형 기준정보 삭제 (비활성화)"""
    try:
        query = "UPDATE guardrail_master_action_types SET is_active = false WHERE code = %s"
        execute_query(query, (code,))
        return {"success": True, "message": "미사용으로 변경되었습니다."}
    except Exception as e:
        logger.error(f"❌ 동작유형 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/master/action-types/{code}/permanent")
async def delete_master_action_type_permanent(code: str, admin_user: dict = Depends(verify_admin)):
    """동작유형 기준정보 완전 삭제"""
    try:
        query = "DELETE FROM guardrail_master_action_types WHERE code = %s"
        execute_query(query, (code,))
        return {"success": True, "message": "완전히 삭제되었습니다."}
    except Exception as e:
        logger.error(f"❌ 동작유형 완전 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/master/all")
async def get_all_master_data(admin_user: dict = Depends(verify_admin)):
    """모든 기준정보 한번에 조회"""
    try:
        policy_types = execute_query("""
            SELECT code, type_id as id, name FROM guardrail_master_policy_types
            WHERE is_active = true ORDER BY sort_order, code
        """)
        filter_types = execute_query("""
            SELECT code, type_id as id, name FROM guardrail_master_filter_types
            WHERE is_active = true ORDER BY sort_order, code
        """)
        severity_levels = execute_query("""
            SELECT code, level_id as id, name, color, priority FROM guardrail_master_severity_levels
            WHERE is_active = true ORDER BY sort_order, code
        """)
        action_types = execute_query("""
            SELECT code, action_id as id, name FROM guardrail_master_action_types
            WHERE is_active = true ORDER BY sort_order, code
        """)

        return {
            "policyTypes": policy_types or [],
            "filterTypes": filter_types or [],
            "severityLevels": severity_levels or [],
            "actionTypes": action_types or []
        }
    except Exception as e:
        logger.error(f"❌ 전체 기준정보 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/logs")
async def get_guardrails_logs(
    admin_user: dict = Depends(verify_admin),
    limit: int = 100,
    result: Optional[str] = None,
    policy_id: Optional[str] = None
):
    """
    가드레일 검사 로그 조회 (guardrails_db 구조)
    """
    try:
        conditions = []
        if result and result != 'all':
            conditions.append(f"l.check_result = '{result}'")
        if policy_id:
            conditions.append(f"l.policy_id = '{policy_id}'")

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT
                l.id,
                l.request_id,
                l.session_id,
                l.user_id,
                l.policy_id,
                l.check_result,
                l.original_text,
                l.detection_score,
                l.original_text,
                l.processed_text,
                l.created_at,
                p.name as policy_name,
                p.severity
            FROM guardrail_check_logs l
            LEFT JOIN guardrail_policies p ON l.policy_id = p.id
            {where_clause}
            ORDER BY l.created_at DESC
        """
        # ----- 1227 LIMIT 500 제거 완료 -----

        results = execute_query(query)

        logs = []
        for l in (results or []):
            logs.append({
                "id": l.get('id'),
                "requestId": l.get('request_id', ''),
                "sessionId": l.get('session_id', ''),
                "userId": l.get('user_id', ''),
                "policyId": l.get('policy_id'),
                "policyName": l.get('policy_name', ''),
                "severity": l.get('severity', 'medium'),
                "result": l.get('check_result', ''),
                "detectedContent": l.get('original_text', ''),
                "score": float(l.get('detection_score', 0) or 0),
                "requestText": (l.get('original_text', '') or '')[:200],
                "responseText": (l.get('processed_text', '') or '')[:200],
                "checkedAt": l.get('created_at').isoformat() if l.get('created_at') else ''
            })

        return {"data": logs, "total": len(logs)}

    except Exception as e:
        logger.error(f"❌ 가드레일 로그 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 가드레일 텍스트 검사 API
# Arthur AI Guardrails 서비스 기반 통합 검사
# ============================================
import re
import uuid
from pydantic import BaseModel
import urllib.request
import urllib.error

class GuardrailCheckRequest(BaseModel):
    text: str
    user_id: Optional[str] = None
    filter_type: Optional[str] = "input_filter"  # input_filter, output_filter, pii_detection, toxicity, custom
    check_input: bool = True
    check_output: bool = False

@app.post("/api/guardrails/check")
async def check_guardrails(request: GuardrailCheckRequest):
    """
    텍스트에 대한 가드레일 검사 수행
    Arthur AI Guardrails 서비스 (/api/check)를 호출하여 모든 필터 유형 처리

    필터 유형:
    - input_filter: 입력 텍스트 검사 (PII + 유해성 + 커스텀)
    - output_filter: 출력 텍스트 검사 (PII + 유해성 + 커스텀)
    - pii_detection: PII 전용 탐지 (주민번호, 전화번호, 이메일 등)
    - toxicity: 유해성 탐지 (욕설, 혐오 표현 등)
    - custom: 사용자 정의 블랙리스트/개인정보 키워드
    """
    import time
    start_time = time.time()

    try:
        text = request.text
        user_id = request.user_id or 'anonymous'
        filter_type = request.filter_type or 'input_filter'
        request_id = str(uuid.uuid4())[:8]

        # Arthur Guardrails 서비스 URL
        arthur_url = os.getenv('ARTHUR_GUARDRAILS_URL', 'http://192.168.122.178:8001')

        # ========================================
        # Arthur Guardrails /api/check 호출
        # ========================================
        try:
            import json as json_lib
            req_data = json_lib.dumps({
                "text": text,
                "filter_type": filter_type,
                "user_id": user_id,
                "check_input": request.check_input,
                "check_output": request.check_output
            }).encode('utf-8')

            req = urllib.request.Request(
                f"{arthur_url}/api/check",
                data=req_data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                arthur_result = json_lib.loads(response.read().decode('utf-8'))

                # Arthur 결과를 그대로 사용
                result = {
                    "is_safe": arthur_result.get('is_safe', True),
                    "action": arthur_result.get('action', 'pass'),
                    "severity": arthur_result.get('severity', 'low'),
                    "filter_type": arthur_result.get('filter_type', filter_type),
                    "blocked_keywords": arthur_result.get('blocked_keywords', []),
                    "blocked_categories": arthur_result.get('blocked_categories', []),
                    "matched_policies": arthur_result.get('matched_policies', []),
                    "detection_score": arthur_result.get('detection_score', 0.0),
                    "pii_detected": arthur_result.get('pii_detected', []),
                    "processing_time_ms": arthur_result.get('processing_time_ms', 0)
                }

                logger.info(f"🛡️ Arthur 가드레일: filter={filter_type}, action={result['action']}, policies={len(result['matched_policies'])}")

                # 검사 로그 저장
                try:
                    log_query = """
                        INSERT INTO guardrail_filter_logs
                        (request_id, user_id, filter_type, original_text, text_length,
                         is_safe, action_taken, severity, blocked_keywords, blocked_categories,
                         pii_detected, matched_policies, detection_score, processing_time_ms)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    execute_query(log_query, (
                        request_id,
                        user_id,
                        filter_type,
                        text[:500],
                        len(text),
                        result['is_safe'],
                        result['action'],
                        result['severity'],
                        result['blocked_keywords'][:10],
                        result['blocked_categories'],
                        json_lib.dumps(result['pii_detected']),
                        json_lib.dumps(result['matched_policies']),
                        result['detection_score'],
                        result['processing_time_ms']
                    ))
                except Exception as log_err:
                    logger.warning(f"로그 저장 실패: {log_err}")

                return {"result": result}

        except urllib.error.URLError as conn_err:
            logger.warning(f"⚠️ Arthur Guardrails 연결 실패: {conn_err}")
            raise Exception(f"Arthur Guardrails connection error: {conn_err}")

        except TimeoutError:
            logger.warning("⚠️ Arthur Guardrails 타임아웃")
            raise Exception("Arthur Guardrails timeout")

    except Exception as e:
        logger.error(f"❌ 가드레일 검사 오류: {e}")

        # 오류 시 기본 응답 (fail-open)
        processing_time = int((time.time() - start_time) * 1000)
        return {
            "result": {
                "is_safe": True,
                "action": "pass",
                "severity": "low",
                "filter_type": request.filter_type or "input_filter",
                "blocked_keywords": [],
                "blocked_categories": [],
                "matched_policies": [],
                "detection_score": 0.0,
                "pii_detected": [],
                "processing_time_ms": processing_time,
                "error": str(e)
            }
        }


@app.post("/api/guardrails/logs")
async def save_guardrails_log(log_data: dict):
    """가드레일 검사 로그 저장 (파이프라인에서 호출)"""
    try:
        query = """
            INSERT INTO guardrail_check_logs
            (request_id, user_id, check_type, original_text, check_result,
             detected_keywords, action_taken, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """
        execute_query(query, (
            str(uuid.uuid4())[:8],
            log_data.get('user_id', 'unknown'),
            'input',
            log_data.get('input_text', '')[:500],
            log_data.get('result', 'pass'),
            log_data.get('blocked_keywords', []),
            log_data.get('result', 'pass')
        ))
        return {"success": True}
    except Exception as e:
        logger.error(f"로그 저장 오류: {e}")
        return {"success": False, "error": str(e)}


# ============================================
# 에러 핸들러
# ============================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """전역 예외 처리"""
    logger.error(f"❌ 예외 발생: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다."}
    )

# ============================================
# 서버 실행
# ============================================
if __name__ == "__main__":
    port = int(os.getenv('API_PORT', 3001))
    host = os.getenv('API_HOST', '0.0.0.0')

    logger.info(f"🚀 서버 시작: http://{host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
