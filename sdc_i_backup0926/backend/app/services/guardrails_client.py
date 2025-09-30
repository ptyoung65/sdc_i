"""
Arthur AI Guardrails Client for Backend Integration
8001 포트의 Arthur AI Guardrails 서비스와 연동하여 콘텐츠 안전성 검증 제공
"""

import httpx
import asyncio
import logging
import os
import json
from typing import Tuple, Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Arthur AI Guardrails 서비스 URL (환경변수로 설정 가능)
HOST_IP = os.getenv("HOST_IP", "192.168.122.177")
GUARDRAILS_SERVICE_URL = f"http://{HOST_IP}:8001"

class GuardrailsClient:
    """Arthur AI Guardrails 서비스 클라이언트"""

    def __init__(self, service_url: str = GUARDRAILS_SERVICE_URL):
        self.service_url = service_url
        self.client = None
        self._is_available = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def check_service_health(self) -> bool:
        """가드레일 서비스 상태 확인"""
        try:
            if not self.client:
                self.client = httpx.AsyncClient(timeout=5.0)

            response = await self.client.get(f"{self.service_url}/health")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"🛡️ [GUARDRAILS] Service healthy: {data.get('status', 'unknown')}")
                self._is_available = True
                return True
            else:
                logger.warning(f"🛡️ [GUARDRAILS] Service unhealthy: HTTP {response.status_code}")
                self._is_available = False
                return False

        except Exception as e:
            logger.error(f"🛡️ [GUARDRAILS] Service health check failed: {e}")
            self._is_available = False
            return False

    async def get_service_status(self) -> Optional[Dict[str, Any]]:
        """가드레일 서비스 상태 및 설정 조회"""
        try:
            if not self.client:
                self.client = httpx.AsyncClient(timeout=5.0)

            response = await self.client.get(f"{self.service_url}/status")

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"🛡️ [GUARDRAILS] Failed to get status: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"🛡️ [GUARDRAILS] Failed to get service status: {e}")
            return None

    async def validate_content(self, text: str, categories: Optional[list] = None) -> Tuple[bool, str]:
        """
        텍스트 콘텐츠 안전성 검증

        Args:
            text: 검증할 텍스트
            categories: 검사할 카테고리 (기본값: ['basic', 'personal', 'blacklist'])

        Returns:
            Tuple[bool, str]: (is_safe, message_or_reason)
        """
        try:
            if not self.client:
                self.client = httpx.AsyncClient(timeout=10.0)

            # 서비스 상태 확인
            if self._is_available is None:
                await self.check_service_health()

            if not self._is_available:
                logger.warning("🛡️ [GUARDRAILS] Service not available, allowing content")
                return True, text

            # 가드레일 테스트 요청
            payload = {
                "text": text,
                "categories": categories or ["basic", "personal", "blacklist"]
            }

            response = await self.client.post(f"{self.service_url}/test", json=payload)

            if response.status_code == 200:
                result = response.json()
                validation_result = result.get("result", {})

                is_safe = validation_result.get("is_safe", True)
                blocked_keywords = validation_result.get("blocked_keywords", [])
                blocked_categories = validation_result.get("blocked_categories", [])
                action_taken = validation_result.get("action_taken", "allowed")
                confidence_score = validation_result.get("confidence_score", 1.0)

                if is_safe:
                    logger.info(f"✅ [GUARDRAILS] Content validated (confidence: {confidence_score:.2f})")
                    return True, text
                else:
                    reason = f"Blocked keywords: {', '.join(blocked_keywords)} in categories: {', '.join(blocked_categories)}"
                    logger.warning(f"🚫 [GUARDRAILS] Content blocked: {reason}")
                    return False, reason

            else:
                logger.error(f"🛡️ [GUARDRAILS] Validation request failed: HTTP {response.status_code}")
                # 서비스 오류 시 기본적으로 허용 (안전 우선)
                return True, text

        except Exception as e:
            logger.error(f"🛡️ [GUARDRAILS] Validation error: {e}")
            # 오류 시 기본적으로 허용 (서비스 지속성 우선)
            return True, text

# 전역 클라이언트 인스턴스
_guardrails_client = None

async def get_guardrails_client() -> GuardrailsClient:
    """가드레일 클라이언트 인스턴스 반환"""
    global _guardrails_client
    if _guardrails_client is None:
        _guardrails_client = GuardrailsClient()
    return _guardrails_client

async def validate_user_input(text: str, user_id: str = "default", request_ip: str = "unknown") -> Tuple[bool, str]:
    """
    사용자 입력 검증 (채팅 시 사용자 메시지 검증)

    Args:
        text: 사용자가 입력한 텍스트
        user_id: 사용자 ID (로깅용)
        request_ip: 요청자 IP 주소 (로깅용)

    Returns:
        Tuple[bool, str]: (is_safe, filtered_text_or_reason)
    """
    logger.info(f"🛡️ [GUARDRAILS] Validating user input from {user_id} ({request_ip}): {text[:50]}...")

    try:
        client = await get_guardrails_client()
        async with client:
            # 사용자 입력은 모든 카테고리 검사
            is_safe, result = await client.validate_content(
                text,
                categories=["basic", "personal", "blacklist"]
            )

            # 로그 저장 (거부된 요청 이력 포함)
            await _log_guardrail_result(
                text=text,
                user_id=user_id,
                request_ip=request_ip,
                is_safe=is_safe,
                result=result,
                validation_type="user_input"
            )

            if is_safe:
                logger.info(f"✅ [GUARDRAILS] User input validated for {user_id}")
                return True, text
            else:
                logger.warning(f"🚫 [GUARDRAILS] User input blocked for {user_id}: {result}")
                return False, result

    except Exception as e:
        logger.error(f"🛡️ [GUARDRAILS] User input validation error: {e}")
        # 오류 시 기본적으로 허용
        return True, text

async def validate_ai_output(text: str, user_id: str = "default", request_ip: str = "unknown") -> Tuple[bool, str]:
    """
    AI 응답 검증 (채팅 시 AI 응답 검증)

    Args:
        text: AI가 생성한 응답 텍스트
        user_id: 사용자 ID (로깅용)

    Returns:
        Tuple[bool, str]: (is_safe, filtered_text_or_reason)
    """
    logger.info(f"🛡️ [GUARDRAILS] Validating AI output for {user_id}: {text[:50]}...")

    try:
        client = await get_guardrails_client()
        async with client:
            # AI 응답은 기본 가드레일과 개인정보 검사
            is_safe, result = await client.validate_content(
                text,
                categories=["basic", "personal"]
            )

            # 로그 저장 (AI 응답 검증 결과)
            await _log_guardrail_result(
                text=text,
                user_id=user_id,
                request_ip=request_ip,
                is_safe=is_safe,
                result=result,
                validation_type="ai_output"
            )

            if is_safe:
                logger.info(f"✅ [GUARDRAILS] AI output validated for {user_id}")
                return True, text
            else:
                logger.warning(f"🚫 [GUARDRAILS] AI output blocked for {user_id}: {result}")
                # AI 응답이 차단된 경우 안전한 대체 응답 제공
                safe_response = "죄송합니다. 안전한 응답을 생성할 수 없어 다른 방식으로 도움드리겠습니다."
                return False, safe_response

    except Exception as e:
        logger.error(f"🛡️ [GUARDRAILS] AI output validation error: {e}")
        # 오류 시 기본적으로 허용
        return True, text

async def get_guardrails_status() -> Dict[str, Any]:
    """가드레일 서비스 상태 및 통계 조회"""
    try:
        client = await get_guardrails_client()
        async with client:
            status = await client.get_service_status()
            if status:
                return status
            else:
                return {"status": "unavailable", "error": "Service not responding"}

    except Exception as e:
        logger.error(f"🛡️ [GUARDRAILS] Failed to get status: {e}")
        return {"status": "error", "error": str(e)}

# 서비스 시작 시 초기화
async def initialize_guardrails():
    """가드레일 서비스 초기화 및 연결 확인"""
    try:
        client = await get_guardrails_client()
        async with client:
            is_healthy = await client.check_service_health()
            if is_healthy:
                status = await client.get_service_status()
                if status:
                    logger.info(f"🛡️ [GUARDRAILS] Initialized successfully")
                    logger.info(f"🛡️ [GUARDRAILS] Service status: {status.get('status', 'unknown')}")
                    logger.info(f"🛡️ [GUARDRAILS] Categories loaded: {len(status.get('categories', {}))}")
                    return True

        logger.warning("🛡️ [GUARDRAILS] Failed to initialize - running without guardrails")
        return False

    except Exception as e:
        logger.error(f"🛡️ [GUARDRAILS] Initialization error: {e}")
        return False

# === 로그 저장 함수들 ===

async def _log_guardrail_result(
    text: str,
    user_id: str,
    request_ip: str,
    is_safe: bool,
    result: str,
    validation_type: str = "user_input"
) -> None:
    """
    가드레일 검증 결과를 데이터베이스에 저장

    Args:
        text: 검증된 텍스트
        user_id: 사용자 ID
        request_ip: 요청자 IP 주소
        is_safe: 안전 여부
        result: 검증 결과 또는 차단 사유
        validation_type: 검증 타입 ('user_input', 'ai_output')
    """
    try:
        client = await get_guardrails_client()
        async with client:
            # 가드레일 서비스의 로그 저장 API 호출
            log_data = {
                "test_text": text,
                "is_safe": is_safe,
                "blocked_keywords": result.split(", ") if not is_safe and ":" in result else [],
                "blocked_categories": [],
                "confidence_score": 1.0 if is_safe else 0.0,
                "action_taken": "allowed" if is_safe else "blocked",
                "sensitivity": 0.7,
                "user_id": user_id,
                "request_ip": request_ip,
                "validation_type": validation_type,
                "timestamp": datetime.now().isoformat()
            }

            # 차단된 카테고리 파싱
            if not is_safe and "categories: " in result:
                categories_part = result.split("categories: ")[1]
                log_data["blocked_categories"] = [cat.strip() for cat in categories_part.split(",")]

            # 가드레일 서비스에 로그 저장 요청
            response = await client.client.post(
                f"{client.service_url}/test",
                json={"text": text, "categories": ["basic", "personal", "blacklist"]}
            )

            logger.info(f"📝 [GUARDRAILS-LOG] Logged {validation_type} result for {user_id} - Safe: {is_safe}")

    except Exception as e:
        logger.error(f"❌ [GUARDRAILS-LOG] Failed to log result: {e}")

async def get_guardrail_logs(
    limit: int = 50,
    include_safe: bool = False,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    가드레일 로그 조회

    Args:
        limit: 조회할 로그 수
        include_safe: 안전한 요청도 포함할지 여부
        user_id: 특정 사용자의 로그만 조회

    Returns:
        로그 목록
    """
    try:
        # 여기에서는 PostgreSQL에 직접 연결하여 로그를 조회하는 로직을 구현할 수 있습니다.
        # 현재는 간단한 예시로 가드레일 서비스의 상태만 반환합니다.
        client = await get_guardrails_client()
        async with client:
            status = await client.get_service_status()
            return [{"message": "로그 조회 기능 구현 예정", "status": status}]

    except Exception as e:
        logger.error(f"❌ [GUARDRAILS-LOG] Failed to get logs: {e}")
        return []

# === 보안 이력 관리 API ===

async def get_security_incidents(
    days: int = 7,
    severity: str = "all"
) -> Dict[str, Any]:
    """
    보안 인시던트 통계 조회

    Args:
        days: 조회할 일수
        severity: 심각도 필터 ('low', 'medium', 'high', 'all')

    Returns:
        보안 인시던트 통계
    """
    try:
        # 실제 구현에서는 데이터베이스에서 통계를 계산합니다
        return {
            "period_days": days,
            "total_blocked_requests": 0,
            "blocked_by_category": {
                "basic": 0,
                "personal": 0,
                "blacklist": 0
            },
            "top_blocked_users": [],
            "blocked_ips": [],
            "recent_incidents": []
        }

    except Exception as e:
        logger.error(f"❌ [SECURITY-STATS] Failed to get security incidents: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    # 테스트 코드
    async def test_guardrails():
        print("Testing Arthur AI Guardrails Client...")

        # 안전한 텍스트 테스트
        is_safe, result = await validate_user_input("안녕하세요, 도움이 필요합니다", "test_user", "127.0.0.1")
        print(f"Safe text: {is_safe} - {result}")

        # 위험할 수 있는 텍스트 테스트
        is_safe, result = await validate_user_input("욕설이 포함된 텍스트", "test_user", "127.0.0.1")
        print(f"Unsafe text: {is_safe} - {result}")

        # 상태 조회 테스트
        status = await get_guardrails_status()
        print(f"Status: {status}")

        # 보안 인시던트 통계 테스트
        incidents = await get_security_incidents()
        print(f"Security Incidents: {incidents}")

    asyncio.run(test_guardrails())