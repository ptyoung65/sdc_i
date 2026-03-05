#!/usr/bin/env python3
"""
Arthur AI Guardrails Service with PostgreSQL Integration
3003 관리 패널의 Arthur AI Guardrails 기능을 PostgreSQL DB와 연동하여 구현
"""

import argparse
import asyncio
import logging
import uuid
import sys
import signal
import traceback
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import io
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# ----- [2026.01.29] JWT 토큰 검증을 위한 import 추가 시작 -----
import jwt
# ----- [2026.01.29] JWT 토큰 검증을 위한 import 추가 종료 -----

# Database integration
from database import db_manager, DatabaseManager

# Enhanced logging configuration
LOG_DIR = os.getenv("LOG_DIR", "/app/logs")
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'{LOG_DIR}/guardrails_8001.log')
        ]
    )
except Exception as e:
    # 파일 로깅 실패 시 콘솔만 사용
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    print(f"Warning: Could not create log file, using console only: {e}")
logger = logging.getLogger(__name__)

# Signal handler for tracking process termination
def signal_handler(signum, frame):
    signal_name = signal.Signals(signum).name
    logger.critical(f"🚨 SIGNAL RECEIVED: {signal_name} ({signum})")
    logger.critical(f"   Frame: {frame}")
    logger.critical(f"   Traceback: {traceback.format_stack()}")
    logger.critical("🛑 Process is terminating due to signal")
    sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)

logger.info("=" * 80)
logger.info("🚀 Arthur AI Guardrails Service starting")
logger.info(f"   PID: {os.getpid()}")
logger.info(f"   Python: {sys.version}")
logger.info(f"   CWD: {os.getcwd()}")
logger.info("=" * 80)

app = FastAPI(
    title="Arthur AI Guardrails Service (PostgreSQL)",
    description="PostgreSQL 연동 Arthur AI Guardrails 서비스 (3003 관리 패널 연동)",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- [2026.01.29] JWT 토큰 기반 인증으로 보안 강화 시작 -----
# Open WebUI와 동일한 JWT Secret Key 사용
WEBUI_SECRET_KEY = os.getenv("WEBUI_SECRET_KEY", "change-this-to-a-random-secret-key-for-production")
JWT_ALGORITHM = "HS256"

def verify_jwt_token(authorization: Optional[str]) -> Optional[dict]:
    """
    JWT 토큰 검증
    Open WebUI에서 발급한 JWT 토큰을 검증하고 사용자 정보 반환
    """
    if not authorization:
        return None

    try:
        # Bearer 토큰 추출
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

        # JWT 디코딩 및 검증
        decoded = jwt.decode(token, WEBUI_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        logger.info(f"✅ JWT 토큰 검증 성공: user_id={decoded.get('id')}")
        return decoded
    except jwt.ExpiredSignatureError:
        logger.warning("⚠️ JWT 토큰 만료됨")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"⚠️ JWT 토큰 검증 실패: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ JWT 검증 중 오류: {e}")
        return None

async def verify_auth(authorization: Optional[str] = Header(None)):
    """
    인증 검증 의존성
    JWT 토큰이 제공된 경우 반드시 유효해야 함
    """
    if authorization:
        jwt_user = verify_jwt_token(authorization)
        if not jwt_user:
            raise HTTPException(
                status_code=401,
                detail="유효하지 않은 인증 토큰입니다. 다시 로그인해주세요."
            )
        return jwt_user

    # 토큰이 없는 경우 - 하위 호환성을 위해 허용 (추후 제거 가능)
    logger.warning("⚠️ JWT 토큰 없이 접근 시도")
    return None
# ----- [2026.01.29] JWT 토큰 기반 인증으로 보안 강화 종료 -----

# === Data Models ===

class GuardrailKeywordModel(BaseModel):
    id: Optional[str] = None
    text: str
    category: str  # 'basic', 'personal', 'blacklist', 'whitelist'
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class GuardrailTestRequest(BaseModel):
    text: str
    categories: Optional[List[str]] = None

class ValidationResult(BaseModel):
    is_safe: bool
    blocked_keywords: List[str] = []
    blocked_categories: List[str] = []
    confidence_score: float
    action_taken: str  # 'allowed', 'blocked', 'flagged'
    details: Dict[str, Any] = {}

class GuardrailTestResponse(BaseModel):
    test_text: str
    result: ValidationResult
    summary: Dict[str, Any]

# === Arthur AI Guardrails Core Logic ===

class GuardrailEngine:
    """PostgreSQL 기반 가드레일 엔진"""

    def __init__(self):
        # 실제 패턴 매칭을 위한 간단한 키워드 리스트
        self.blocked_patterns = {
            "basic": ["욕설", "비속어", "성적", "폭력", "개인정보", "유해"],
            "personal": ["허성", "개인", "신용카드", "주민번호"],
            "blacklist": ["블랙", "금지", "차단"],
            "whitelist": []  # 화이트리스트는 허용
        }

    async def validate_text(self, text: str, categories: List[str] = None) -> ValidationResult:
        """텍스트 가드레일 검증 (PostgreSQL 기반)"""

        # 설정 조회
        settings = await db_manager.get_settings()
        sensitivity = float(settings.get("global_sensitivity", "0.7"))
        auto_block = settings.get("auto_block", "true").lower() == "true"

        blocked_keywords = []
        blocked_categories = []

        # 검사할 카테고리 결정
        if categories is None:
            categories = ["basic", "personal", "blacklist"]

        # 활성화된 키워드만 조회하여 검사
        for category in categories:
            keywords = await db_manager.get_keywords_by_category(category)

            for keyword_data in keywords:
                if keyword_data["enabled"]:
                    # 실제 등록된 키워드가 텍스트에 포함되어 있는지 검사
                    keyword_text = keyword_data["text"].lower()
                    if keyword_text in text.lower():
                        blocked_keywords.append(keyword_data["text"])
                        if category not in blocked_categories:
                            blocked_categories.append(category)

        # 결과 판정
        is_safe = len(blocked_keywords) == 0
        confidence_score = 1.0 - (len(blocked_keywords) * 0.2)  # 단순 계산
        confidence_score = max(0.0, min(1.0, confidence_score))

        action_taken = "allowed" if is_safe else ("blocked" if auto_block else "flagged")

        return ValidationResult(
            is_safe=is_safe,
            blocked_keywords=blocked_keywords,
            blocked_categories=blocked_categories,
            confidence_score=confidence_score,
            action_taken=action_taken,
            details={
                "checked_categories": categories,
                "total_keywords_checked": len(await db_manager.get_all_keywords()),
                "sensitivity": sensitivity
            }
        )

# 전역 가드레일 엔진 인스턴스
guardrail_engine = GuardrailEngine()

@app.on_event("startup")
async def startup_event():
    """서비스 시작 시 초기화"""
    try:
        await DatabaseManager.init_database()
        logger.info("🛡️ Arthur AI Guardrails Service started with PostgreSQL")

        keywords = await db_manager.get_all_keywords()
        logger.info(f"📊 Loaded {len(keywords)} guardrail keywords from database")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    keywords_count = len(await db_manager.get_all_keywords())
    settings = await db_manager.get_settings()

    return {
        "status": "Online",
        "service": "Arthur AI Guardrails (PostgreSQL)",
        "timestamp": datetime.now().isoformat(),
        "keywords_loaded": keywords_count,
        "guardrails_enabled": settings.get("guardrails_enabled", "true") == "true",
        "database": "PostgreSQL Connected"
    }

@app.get("/status")
async def get_status():
    """상태 및 통계 정보"""

    # 설정 조회
    settings = await db_manager.get_settings()

    # 카테고리별 통계
    all_keywords = await db_manager.get_all_keywords()

    # 카테고리별 분류
    categories_stats = {
        "기본 가드레일": {
            "enabled": len([k for k in all_keywords if k["category"] == "basic" and k["enabled"]]),
            "total": len([k for k in all_keywords if k["category"] == "basic"]),
            "count": 66,  # 3003 화면에 표시되는 수치
            "status": "active"
        },
        "허성 정보": {
            "enabled": len([k for k in all_keywords if k["category"] == "personal" and k["enabled"]]),
            "total": len([k for k in all_keywords if k["category"] == "personal"]),
            "count": 125,  # 3003 화면에 표시되는 수치
            "status": "active"
        },
        "블랙/화이트 리스트": {
            "enabled": len([k for k in all_keywords if k["category"] in ["blacklist", "whitelist"] and k["enabled"]]),
            "total": len([k for k in all_keywords if k["category"] in ["blacklist", "whitelist"]]),
            "count": 0,  # 3003 화면에 표시되는 수치
            "status": "blocked"
        }
    }

    return {
        "status": "Online",
        "guardrails_enabled": settings.get("guardrails_enabled", "true") == "true",
        "korean_guardrails_enabled": settings.get("korean_guardrails_enabled", "true") == "true",
        "categories": categories_stats,
        "global_settings": {
            "sensitivity": float(settings.get("global_sensitivity", "0.7")),
            "auto_block": settings.get("auto_block", "true") == "true",
            "logging_enabled": settings.get("logging_enabled", "true") == "true"
        },
        "database_info": {
            "total_keywords": len(all_keywords),
            "storage": "PostgreSQL"
        }
    }

@app.post("/test")
async def test_guardrails(request: GuardrailTestRequest, background_tasks: BackgroundTasks):
    """가드레일 테스트"""

    # 가드레일 검증 실행
    result = await guardrail_engine.validate_text(request.text, request.categories)

    # 로그 저장 (백그라운드)
    settings = await db_manager.get_settings()
    if settings.get("logging_enabled", "true") == "true":
        log_data = {
            "test_text": request.text,
            "is_safe": result.is_safe,
            "blocked_keywords": result.blocked_keywords,
            "blocked_categories": result.blocked_categories,
            "confidence_score": float(result.confidence_score),
            "action_taken": result.action_taken,
            "sensitivity": float(settings.get("global_sensitivity", "0.7"))
        }
        background_tasks.add_task(db_manager.log_test_result, log_data)

    return GuardrailTestResponse(
        test_text=request.text,
        result=result,
        summary={
            "status": "SAFE" if result.is_safe else "UNSAFE",
            "confidence": f"{result.confidence_score * 100:.1f}%",
            "action": result.action_taken,
            "blocked_items": len(result.blocked_keywords)
        }
    )


# ============================================
# 필터 유형별 검사 API
# ============================================
import re

class FilterCheckRequest(BaseModel):
    text: str
    filter_type: str  # input_filter, output_filter, pii_detection, toxicity, custom
    user_id: Optional[str] = None
    user_email: Optional[str] = None  # [2026-01-23 추가] 사용자 이메일
    model_id: Optional[str] = None  # [2026-01-21 추가] 모델 ID (예: qwen2-1.5b-instruct)
    model_name: Optional[str] = None  # [2026-01-21 추가] 모델명 (예: Qwen 2 1.5B)
    model: Optional[str] = None  # 하위 호환용 (deprecated)
    check_input: bool = True
    check_output: bool = False

class FilterCheckResponse(BaseModel):
    is_safe: bool
    action: str  # pass, warn, block
    severity: str  # low, medium, high, critical
    filter_type: str
    blocked_keywords: List[str] = []
    blocked_categories: List[str] = []
    matched_policies: List[Dict[str, Any]] = []
    detection_score: float = 0.0
    pii_detected: List[Dict[str, Any]] = []
    processing_time_ms: int = 0

# ----- 1227 룰 기반 PII 탐지 및 유효성 검증 시작 -----
# PII 정규식 패턴
PII_PATTERNS = {
    'ssn': {
        'pattern': r'\d{6}[-\s]?[1-4]\d{6}',  # 주민번호: 생년월일 6자리 + 성별구분자(1-4) + 6자리
        'name': '주민등록번호',
        'severity': 'critical',
        'action': 'block',
        'validate': True  # 체크섬 검증 필요
    },
    'phone': {
        'pattern': r'(01[0-9]|02|0[3-9][0-9])[-.\s]?\d{3,4}[-.\s]?\d{4}',
        'name': '전화번호',
        'severity': 'high',
        'action': 'warn',
        'validate': False
    },
    'email': {
        'pattern': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'name': '이메일',
        'severity': 'high',
        'action': 'warn',
        'validate': False
    },
    'credit_card': {
        'pattern': r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',
        'name': '신용카드번호',
        'severity': 'critical',
        'action': 'block',
        'validate': True  # Luhn 알고리즘 검증 필요
    },
    'bank_account': {
        'pattern': r'\d{3,4}[-\s]?\d{2,4}[-\s]?\d{4,6}',
        'name': '계좌번호',
        'severity': 'high',
        'action': 'warn',
        'validate': False
    },
    'passport': {
        'pattern': r'[A-Z]{1,2}\d{7,8}',  # 여권번호: 영문 1-2자 + 숫자 7-8자
        'name': '여권번호',
        'severity': 'critical',
        'action': 'block',
        'validate': False
    },
    'driver_license': {
        'pattern': r'\d{2}-\d{2}-\d{6}-\d{2}',  # 운전면허: 지역코드-연도-일련번호-체크
        'name': '운전면허번호',
        'severity': 'critical',
        'action': 'block',
        'validate': False
    },
    'ip_address': {
        'pattern': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # IP 주소
        'name': 'IP 주소',
        'severity': 'medium',
        'action': 'warn',
        'validate': False
    }
}


class PIIValidator:
    """PII 유효성 검증 클래스"""

    @staticmethod
    def validate_korean_ssn(ssn: str) -> bool:
        """
        주민등록번호 체크섬 검증 (한국)
        형식: YYMMDD-GNNNNNN
        - 앞 6자리: 생년월일
        - 7번째 자리: 성별/세기 구분 (1-4)
        - 마지막 자리: 체크섬
        """
        # 숫자만 추출
        digits = re.sub(r'[-\s]', '', ssn)

        if len(digits) != 13:
            return False

        try:
            # 가중치: 2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5
            weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]

            # 가중합 계산
            total = sum(int(digits[i]) * weights[i] for i in range(12))

            # 체크섬 검증: (11 - (가중합 % 11)) % 10 == 마지막 자리
            check_digit = (11 - (total % 11)) % 10

            return check_digit == int(digits[12])
        except (ValueError, IndexError):
            return False

    @staticmethod
    def validate_credit_card_luhn(card_number: str) -> bool:
        """
        신용카드번호 Luhn 알고리즘 검증
        - 모든 주요 카드사(Visa, MasterCard, 국내카드 등)에 적용
        """
        # 숫자만 추출
        digits = re.sub(r'[-\s]', '', card_number)

        if len(digits) < 13 or len(digits) > 19:
            return False

        try:
            # Luhn 알고리즘
            total = 0
            reverse_digits = digits[::-1]

            for i, digit in enumerate(reverse_digits):
                n = int(digit)
                if i % 2 == 1:  # 짝수 위치 (0-indexed에서 홀수)
                    n *= 2
                    if n > 9:
                        n -= 9
                total += n

            return total % 10 == 0
        except ValueError:
            return False

    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """전화번호 형식 검증 (한국)"""
        digits = re.sub(r'[-.\s]', '', phone)

        # 휴대폰: 010, 011, 016, 017, 018, 019
        if len(digits) == 11 and digits.startswith('01'):
            return True
        # 지역번호: 02 (서울) 또는 0XX (기타)
        if len(digits) == 10 and (digits.startswith('02') or digits[:3] in ['031', '032', '033', '041', '042', '043', '044', '051', '052', '053', '054', '055', '061', '062', '063', '064']):
            return True
        if len(digits) == 9 and digits.startswith('02'):
            return True

        return False

    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """IP 주소 유효성 검증"""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            return True
        except ValueError:
            return False


class RuleBasedGuardrail:
    """
    룰 기반 가드레일 검사 클래스
    - PII 정규식 패턴 탐지
    - 유효성 검증 (체크섬, Luhn 등)
    """

    def __init__(self):
        self.validator = PIIValidator()
        self.patterns = PII_PATTERNS

    def detect_pii(self, text: str, validate: bool = True) -> List[Dict[str, Any]]:
        """
        텍스트에서 PII 탐지

        Args:
            text: 검사할 텍스트
            validate: True면 유효성 검증 수행, False면 패턴 매칭만

        Returns:
            탐지된 PII 목록
        """
        detected = []

        for pii_type, pii_info in self.patterns.items():
            matches = re.findall(pii_info['pattern'], text, re.IGNORECASE)

            for match in matches:
                is_valid = True
                validation_method = "none"

                # 유효성 검증이 필요한 경우
                if validate and pii_info.get('validate', False):
                    if pii_type == 'ssn':
                        is_valid = self.validator.validate_korean_ssn(match)
                        validation_method = "checksum"
                    elif pii_type == 'credit_card':
                        is_valid = self.validator.validate_credit_card_luhn(match)
                        validation_method = "luhn"
                    elif pii_type == 'phone':
                        is_valid = self.validator.validate_phone_number(match)
                        validation_method = "format"
                    elif pii_type == 'ip_address':
                        is_valid = self.validator.validate_ip_address(match)
                        validation_method = "format"

                # 마스킹 처리
                if len(match) > 4:
                    masked = match[:4] + '*' * (len(match) - 4)
                else:
                    masked = '***'

                detected.append({
                    "type": pii_type,
                    "name": pii_info['name'],
                    "value": masked,
                    "original_length": len(match),
                    "severity": pii_info['severity'],
                    "action": pii_info['action'],
                    "is_valid": is_valid,
                    "validation_method": validation_method,
                    "pattern_matched": True
                })

        return detected

    def check_text(self, text: str, validate: bool = True) -> Dict[str, Any]:
        """
        텍스트 전체 검사

        Returns:
            검사 결과 딕셔너리
        """
        pii_results = self.detect_pii(text, validate)

        # 가장 높은 심각도 결정
        severity_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        max_severity = 'low'
        action = 'pass'

        valid_pii_count = 0
        for pii in pii_results:
            if pii['is_valid']:
                valid_pii_count += 1
                if severity_order.get(pii['severity'], 0) > severity_order.get(max_severity, 0):
                    max_severity = pii['severity']
                if pii['action'] == 'block':
                    action = 'block'
                elif pii['action'] == 'warn' and action != 'block':
                    action = 'warn'

        return {
            "is_safe": valid_pii_count == 0,
            "pii_detected": pii_results,
            "valid_pii_count": valid_pii_count,
            "total_pii_count": len(pii_results),
            "severity": max_severity,
            "action": action,
            "detection_score": min(1.0, valid_pii_count * 0.25)
        }


# 전역 룰 기반 가드레일 인스턴스
rule_based_guardrail = RuleBasedGuardrail()
# ----- 1227 룰 기반 PII 탐지 및 유효성 검증 종료 -----

@app.post("/api/check", response_model=FilterCheckResponse)
async def check_with_filter_type(request: FilterCheckRequest, background_tasks: BackgroundTasks):
    """
    필터 유형별 가드레일 검사
    - input_filter: 입력 텍스트 검사 (키워드 + PII)
    - output_filter: 출력 텍스트 검사 (키워드 + PII)
    - pii_detection: PII 전용 탐지
    - toxicity: 유해성 탐지 (욕설, 혐오 등)
    - custom: 사용자 정의 규칙
    """
    import time
    start_time = time.time()

    text = request.text
    filter_type = request.filter_type
    user_id = request.user_id or 'anonymous'
    user_email = request.user_email or ''  # [2026-01-23 추가] 사용자 이메일
    # [2026-01-21 수정] 모델 ID와 모델명 둘 다 추출
    model_id = request.model_id or request.model or 'unknown'
    model_name = request.model_name or model_id  # 모델명이 없으면 ID 사용

    # 결과 초기화
    is_safe = True
    action = "pass"
    severity = "low"
    blocked_keywords = []
    blocked_categories = []
    matched_policies = []
    pii_detected = []
    detection_score = 0.0

    settings = await db_manager.get_settings()
    auto_block = settings.get("auto_block", "true").lower() == "true"

    # ========================================
    # 1. PII 탐지 (pii_detection, input_filter, output_filter에서 실행)
    # ----- 1227 룰 기반 PII 탐지 및 유효성 검증 적용 -----
    # ========================================
    if filter_type in ['pii_detection', 'input_filter', 'output_filter']:
        # 룰 기반 가드레일을 사용한 PII 탐지 (유효성 검증 포함)
        pii_result = rule_based_guardrail.check_text(text, validate=True)

        for pii in pii_result['pii_detected']:
            # 유효성 검증을 통과한 PII만 처리 (패턴 매칭만 된 것은 제외 가능)
            # validate=True이므로 is_valid가 False면 실제 유효한 PII가 아님
            pii_detected.append({
                "type": pii['type'],
                "name": pii['name'],
                "value": pii['value'],
                "severity": pii['severity'],
                "action": pii['action'],
                "is_valid": pii['is_valid'],
                "validation_method": pii['validation_method']
            })

            # 유효한 PII인 경우에만 차단 처리
            if pii['is_valid']:
                blocked_keywords.append(f"{pii['name']}: {pii['value']}")

                if 'pii_detection' not in blocked_categories:
                    blocked_categories.append('pii_detection')

                matched_policies.append({
                    "id": f"pii_{pii['type']}",
                    "name": f"{pii['name']} 탐지",
                    "category": "pii_detection",
                    "severity": pii['severity'],
                    "detected": [pii['value']],
                    "validation_method": pii['validation_method'],
                    "is_valid": pii['is_valid']
                })

                # 심각도 업데이트
                if pii['severity'] == 'critical':
                    severity = 'critical'
                    action = 'block'
                    is_safe = False
                    detection_score = max(detection_score, 0.95)
                elif pii['severity'] == 'high' and severity not in ['critical']:
                    severity = 'high'
                    if action != 'block':
                        action = 'warn'
                    is_safe = False
                    detection_score = max(detection_score, 0.8)

    # ========================================
    # 2. 동적 카테고리 검사 (모든 등록된 카테고리 자동 검사)
    # ========================================
    # 카테고리별 설정 (심각도, 액션 등)
    category_config = {
        # 유해성 관련 카테고리 (높은 심각도)
        'basic': {'name': '기본 유해성', 'severity': 'high', 'score': 0.85, 'auto_block': True},
        'basic_profanity': {'name': '욕설/비속어', 'severity': 'high', 'score': 0.85, 'auto_block': True},
        'basic_sexual': {'name': '성적 콘텐츠', 'severity': 'high', 'score': 0.85, 'auto_block': True},
        'basic_violence': {'name': '폭력적 콘텐츠', 'severity': 'high', 'score': 0.85, 'auto_block': True},
        'basic_hate': {'name': '혐오 표현', 'severity': 'high', 'score': 0.85, 'auto_block': True},
        'toxicity': {'name': '유해성 탐지', 'severity': 'high', 'score': 0.85, 'auto_block': True},
        # 개인/기업 정보 보호 카테고리 (높은 심각도)
        'personal': {'name': '개인정보 보호', 'severity': 'high', 'score': 0.8, 'auto_block': True},
        'corporate': {'name': '기업정보 보호', 'severity': 'high', 'score': 0.8, 'auto_block': True},
        'security': {'name': '보안 정보', 'severity': 'high', 'score': 0.8, 'auto_block': True},
        # 커스텀 카테고리 (중간 심각도)
        'blacklist': {'name': '블랙리스트', 'severity': 'medium', 'score': 0.7, 'auto_block': False},
        'whitelist': {'name': '화이트리스트', 'severity': 'low', 'score': 0.5, 'auto_block': False},
        'custom': {'name': '사용자 정의', 'severity': 'medium', 'score': 0.7, 'auto_block': False},
    }

    # 기본 설정 (등록되지 않은 새 카테고리용)
    default_config = {'name': '정책 위반', 'severity': 'high', 'score': 0.8, 'auto_block': True}

    if filter_type in ['toxicity', 'custom', 'input_filter', 'output_filter']:
        # DB에서 모든 활성 카테고리 조회 (동적)
        all_categories = await db_manager.get_all_categories()
        logger.info(f"[Dynamic Check] 검사 대상 카테고리: {all_categories}")

        for category in all_categories:
            # whitelist 카테고리는 허용 목록이므로 검사에서 제외
            if category == 'whitelist':
                continue

            # 카테고리 설정 가져오기 (없으면 기본값 사용)
            config = category_config.get(category, default_config)

            # 해당 카테고리의 키워드 검사
            keywords = await db_manager.get_keywords_by_category(category)
            for kw_data in keywords:
                if kw_data.get('enabled', True):
                    kw_text = kw_data.get('text', '').lower()
                    if kw_text and kw_text in text.lower():
                        blocked_keywords.append(kw_data['text'])
                        if category not in blocked_categories:
                            blocked_categories.append(category)

                        matched_policies.append({
                            "id": f"{category}_{kw_data.get('id', '')}",
                            "name": config['name'],
                            "category": category,
                            "severity": config['severity'],
                            "detected": [kw_data['text']]
                        })

                        is_safe = False
                        if action != 'block':
                            action = 'block' if (auto_block and config['auto_block']) else 'warn'
                        if config['severity'] == 'high' and severity not in ['critical']:
                            severity = 'high'
                        elif config['severity'] == 'medium' and severity == 'low':
                            severity = 'medium'
                        detection_score = max(detection_score, config['score'])

    # 처리 시간 계산
    processing_time = int((time.time() - start_time) * 1000)

    # 중복 제거
    blocked_keywords = list(set(blocked_keywords))
    blocked_categories = list(set(blocked_categories))

    # 로그 저장
    if settings.get("logging_enabled", "true") == "true":
        log_data = {
            "test_text": text[:500],
            "filter_type": filter_type,
            "user_id": user_id,
            "user_email": user_email,  # [2026-01-23 추가] 사용자 이메일
            "is_safe": is_safe,
            "action": action,
            "blocked_keywords": blocked_keywords,
            "blocked_categories": blocked_categories,
            "pii_detected": len(pii_detected)
        }
        background_tasks.add_task(db_manager.log_test_result, log_data)

    # [2026-01-21 수정] 로그에 모델 ID와 모델명 추가
    logger.info(f"🛡️ 필터 검사: model_id={model_id}, model_name={model_name}, filter_type={filter_type}, action={action}, keywords={len(blocked_keywords)}, pii={len(pii_detected)}")

    return FilterCheckResponse(
        is_safe=is_safe,
        action=action,
        severity=severity,
        filter_type=filter_type,
        blocked_keywords=blocked_keywords,
        blocked_categories=blocked_categories,
        matched_policies=matched_policies,
        detection_score=detection_score,
        pii_detected=pii_detected,
        processing_time_ms=processing_time
    )


# ----- 1227 룰 기반 PII 탐지 전용 API 추가 시작 -----
class RuleBasedCheckRequest(BaseModel):
    text: str
    do_validate: bool = True  # 유효성 검증 여부 (체크섬, Luhn 등) - 'validate' 대신 사용
    include_invalid: bool = False  # 유효하지 않은 PII도 결과에 포함할지


class RuleBasedCheckResponse(BaseModel):
    is_safe: bool
    pii_detected: List[Dict[str, Any]]
    valid_pii_count: int
    total_pii_count: int
    severity: str
    action: str
    detection_score: float
    validation_summary: Dict[str, Any]


@app.post("/api/check/rule-based", response_model=RuleBasedCheckResponse)
async def check_with_rule_based(request: RuleBasedCheckRequest, background_tasks: BackgroundTasks):
    """
    룰 기반 PII 탐지 API
    - 정규식 패턴으로 PII 탐지
    - 유효성 검증 (주민번호 체크섬, 신용카드 Luhn 알고리즘)

    Args:
        text: 검사할 텍스트
        do_validate: True면 유효성 검증 수행
        include_invalid: True면 유효하지 않은 PII도 결과에 포함

    Returns:
        탐지 결과 및 유효성 검증 결과
    """
    import time
    start_time = time.time()

    # 룰 기반 검사 수행
    result = rule_based_guardrail.check_text(request.text, validate=request.do_validate)

    # 유효하지 않은 PII 필터링 (옵션)
    if not request.include_invalid:
        result['pii_detected'] = [p for p in result['pii_detected'] if p['is_valid']]

    # 유효성 검증 요약
    validation_summary = {
        "checksum_verified": sum(1 for p in result['pii_detected'] if p.get('validation_method') == 'checksum' and p.get('is_valid')),
        "luhn_verified": sum(1 for p in result['pii_detected'] if p.get('validation_method') == 'luhn' and p.get('is_valid')),
        "format_verified": sum(1 for p in result['pii_detected'] if p.get('validation_method') == 'format' and p.get('is_valid')),
        "pattern_only": sum(1 for p in result['pii_detected'] if p.get('validation_method') == 'none'),
        "processing_time_ms": int((time.time() - start_time) * 1000)
    }

    # 로그 저장
    settings = await db_manager.get_settings()
    if settings.get("logging_enabled", "true") == "true":
        log_data = {
            "test_text": request.text[:500],
            "filter_type": "rule_based",
            "is_safe": result['is_safe'],
            "action": result['action'],
            "blocked_keywords": [p['name'] for p in result['pii_detected'] if p['is_valid']],
            "blocked_categories": ['pii_detection'] if result['valid_pii_count'] > 0 else [],
            "pii_detected": result['valid_pii_count']
        }
        background_tasks.add_task(db_manager.log_test_result, log_data)

    logger.info(f"🛡️ 룰 기반 검사: validate={request.do_validate}, pii={result['valid_pii_count']}/{result['total_pii_count']}, action={result['action']}")

    return RuleBasedCheckResponse(
        is_safe=result['is_safe'],
        pii_detected=result['pii_detected'],
        valid_pii_count=result['valid_pii_count'],
        total_pii_count=result['total_pii_count'],
        severity=result['severity'],
        action=result['action'],
        detection_score=result['detection_score'],
        validation_summary=validation_summary
    )


@app.get("/api/pii-patterns")
async def get_pii_patterns():
    """
    등록된 PII 패턴 목록 조회
    - 탐지 가능한 PII 유형과 설정 반환
    """
    patterns_info = []
    for pii_type, pii_info in PII_PATTERNS.items():
        patterns_info.append({
            "type": pii_type,
            "name": pii_info['name'],
            "severity": pii_info['severity'],
            "action": pii_info['action'],
            "has_validation": pii_info.get('validate', False),
            "validation_method": "checksum" if pii_type == 'ssn' else ("luhn" if pii_type == 'credit_card' else "none")
        })

    return {
        "patterns": patterns_info,
        "total": len(patterns_info),
        "validation_methods": {
            "checksum": "주민등록번호 체크섬 검증 (한국)",
            "luhn": "신용카드 Luhn 알고리즘 검증",
            "format": "형식 검증 (전화번호, IP 등)"
        }
    }
# ----- 1227 룰 기반 PII 탐지 전용 API 추가 종료 -----


@app.get("/keywords")
async def get_keywords(user: Optional[dict] = Depends(verify_auth)):  # [2026.01.29] JWT 인증 추가
    """키워드 목록 조회"""
    all_keywords = await db_manager.get_all_keywords()

    # 카테고리별 분류 (basic_profanity, basic_sexual 등을 basic으로 그룹화)
    by_category = {
        "basic": [k for k in all_keywords if k["category"].startswith("basic_") or k["category"] == "basic"],
        "personal": [k for k in all_keywords if k["category"] == "personal"],
        "blacklist": [k for k in all_keywords if k["category"] == "blacklist"],
        "whitelist": [k for k in all_keywords if k["category"] == "whitelist"]
    }

    return {
        "keywords": all_keywords,
        "total": len(all_keywords),
        "by_category": by_category,
        "source": "PostgreSQL Database"
    }

@app.post("/keywords")
async def add_keyword(keyword: GuardrailKeywordModel, user: Optional[dict] = Depends(verify_auth)):  # [2026.01.29] JWT 인증 추가
    """새 키워드 추가"""

    # ID가 없으면 자동 생성
    if not keyword.id:
        keyword.id = str(uuid.uuid4())

    keyword_data = {
        "id": keyword.id,
        "text": keyword.text,
        "category": keyword.category,
        "enabled": keyword.enabled
    }

    try:
        result = await db_manager.add_keyword(keyword_data)
        logger.info(f"➕ Added keyword: {keyword.text} (category: {keyword.category})")
        return result
    except Exception as e:
        logger.error(f"❌ Failed to add keyword: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add keyword: {str(e)}")

@app.put("/keywords/{keyword_id}")
async def update_keyword(keyword_id: str, keyword: GuardrailKeywordModel, user: Optional[dict] = Depends(verify_auth)):  # [2026.01.29] JWT 인증 추가
    """키워드 업데이트"""

    keyword_data = {
        "text": keyword.text,
        "category": keyword.category,
        "enabled": keyword.enabled
    }

    result = await db_manager.update_keyword(keyword_id, keyword_data)

    if not result:
        raise HTTPException(status_code=404, detail="Keyword not found")

    logger.info(f"🔄 Updated keyword: {keyword.text} (category: {keyword.category})")
    return result

@app.delete("/keywords/{keyword_id}")
async def delete_keyword(keyword_id: str, user: Optional[dict] = Depends(verify_auth)):  # [2026.01.29] JWT 인증 추가
    """키워드 삭제"""

    success = await db_manager.delete_keyword(keyword_id)

    if not success:
        raise HTTPException(status_code=404, detail="Keyword not found")

    logger.info(f"🗑️ Deleted keyword: {keyword_id}")
    return {"message": "Keyword deleted successfully"}

@app.get("/settings")
async def get_settings(user: Optional[dict] = Depends(verify_auth)):  # [2026.01.29] JWT 인증 추가
    """설정 조회"""
    settings = await db_manager.get_settings()
    return {
        "settings": settings,
        "source": "PostgreSQL Database"
    }

@app.put("/settings/{key}")
async def update_setting(key: str, value: str, user: Optional[dict] = Depends(verify_auth)):  # [2026.01.29] JWT 인증 추가
    """설정 업데이트"""
    success = await db_manager.update_setting(key, value)

    if success:
        logger.info(f"⚙️ Updated setting: {key} = {value}")
        return {"message": f"Setting {key} updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update setting")

@app.get("/logs")
async def get_guardrail_logs(
    limit: int = 50,
    offset: int = 0,
    filter_safe: Optional[bool] = None,
    search: Optional[str] = None,
    user: Optional[dict] = Depends(verify_auth)  # [2026.01.29] JWT 인증 추가
):
    """가드레일 로그 조회"""
    try:
        logs = await db_manager.get_logs(
            limit=limit,
            offset=offset,
            filter_safe=filter_safe,
            search=search
        )

        total_count = await db_manager.get_logs_count(
            filter_safe=filter_safe,
            search=search
        )

        return {
            "logs": logs,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
    except Exception as e:
        logger.error(f"❌ Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

@app.get("/logs/stats")
async def get_logs_statistics():
    """로그 통계 조회"""
    try:
        stats = await db_manager.get_log_statistics()
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to get log statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

# === Excel Import/Export Endpoints ===

@app.get("/keywords/export/excel")
async def export_keywords_to_excel():
    """키워드를 엑셀 파일로 내보내기"""
    try:
        # 모든 키워드 조회
        all_keywords = await db_manager.get_all_keywords()

        # 엑셀 워크북 생성
        wb = Workbook()
        ws = wb.active
        ws.title = "가드레일 키워드"

        # 스타일 정의
        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # 헤더 작성
        headers = ['ID', '키워드 텍스트', '카테고리', '활성화', '생성일', '수정일']
        ws.append(headers)

        # 헤더 스타일 적용
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border

        # 데이터 작성
        for kw in all_keywords:
            ws.append([
                kw.get('id', ''),
                kw.get('text', ''),
                kw.get('category', ''),
                'TRUE' if kw.get('enabled', False) else 'FALSE',
                kw.get('created_at', ''),
                kw.get('updated_at', '')
            ])

        # 모든 셀에 테두리 적용
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=6):
            for cell in row:
                cell.border = border
                if cell.column == 4:  # 활성화 열
                    cell.alignment = Alignment(horizontal="center")

        # 열 너비 자동 조정
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 12
        ws.column_dimensions['E'].width = 20
        ws.column_dimensions['F'].width = 20

        # 가이드 시트 추가
        ws_guide = wb.create_sheet("업로드 가이드")
        guide_text = [
            ["가드레일 키워드 엑셀 업로드 가이드"],
            [""],
            ["1. 파일 형식: .xlsx"],
            ["2. 필수 열: ID, 키워드 텍스트, 카테고리, 활성화"],
            ["3. 카테고리 종류:"],
            ["   - basic_profanity: 욕설/비속어"],
            ["   - basic_sexual: 성적 콘텐츠"],
            ["   - basic_violence: 폭력적 콘텐츠"],
            ["   - basic_pii: 개인정보"],
            ["   - basic_harmful: 유해한 지시사항"],
            ["   - personal: 허성정보 (회사 정보)"],
            ["   - blacklist: 블랙리스트"],
            ["   - whitelist: 화이트리스트"],
            [""],
            ["4. 활성화 값: TRUE 또는 FALSE"],
            ["5. ID는 중복되지 않아야 합니다"],
        ]
        for row_data in guide_text:
            ws_guide.append(row_data)
        ws_guide['A1'].font = Font(bold=True, size=14, color="4472C4")
        ws_guide.column_dimensions['A'].width = 100

        # 메모리에 엑셀 파일 저장
        excel_file = io.BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        # 파일명 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"guardrail_keywords_{timestamp}.xlsx"

        logger.info(f"📥 Exported {len(all_keywords)} keywords to Excel")

        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logger.error(f"❌ Failed to export keywords to Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export: {str(e)}")

@app.post("/keywords/import/excel")
async def import_keywords_from_excel(file: UploadFile = File(...)):
    """엑셀 파일에서 키워드 가져오기"""
    try:
        # 파일 확장자 확인
        if not file.filename.endswith('.xlsx'):
            raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

        # 파일 읽기
        contents = await file.read()
        excel_file = io.BytesIO(contents)

        # 엑셀 파일 파싱
        wb = load_workbook(excel_file)

        if "가드레일 키워드" not in wb.sheetnames:
            raise HTTPException(status_code=400, detail="Sheet '가드레일 키워드' not found")

        ws = wb["가드레일 키워드"]

        # 헤더 확인
        headers = [cell.value for cell in ws[1]]
        if headers[:4] != ['ID', '키워드 텍스트', '카테고리', '활성화']:
            raise HTTPException(status_code=400, detail="Invalid header format")

        # 키워드 파싱
        keywords_to_add = []
        keywords_to_update = []
        errors = []

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row[0]:  # ID가 없으면 건너뛰기
                continue

            try:
                keyword_id = str(row[0]).strip()
                text = str(row[1]).strip() if row[1] else ''
                category = str(row[2]).strip() if row[2] else ''
                enabled_str = str(row[3]).strip().upper() if row[3] else 'TRUE'
                enabled = enabled_str == 'TRUE'

                if not text or not category:
                    errors.append(f"Row {row_idx}: Missing text or category")
                    continue

                # 카테고리 검증
                valid_categories = [
                    'basic_profanity', 'basic_sexual', 'basic_violence',
                    'basic_pii', 'basic_harmful', 'personal',
                    'blacklist', 'whitelist'
                ]
                if category not in valid_categories:
                    errors.append(f"Row {row_idx}: Invalid category '{category}'")
                    continue

                keyword_data = {
                    'id': keyword_id,
                    'text': text,
                    'category': category,
                    'enabled': enabled
                }

                # 기존 키워드 존재 여부 확인
                existing = await db_manager.get_keyword_by_id(keyword_id)
                if existing:
                    keywords_to_update.append(keyword_data)
                else:
                    keywords_to_add.append(keyword_data)

            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)}")

        # 데이터베이스에 저장
        added_count = 0
        updated_count = 0

        for kw in keywords_to_add:
            await db_manager.add_keyword(kw)
            added_count += 1

        for kw in keywords_to_update:
            await db_manager.update_keyword(kw['id'], kw)
            updated_count += 1

        logger.info(f"📤 Imported keywords: {added_count} added, {updated_count} updated")

        return {
            "success": True,
            "added": added_count,
            "updated": updated_count,
            "errors": errors,
            "total_processed": added_count + updated_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to import keywords from Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import: {str(e)}")

# ============================================
# 대시보드 API
# ============================================

@app.get("/api/guardrails/dashboard")
async def get_guardrails_dashboard(range: Optional[str] = '7d'):
    """
    가드레일 대시보드 통계
    - 총 정책 수, 활성화된 정책 수
    - 총 검사 수, 차단된 요청 수
    - 정책별 통계, 최근 차단 로그
    """
    try:
        from database import execute_raw_query

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

        # 정책 통계 조회
        policy_query = """
            SELECT
                COUNT(*) as total_policies,
                COUNT(*) FILTER (WHERE enabled = true) as active_policies
            FROM guardrail_policies
        """
        try:
            policy_results = await execute_raw_query(policy_query)
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
                COUNT(*) FILTER (WHERE check_result = 'block') as blocked_count,
                COUNT(*) FILTER (WHERE check_result = 'pass') as passed_count,
                COUNT(*) FILTER (WHERE check_result = 'warn') as warning_count
            FROM guardrail_check_logs
            WHERE created_at >= NOW() - INTERVAL '{days} days'
        """
        try:
            log_results = await execute_raw_query(log_query)
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

        # 정책별 통계
        # 카테고리별 통계 쿼리 (정책별이 아닌 카테고리별로 집계)
        policy_stats_query = f"""
            WITH category_mapping AS (
                SELECT 'company' as category, 'corporate' as log_category
                UNION ALL SELECT 'privacy', 'personal'
                UNION ALL SELECT 'privacy', 'pii_detection'
                UNION ALL SELECT 'content', 'toxicity'
                UNION ALL SELECT 'security', 'security'
                UNION ALL SELECT 'compliance', 'compliance'
            ),
            category_logs AS (
                SELECT 
                    COALESCE(cm.category, cat.value) as category,
                    l.id,
                    l.check_result
                FROM guardrail_check_logs l,
                LATERAL jsonb_array_elements_text(l.detected_categories) as cat(value)
                LEFT JOIN category_mapping cm ON cm.log_category = cat.value
                WHERE l.created_at >= NOW() - INTERVAL '{days} days'
            )
            SELECT
                p.category as id,
                CASE p.category
                    WHEN 'company' THEN '회사정보'
                    WHEN 'compliance' THEN '규정준수'
                    WHEN 'content' THEN '콘텐츠'
                    WHEN 'privacy' THEN '개인정보'
                    WHEN 'security' THEN '보안'
                    ELSE p.category
                END as policy_name,
                p.category,
                'high' as severity,
                true as is_active,
                COUNT(DISTINCT cl.id) as total_checks,
                COUNT(DISTINCT cl.id) FILTER (WHERE cl.check_result = 'block') as blocked_count,
                COUNT(DISTINCT cl.id) FILTER (WHERE cl.check_result = 'pass') as passed_count,
                COUNT(DISTINCT cl.id) FILTER (WHERE cl.check_result = 'warn') as warned_count,
                ROUND(
                    COUNT(DISTINCT cl.id) FILTER (WHERE cl.check_result = 'block')::numeric /
                    NULLIF(COUNT(DISTINCT cl.id), 0) * 100, 1
                ) as block_rate
            FROM (SELECT DISTINCT category FROM guardrail_policies) p
            LEFT JOIN category_logs cl ON cl.category = p.category
            GROUP BY p.category
            ORDER BY blocked_count DESC
        """
        try:
            policy_stats = await execute_raw_query(policy_stats_query)
        except Exception as e:
            logger.error(f"정책별 통계 조회 오류: {e}")
            policy_stats = []

        # 최근 차단 로그
        recent_logs_query = f"""
            SELECT
                l.id,
                l.request_id,
                l.user_id,
                l.check_result,
                l.original_text,
                l.detection_score,
                l.detected_keywords,
                l.detected_categories,
                l.created_at,
                p.name as policy_name,
                p.severity
            FROM guardrail_check_logs l
            LEFT JOIN guardrail_policies p ON l.policy_id = p.id
            WHERE l.check_result = 'block'
            AND l.created_at >= NOW() - INTERVAL '{days} days'
            ORDER BY l.created_at DESC
            LIMIT 10
        """
        try:
            recent_logs = await execute_raw_query(recent_logs_query)
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
                "category": p.get('category', ''),
                "severity": p.get('severity', 'medium'),
                "isActive": p.get('is_active', False),
                "totalChecks": p.get('total_checks', 0) or 0,
                "blockedCount": p.get('blocked_count', 0) or 0,
                "passedCount": p.get('passed_count', 0) or 0,
                "warnedCount": p.get('warned_count', 0) or 0,
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
                "severity": l.get('severity', 'medium'),
                "detectedCategories": l.get('detected_categories', []) or [],
                "detectedKeywords": l.get('detected_keywords', []) or []
            } for l in (recent_logs or [])]
        }

    except Exception as e:
        logger.error(f"❌ 가드레일 대시보드 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 정책 관리 API
# ============================================

@app.get("/api/guardrails/policies")
async def get_guardrails_policies(
    severity: Optional[str] = None,
    is_active: Optional[bool] = None,
    category: Optional[str] = None,
    filter_type: Optional[str] = None,
    action_type: Optional[str] = None
):
    """가드레일 정책 목록 조회"""
    try:
        from database import execute_raw_query

        conditions = []
        if severity and severity != 'all':
            conditions.append(f"p.severity = '{severity}'")
        if is_active is not None:
            conditions.append(f"p.enabled = {is_active}")
        if category and category != 'all':
            conditions.append(f"p.category = '{category}'")
        if filter_type and filter_type != 'all':
            conditions.append(f"p.filter_type = '{filter_type}'")
        if action_type and action_type != 'all':
            conditions.append(f"p.action_type = '{action_type}'")

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # [2026-01-23 수정] 카테고리 매핑으로 통계 계산
        # 로그의 detected_categories (corporate, personal, basic 등)와
        # 정책의 category (company, privacy, content 등) 매핑
        query = f"""
            SELECT
                p.id,
                p.name,
                p.description,
                p.category,
                p.filter_type,
                p.severity,
                p.action_type,
                p.enabled,
                p.rules,
                p.created_at,
                p.updated_at,
                COUNT(l.id) as total_checks,
                COUNT(l.id) FILTER (WHERE l.check_result = 'block') as blocked_count,
                COUNT(l.id) FILTER (WHERE l.check_result = 'warn') as warned_count
            FROM guardrail_policies p
            LEFT JOIN guardrail_check_logs l ON (
                -- 직접 policy_id 매칭
                p.id = l.policy_id
                -- 또는 카테고리 매핑으로 매칭
                OR (p.category = 'company' AND l.detected_categories::text LIKE '%corporate%')
                OR (p.category = 'privacy' AND (l.detected_categories::text LIKE '%personal%' OR l.detected_categories::text LIKE '%privacy%'))
                OR (p.category = 'content' AND (l.detected_categories::text LIKE '%basic%' OR l.detected_categories::text LIKE '%toxicity%'))
                OR (p.category = 'compliance' AND l.detected_categories::text LIKE '%security%')
            )
            {where_clause}
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """

        results = await execute_raw_query(query)

        policies = []
        for p in (results or []):
            rules = p.get('rules', {}) or {}
            keywords = []
            patterns = []

            # rules가 딕셔너리인 경우 (DB 저장 형식: {"keywords": [...], "patterns": [...]})
            if isinstance(rules, dict):
                keywords = rules.get('keywords', []) or []
                patterns = rules.get('patterns', []) or []
            # rules가 리스트인 경우 (이전 형식)
            elif isinstance(rules, list):
                for rule in rules:
                    if isinstance(rule, dict):
                        pattern = rule.get('pattern', '')
                        if pattern:
                            if rule.get('type') == 'keyword':
                                keywords.extend(pattern.split('|'))
                            else:
                                patterns.append(pattern)

            policies.append({
                "id": p.get('id'),
                "name": p.get('name', ''),
                "description": p.get('description', ''),
                "category": p.get('category', 'content'),
                "filterType": p.get('filter_type', 'input_filter'),
                "severity": p.get('severity', 'medium'),
                "actionType": p.get('action_type', 'block'),
                "isActive": p.get('enabled', False),
                "keywords": keywords,
                "patterns": patterns,
                "createdAt": p.get('created_at').isoformat() if p.get('created_at') else '',
                "updatedAt": p.get('updated_at').isoformat() if p.get('updated_at') else '',
                "totalChecks": p.get('total_checks', 0) or 0,
                "blockedCount": p.get('blocked_count', 0) or 0,
                "warnedCount": p.get('warned_count', 0) or 0  # [2026-01-23 추가]
            })

        return {"data": policies, "total": len(policies)}

    except Exception as e:
        logger.error(f"❌ 가드레일 정책 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/policies/{policy_id}")
async def get_guardrails_policy(policy_id: str):
    """특정 가드레일 정책 조회"""
    try:
        from database import execute_raw_query

        query = """
            SELECT id, name, description, category, severity, enabled, rules, created_at, updated_at
            FROM guardrail_policies
            WHERE id = %s
        """
        results = await execute_raw_query(query, (policy_id,))

        if not results:
            raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다")

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


class PolicyCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ''
    category: str = 'content'
    filterType: str = 'input_filter'
    severity: str = 'medium'
    actionType: str = 'block'
    enabled: bool = True
    keywords: List[str] = []
    patterns: List[str] = []


@app.post("/api/guardrails/policies")
async def create_guardrails_policy(policy: PolicyCreateRequest):
    """새 가드레일 정책 생성"""
    try:
        from database import execute_raw_query
        import uuid

        policy_id = str(uuid.uuid4())[:8]

        # rules 구성
        rules = []
        if policy.keywords:
            rules.append({
                "type": "keyword",
                "pattern": "|".join(policy.keywords),
                "action": policy.actionType
            })
        for pattern in policy.patterns:
            rules.append({
                "type": "regex",
                "pattern": pattern,
                "action": policy.actionType
            })

        import json
        query = """
            INSERT INTO guardrail_policies (id, name, description, category, filter_type, severity, action_type, enabled, rules, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id, name, description, category, filter_type, severity, action_type, enabled, created_at
        """

        result = await execute_raw_query(
            query,
            (policy_id, policy.name, policy.description, policy.category,
             policy.filterType, policy.severity, policy.actionType, policy.enabled, json.dumps(rules))
        )

        if result:
            logger.info(f"➕ 정책 생성: {policy.name} (ID: {policy_id})")
            return {
                "id": policy_id,
                "name": policy.name,
                "description": policy.description,
                "category": policy.category,
                "filterType": policy.filterType,
                "severity": policy.severity,
                "actionType": policy.actionType,
                "enabled": policy.enabled,
                "message": "정책이 생성되었습니다"
            }
        else:
            raise HTTPException(status_code=500, detail="정책 생성 실패")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 정책 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/guardrails/policies/{policy_id}")
async def update_guardrails_policy(policy_id: str, policy: PolicyCreateRequest):
    """가드레일 정책 수정"""
    try:
        from database import execute_raw_query
        import json

        # rules 구성
        rules = []
        if policy.keywords:
            rules.append({
                "type": "keyword",
                "pattern": "|".join(policy.keywords),
                "action": policy.actionType
            })
        for pattern in policy.patterns:
            rules.append({
                "type": "regex",
                "pattern": pattern,
                "action": policy.actionType
            })

        query = """
            UPDATE guardrail_policies
            SET name = %s, description = %s, category = %s, filter_type = %s,
                severity = %s, action_type = %s, enabled = %s, rules = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id
        """

        result = await execute_raw_query(
            query,
            (policy.name, policy.description, policy.category, policy.filterType,
             policy.severity, policy.actionType, policy.enabled, json.dumps(rules), policy_id)
        )

        if result:
            logger.info(f"🔄 정책 수정: {policy.name} (ID: {policy_id})")
            return {"id": policy_id, "message": "정책이 수정되었습니다"}
        else:
            raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 정책 수정 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# [2026-01-21] 정책 삭제 API - 프론트엔드 일괄삭제 기능에서 사용
@app.delete("/api/guardrails/policies/{policy_id}")
async def delete_guardrails_policy(policy_id: str):
    """가드레일 정책 삭제 (일괄삭제 시 개별 호출)"""
    try:
        from database import execute_raw_query

        query = "DELETE FROM guardrail_policies WHERE id = %s RETURNING id"
        result = await execute_raw_query(query, (policy_id,))

        if result:
            logger.info(f"🗑️ 정책 삭제: {policy_id}")
            return {"message": "정책이 삭제되었습니다"}
        else:
            raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 정책 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# [2026-01-21] 정책 토글 API - 개별 정책 활성화/비활성화 토글
@app.put("/api/guardrails/policies/{policy_id}/toggle")
async def toggle_guardrails_policy(policy_id: str):
    """가드레일 정책 활성화/비활성화 토글"""
    try:
        from database import execute_raw_query

        query = """
            UPDATE guardrail_policies
            SET enabled = NOT enabled, updated_at = NOW()
            WHERE id = %s
            RETURNING id, enabled
        """
        result = await execute_raw_query(query, (policy_id,))

        if result:
            new_status = result[0].get('enabled', False)
            logger.info(f"🔄 정책 토글: {policy_id} -> {'활성' if new_status else '비활성'}")
            return {"id": policy_id, "enabled": new_status, "message": f"정책이 {'활성화' if new_status else '비활성화'}되었습니다"}
        else:
            raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 정책 토글 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# [2026-01-21 추가] 정책 활성화/비활성화 설정 요청 모델
class PolicySetActiveRequest(BaseModel):
    isActive: bool = Field(..., description="활성화 여부")


@app.put("/api/guardrails/policies/{policy_id}/set-active")
async def set_policy_active(policy_id: str, request: PolicySetActiveRequest):
    """가드레일 정책 활성화/비활성화 설정 (특정 값으로 설정)"""
    try:
        from database import execute_raw_query

        query = """
            UPDATE guardrail_policies
            SET enabled = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, enabled
        """
        result = await execute_raw_query(query, (request.isActive, policy_id))

        if result:
            new_status = result[0].get('enabled', False)
            logger.info(f"🔄 정책 활성화 설정: {policy_id} -> {'활성' if new_status else '비활성'}")
            return {"id": policy_id, "enabled": new_status, "isActive": new_status, "message": f"정책이 {'활성화' if new_status else '비활성화'}되었습니다"}
        else:
            raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 정책 활성화 설정 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 기준 데이터 관리 API
# ============================================

@app.get("/api/guardrails/master/policy-types")
async def get_policy_types():
    """정책 유형 목록 조회"""
    try:
        from database import execute_raw_query

        query = """
            SELECT code, id, name, description, is_active, created_at
            FROM guardrail_policy_types
            ORDER BY created_at
        """
        results = await execute_raw_query(query)

        return {
            "data": [{
                "code": r.get('code'),
                "id": r.get('id'),
                "name": r.get('name'),
                "description": r.get('description'),
                "isActive": r.get('is_active', True),
                "createdAt": r.get('created_at').isoformat() if r.get('created_at') else ''
            } for r in (results or [])],
            "total": len(results or [])
        }
    except Exception as e:
        logger.error(f"❌ 정책 유형 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PolicyTypeRequest(BaseModel):
    code: Optional[str] = None  # code가 없으면 자동 생성
    name: str
    description: Optional[str] = ''


@app.post("/api/guardrails/master/policy-types")
async def create_policy_type(policy_type: PolicyTypeRequest):
    """정책 유형 추가"""
    try:
        from database import execute_raw_query

        # code가 없으면 자동 생성 (PT + 3자리)
        code = policy_type.code
        if not code:
            # 기존 PT 코드 중 최대값 조회
            max_query = "SELECT code FROM guardrail_policy_types WHERE code LIKE 'PT%' ORDER BY code DESC LIMIT 1"
            max_result = await execute_raw_query(max_query)
            if max_result and max_result[0].get('code'):
                max_code = max_result[0]['code']
                try:
                    max_num = int(max_code[2:])
                    code = f"PT{max_num + 1:03d}"
                except:
                    code = "PT001"
            else:
                code = "PT001"

        query = """
            INSERT INTO guardrail_policy_types (code, name, description, created_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
            RETURNING code
        """
        result = await execute_raw_query(query, (code, policy_type.name, policy_type.description))

        if result:
            return {"code": code, "message": "정책 유형이 추가되었습니다"}
        else:
            raise HTTPException(status_code=500, detail="정책 유형 추가 실패")

    except Exception as e:
        logger.error(f"❌ 정책 유형 추가 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/master/policy-types/{code}")
async def delete_policy_type(code: str):
    """정책 유형 삭제 (비활성화)"""
    try:
        from database import execute_raw_query

        query = "UPDATE guardrail_policy_types SET is_active = false WHERE code = %s RETURNING code"
        result = await execute_raw_query(query, (code,))

        if result:
            return {"message": "정책 유형이 비활성화되었습니다"}
        else:
            raise HTTPException(status_code=404, detail="정책 유형을 찾을 수 없습니다")

    except Exception as e:
        logger.error(f"❌ 정책 유형 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PolicyTypeUpdateRequest(BaseModel):
    name: str
    description: Optional[str] = ''


@app.put("/api/guardrails/master/policy-types/{code}")
async def update_policy_type(code: str, policy_type: PolicyTypeUpdateRequest):
    """정책 유형 수정"""
    try:
        from database import execute_raw_query

        query = """
            UPDATE guardrail_policy_types
            SET name = %s, description = %s
            WHERE code = %s
            RETURNING code
        """
        result = await execute_raw_query(query, (policy_type.name, policy_type.description, code))

        if result:
            return {"code": code, "message": "정책 유형이 수정되었습니다"}
        else:
            raise HTTPException(status_code=404, detail="정책 유형을 찾을 수 없습니다")

    except Exception as e:
        logger.error(f"❌ 정책 유형 수정 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/master/policy-types/{code}/permanent")
async def permanent_delete_policy_type(code: str):
    """정책 유형 완전 삭제"""
    try:
        from database import execute_raw_query

        query = "DELETE FROM guardrail_policy_types WHERE code = %s RETURNING code"
        result = await execute_raw_query(query, (code,))

        if result:
            return {"message": "정책 유형이 완전히 삭제되었습니다"}
        else:
            raise HTTPException(status_code=404, detail="정책 유형을 찾을 수 없습니다")

    except Exception as e:
        logger.error(f"❌ 정책 유형 완전 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/master/filter-types")
async def get_filter_types():
    """필터 유형 목록 조회"""
    try:
        from database import execute_raw_query

        query = """
            SELECT code, id, name, description, is_active, created_at
            FROM guardrail_filter_types
            ORDER BY created_at
        """
        results = await execute_raw_query(query)

        return {
            "data": [{
                "code": r.get('code'),
                "id": r.get('id'),
                "name": r.get('name'),
                "description": r.get('description'),
                "isActive": r.get('is_active', True),
                "createdAt": r.get('created_at').isoformat() if r.get('created_at') else ''
            } for r in (results or [])],
            "total": len(results or [])
        }
    except Exception as e:
        logger.error(f"❌ 필터 유형 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class FilterTypeRequest(BaseModel):
    code: Optional[str] = None  # code가 없으면 자동 생성
    name: str
    description: Optional[str] = ''


@app.post("/api/guardrails/master/filter-types")
async def create_filter_type(filter_type: FilterTypeRequest):
    """필터 유형 추가"""
    try:
        from database import execute_raw_query

        # code가 없으면 자동 생성 (FT + 3자리)
        code = filter_type.code
        if not code:
            # 기존 FT 코드 중 최대값 조회
            max_query = "SELECT code FROM guardrail_filter_types WHERE code LIKE 'FT%' ORDER BY code DESC LIMIT 1"
            max_result = await execute_raw_query(max_query)
            if max_result and max_result[0].get('code'):
                max_code = max_result[0]['code']
                try:
                    max_num = int(max_code[2:])
                    code = f"FT{max_num + 1:03d}"
                except:
                    code = "FT001"
            else:
                code = "FT001"

        query = """
            INSERT INTO guardrail_filter_types (code, name, description, created_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
            RETURNING code
        """
        result = await execute_raw_query(query, (code, filter_type.name, filter_type.description))

        if result:
            return {"code": code, "message": "필터 유형이 추가되었습니다"}
        else:
            raise HTTPException(status_code=500, detail="필터 유형 추가 실패")

    except Exception as e:
        logger.error(f"❌ 필터 유형 추가 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/master/filter-types/{code}")
async def delete_filter_type(code: str):
    """필터 유형 삭제 (비활성화)"""
    try:
        from database import execute_raw_query

        query = "UPDATE guardrail_filter_types SET is_active = false WHERE code = %s RETURNING code"
        result = await execute_raw_query(query, (code,))

        if result:
            return {"message": "필터 유형이 비활성화되었습니다"}
        else:
            raise HTTPException(status_code=404, detail="필터 유형을 찾을 수 없습니다")

    except Exception as e:
        logger.error(f"❌ 필터 유형 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class FilterTypeUpdateRequest(BaseModel):
    name: str
    description: Optional[str] = ''


@app.put("/api/guardrails/master/filter-types/{code}")
async def update_filter_type(code: str, filter_type: FilterTypeUpdateRequest):
    """필터 유형 수정"""
    try:
        from database import execute_raw_query

        query = """
            UPDATE guardrail_filter_types
            SET name = %s, description = %s
            WHERE code = %s
            RETURNING code
        """
        result = await execute_raw_query(query, (filter_type.name, filter_type.description, code))

        if result:
            return {"code": code, "message": "필터 유형이 수정되었습니다"}
        else:
            raise HTTPException(status_code=404, detail="필터 유형을 찾을 수 없습니다")

    except Exception as e:
        logger.error(f"❌ 필터 유형 수정 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/guardrails/master/filter-types/{code}/permanent")
async def permanent_delete_filter_type(code: str):
    """필터 유형 완전 삭제"""
    try:
        from database import execute_raw_query

        query = "DELETE FROM guardrail_filter_types WHERE code = %s RETURNING code"
        result = await execute_raw_query(query, (code,))

        if result:
            return {"message": "필터 유형이 완전히 삭제되었습니다"}
        else:
            raise HTTPException(status_code=404, detail="필터 유형을 찾을 수 없습니다")

    except Exception as e:
        logger.error(f"❌ 필터 유형 완전 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/master/severity-levels")
async def get_severity_levels():
    """심각도 목록 조회"""
    try:
        from database import execute_raw_query

        query = """
            SELECT code, id, name, description, color, priority, is_active
            FROM guardrail_severity_levels
            ORDER BY priority
        """
        results = await execute_raw_query(query)

        return {
            "data": [{
                "code": r.get('code'),
                "id": r.get('id'),
                "name": r.get('name'),
                "description": r.get('description'),
                "color": r.get('color'),
                "priority": r.get('priority'),
                "isActive": r.get('is_active', True)
            } for r in (results or [])],
            "total": len(results or [])
        }
    except Exception as e:
        logger.error(f"❌ 심각도 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/master/action-types")
async def get_action_types():
    """액션 유형 목록 조회"""
    try:
        from database import execute_raw_query

        query = """
            SELECT code, id, name, description, is_active
            FROM guardrail_action_types
            ORDER BY created_at
        """
        results = await execute_raw_query(query)

        return {
            "data": [{
                "code": r.get('code'),
                "id": r.get('id'),
                "name": r.get('name'),
                "description": r.get('description'),
                "isActive": r.get('is_active', True)
            } for r in (results or [])],
            "total": len(results or [])
        }
    except Exception as e:
        logger.error(f"❌ 액션 유형 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/master/all")
async def get_all_master_data():
    """모든 기준 데이터 조회"""
    # ----- 1227 기본 데이터 반환 수정 시작 -----
    # 테이블이 없거나 비어있으면 기본 데이터 반환
    default_policy_types = [
        {"code": "basic", "id": "basic", "name": "기본 금지어"},
        {"code": "personal", "id": "personal", "name": "개인정보"},
        {"code": "corporate", "id": "corporate", "name": "회사정보"},
        {"code": "blacklist", "id": "blacklist", "name": "블랙리스트"},
        {"code": "whitelist", "id": "whitelist", "name": "화이트리스트"}
    ]
    default_filter_types = [
        {"code": "FT001", "id": "input_filter", "name": "입력 필터"},
        {"code": "FT002", "id": "output_filter", "name": "출력 필터"},
        {"code": "FT003", "id": "pii_detection", "name": "PII 탐지"},
        {"code": "FT004", "id": "toxicity", "name": "유해성 탐지"},
        {"code": "FT005", "id": "custom", "name": "커스텀"}
    ]
    default_severity_levels = [
        {"code": "SV001", "id": "critical", "name": "Critical (치명적)"},
        {"code": "SV002", "id": "high", "name": "High (높음)"},
        {"code": "SV003", "id": "medium", "name": "Medium (중간)"},
        {"code": "SV004", "id": "low", "name": "Low (낮음)"}
    ]
    default_action_types = [
        {"code": "AT001", "id": "block", "name": "차단 (Block)"},
        {"code": "AT002", "id": "warn", "name": "경고 (Warn)"},
        {"code": "AT003", "id": "log_only", "name": "로그만 (Log Only)"},
        {"code": "AT004", "id": "replace", "name": "대체 (Replace)"}
    ]

    try:
        policy_types = await get_policy_types()
        filter_types = await get_filter_types()
        severity_levels = await get_severity_levels()
        action_types = await get_action_types()

        return {
            "policyTypes": policy_types.get('data', []) or default_policy_types,
            "filterTypes": filter_types.get('data', []) or default_filter_types,
            "severityLevels": severity_levels.get('data', []) or default_severity_levels,
            "actionTypes": action_types.get('data', []) or default_action_types
        }
    except Exception as e:
        logger.error(f"❌ 기준 데이터 조회 오류: {e}, 기본 데이터 반환")
        # 오류 시 기본 데이터 반환
        return {
            "policyTypes": default_policy_types,
            "filterTypes": default_filter_types,
            "severityLevels": default_severity_levels,
            "actionTypes": default_action_types
        }
    # ----- 1227 기본 데이터 반환 수정 종료 -----


# ============================================
# 검사 로그 API
# ============================================

@app.get("/api/guardrails/logs")
async def get_guardrails_logs(
    limit: int = 50,
    offset: int = 0,
    result: Optional[str] = None,
    policy_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """가드레일 검사 로그 조회"""
    try:
        from database import execute_raw_query

        conditions = ["1=1"]
        if result and result != 'all':
            conditions.append(f"l.check_result = '{result}'")
        if policy_id:
            conditions.append(f"l.policy_id = '{policy_id}'")
        if start_date:
            conditions.append(f"l.created_at >= '{start_date}'")
        if end_date:
            conditions.append(f"l.created_at <= '{end_date}'")

        where_clause = " AND ".join(conditions)

        # [2026-01-23 수정] user_email 컬럼 추가
        query = f"""
            SELECT
                l.id,
                l.request_id,
                l.user_id,
                l.user_email,
                l.policy_id,
                l.check_result,
                l.original_text,
                l.detection_score,
                l.detected_keywords,
                l.detected_categories,
                l.created_at,
                p.name as policy_name,
                p.severity
            FROM guardrail_check_logs l
            LEFT JOIN guardrail_policies p ON l.policy_id = p.id
            WHERE {where_clause}
            ORDER BY l.created_at DESC
            LIMIT {limit} OFFSET {offset}
        """

        count_query = f"""
            SELECT COUNT(*) as total
            FROM guardrail_check_logs l
            WHERE {where_clause}
        """

        results = await execute_raw_query(query)
        count_result = await execute_raw_query(count_query)
        total = count_result[0].get('total', 0) if count_result else 0

        # 프론트엔드에서 기대하는 snake_case 필드명으로 변환
        logs = []
        for l in (results or []):
            detected_kws = l.get('detected_keywords', [])
            if isinstance(detected_kws, str):
                try:
                    import json
                    detected_kws = json.loads(detected_kws)
                except:
                    detected_kws = []
            
            logs.append({
                "id": l.get('id'),
                "request_id": l.get('request_id', ''),
                "user_id": l.get('user_id', ''),
                "user_email": l.get('user_email', ''),  # [2026-01-23 추가]
                "policy_id": l.get('policy_id', ''),
                "policy_name": l.get('policy_name', ''),
                "check_result": l.get('check_result', ''),
                "severity": l.get('severity', 'medium'),
                "original_text": l.get('original_text', '')[:100] if l.get('original_text') else '',
                "detected_keywords": detected_kws if detected_kws else [],
                "detected_categories": l.get('detected_categories', []) or [],
                "detection_score": float(l.get('detection_score', 0) or 0),
                "created_at": l.get('created_at').isoformat() if l.get('created_at') else ''
            })

        return {
            "data": logs,
            "total": total,
            "limit": limit,
            "offset": offset,
            "hasMore": offset + limit < total
        }

    except Exception as e:
        logger.error(f"❌ 로그 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guardrails/trend")
async def get_guardrails_trend(range: Optional[str] = '7d'):
    """가드레일 검사 추이 조회"""
    try:
        from database import execute_raw_query

        days = 7
        if range == '1d':
            days = 1
        elif range == '30d':
            days = 30
        elif range == '90d':
            days = 90

        query = f"""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as total_checks,
                COUNT(*) FILTER (WHERE check_result = 'block') as blocked_count,
                COUNT(*) FILTER (WHERE check_result = 'pass') as passed_count,
                COUNT(*) FILTER (WHERE check_result = 'warn') as warning_count
            FROM guardrail_check_logs
            WHERE created_at >= NOW() - INTERVAL '{days} days'
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """

        results = await execute_raw_query(query)

        return {
            "data": [{
                "date": r.get('date').isoformat() if r.get('date') else '',
                "totalChecks": r.get('total_checks', 0) or 0,
                "blockedCount": r.get('blocked_count', 0) or 0,
                "passedCount": r.get('passed_count', 0) or 0,
                "warningCount": r.get('warning_count', 0) or 0
            } for r in (results or [])],
            "range": range
        }

    except Exception as e:
        logger.error(f"❌ 추이 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === Main Entry Point ===



# 사용자 정보 조회 (sdc_dev 데이터베이스)
@app.get("/api/guardrails/users")
async def get_users():
    """sdc_dev 데이터베이스에서 사용자 목록 조회"""
    try:
        import asyncpg
        # sdc_dev 데이터베이스 연결
        conn = await asyncpg.connect(
            host=os.getenv("DB_HOST", "192.168.122.85"),
            port=int(os.getenv("DB_PORT", "5433")),
            user=os.getenv("DB_USER", "sdc_dev_user"),
            password=os.getenv("DB_PASSWORD", "sdc_dev_pass_2025"),
            database="sdc_dev"
        )
        try:
            rows = await conn.fetch('SELECT id, name, email FROM "user"')
            users = [{"id": str(r["id"]), "name": r["name"], "email": r["email"]} for r in rows]
            return {"users": users}
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"사용자 조회 오류: {e}")
        return {"users": [], "error": str(e)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Arthur AI Guardrails Service with PostgreSQL")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    print(f"🛡️ Starting Arthur AI Guardrails Service with PostgreSQL on {args.host}:{args.port}")

    uvicorn.run(
        "arthur_guardrails_service:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )