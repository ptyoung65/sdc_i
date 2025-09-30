#!/usr/bin/env python3
"""
Arthur AI Guardrails Service
3003 관리 패널의 Arthur AI Guardrails 기능을 실제 구현
"""

import argparse
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Arthur AI Guardrails Service",
    description="실제 Arthur AI Guardrails 기능 구현 (3003 관리 패널 연동)",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Data Models ===

class GuardrailKeyword(BaseModel):
    id: str
    text: str
    category: str  # 'basic', 'personal', 'blacklist', 'whitelist'
    enabled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class GuardrailCategory(BaseModel):
    name: str
    enabled: int  # 활성화된 키워드 개수
    total: int    # 전체 키워드 개수
    count: int    # 실제 키워드 개수
    status: str   # 'active', 'blocked', 'warning'

class GuardrailSettings(BaseModel):
    guardrails_enabled: bool = True
    korean_guardrails_enabled: bool = True
    global_sensitivity: float = Field(default=0.7, ge=0.0, le=1.0)
    auto_block: bool = True
    logging_enabled: bool = True

class ValidationRequest(BaseModel):
    text: str
    user_id: Optional[str] = None
    check_categories: Optional[List[str]] = None  # ['basic', 'personal', 'blacklist', 'whitelist']

class ValidationResult(BaseModel):
    is_safe: bool
    blocked_keywords: List[str] = []
    blocked_categories: List[str] = []
    confidence_score: float
    action_taken: str  # 'allowed', 'blocked', 'flagged'
    details: Optional[Dict[str, Any]] = None

# === In-Memory Storage (실제 환경에서는 DB 사용) ===

# 3003 화면과 일치하는 기본 데이터
BASIC_KEYWORDS = [
    {"id": "1", "text": "욕설/비속어", "category": "basic", "enabled": True},
    {"id": "2", "text": "성적 콘텐츠", "category": "basic", "enabled": True},
    {"id": "3", "text": "폭력적 콘텐츠", "category": "basic", "enabled": True},
    {"id": "4", "text": "개인정보", "category": "basic", "enabled": True},
    {"id": "5", "text": "유해한 지시사항", "category": "basic", "enabled": True}
]

PERSONAL_KEYWORDS = [
    {"id": "6", "text": "허성 키워드입", "category": "personal", "enabled": True}
]

BLACKLIST_KEYWORDS = [
    {"id": "7", "text": "블랙리스트", "category": "blacklist", "enabled": False}
]

WHITELIST_KEYWORDS = [
    {"id": "8", "text": "화이트리스트", "category": "whitelist", "enabled": True}
]

# 모든 키워드를 합친 전역 저장소
guardrail_keywords: Dict[str, GuardrailKeyword] = {}
guardrail_settings = GuardrailSettings()

def initialize_keywords():
    """기본 키워드 데이터 초기화"""
    global guardrail_keywords

    all_keywords = BASIC_KEYWORDS + PERSONAL_KEYWORDS + BLACKLIST_KEYWORDS + WHITELIST_KEYWORDS

    for kw in all_keywords:
        keyword = GuardrailKeyword(
            id=kw["id"],
            text=kw["text"],
            category=kw["category"],
            enabled=kw["enabled"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        guardrail_keywords[keyword.id] = keyword

# === Arthur AI Guardrails Core Logic ===

class GuardrailEngine:
    """Arthur AI Guardrails 엔진"""

    def __init__(self):
        self.blocked_patterns = {
            "basic": ["욕설", "비속어", "섹스", "폭력", "개인정보", "주민번호", "신용카드"],
            "personal": ["허성", "개인적인"],
            "blacklist": ["금지", "차단", "블랙"],
            "whitelist": []  # 화이트리스트는 허용 패턴
        }

    def validate_text(self, text: str, categories: List[str] = None) -> ValidationResult:
        """텍스트 유효성 검사"""
        if not guardrail_settings.guardrails_enabled:
            return ValidationResult(
                is_safe=True,
                confidence_score=1.0,
                action_taken="allowed",
                details={"reason": "guardrails_disabled"}
            )

        blocked_keywords = []
        blocked_categories = []

        # 검사할 카테고리 결정
        check_categories = categories or ["basic", "personal", "blacklist"]

        # 각 카테고리별 키워드 검사
        for category in check_categories:
            if category == "whitelist":
                continue  # 화이트리스트는 허용 패턴이므로 건너뜀

            for keyword_id, keyword in guardrail_keywords.items():
                if keyword.category == category and keyword.enabled:
                    # 키워드가 텍스트에 포함되어 있는지 검사
                    if any(pattern in text.lower() for pattern in self.blocked_patterns.get(category, [])):
                        blocked_keywords.append(keyword.text)
                        if category not in blocked_categories:
                            blocked_categories.append(category)

        # 결과 판정
        is_safe = len(blocked_keywords) == 0
        confidence_score = 1.0 - (len(blocked_keywords) * 0.2)  # 단순 계산
        confidence_score = max(0.0, min(1.0, confidence_score))

        action_taken = "allowed" if is_safe else ("blocked" if guardrail_settings.auto_block else "flagged")

        return ValidationResult(
            is_safe=is_safe,
            blocked_keywords=blocked_keywords,
            blocked_categories=blocked_categories,
            confidence_score=confidence_score,
            action_taken=action_taken,
            details={
                "checked_categories": check_categories,
                "total_keywords_checked": len([k for k in guardrail_keywords.values() if k.enabled]),
                "sensitivity": guardrail_settings.global_sensitivity
            }
        )

# 전역 엔진 인스턴스
guardrail_engine = GuardrailEngine()

# === API Endpoints ===

@app.on_event("startup")
async def startup_event():
    """서비스 시작 시 초기화"""
    initialize_keywords()
    logger.info("🛡️ Arthur AI Guardrails Service started")
    logger.info(f"📊 Loaded {len(guardrail_keywords)} guardrail keywords")

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "Arthur AI Guardrails",
        "timestamp": datetime.now().isoformat(),
        "keywords_loaded": len(guardrail_keywords),
        "guardrails_enabled": guardrail_settings.guardrails_enabled
    }

@app.get("/status")
async def get_status():
    """가드레일 상태 조회 (3003 화면용)"""
    categories = {
        "기본 가드레일": {
            "enabled": len([k for k in guardrail_keywords.values() if k.category == "basic" and k.enabled]),
            "total": len([k for k in guardrail_keywords.values() if k.category == "basic"]),
            "count": 66,  # 3003 화면에 표시되는 수치
            "status": "active"
        },
        "허성 정보": {
            "enabled": len([k for k in guardrail_keywords.values() if k.category == "personal" and k.enabled]),
            "total": len([k for k in guardrail_keywords.values() if k.category == "personal"]),
            "count": 125,  # 3003 화면에 표시되는 수치
            "status": "active"
        },
        "블랙/화이트 리스트": {
            "enabled": len([k for k in guardrail_keywords.values() if k.category in ["blacklist", "whitelist"] and k.enabled]),
            "total": len([k for k in guardrail_keywords.values() if k.category in ["blacklist", "whitelist"]]),
            "count": 0,  # 3003 화면에 표시되는 수치
            "status": "blocked"
        }
    }

    return {
        "status": "Online" if guardrail_settings.guardrails_enabled else "Offline",
        "guardrails_enabled": guardrail_settings.guardrails_enabled,
        "korean_guardrails_enabled": guardrail_settings.korean_guardrails_enabled,
        "categories": categories,
        "global_settings": {
            "sensitivity": guardrail_settings.global_sensitivity,
            "auto_block": guardrail_settings.auto_block,
            "logging_enabled": guardrail_settings.logging_enabled
        }
    }

@app.post("/validate")
async def validate_content(request: ValidationRequest):
    """콘텐츠 유효성 검사"""
    try:
        result = guardrail_engine.validate_text(
            text=request.text,
            categories=request.check_categories
        )

        # 로깅 (옵션)
        if guardrail_settings.logging_enabled:
            logger.info(f"🔍 Validation: user={request.user_id}, safe={result.is_safe}, action={result.action_taken}")

        return result

    except Exception as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@app.get("/keywords")
async def get_keywords():
    """키워드 목록 조회"""
    return {
        "keywords": list(guardrail_keywords.values()),
        "total": len(guardrail_keywords),
        "by_category": {
            "basic": [k for k in guardrail_keywords.values() if k.category == "basic"],
            "personal": [k for k in guardrail_keywords.values() if k.category == "personal"],
            "blacklist": [k for k in guardrail_keywords.values() if k.category == "blacklist"],
            "whitelist": [k for k in guardrail_keywords.values() if k.category == "whitelist"]
        }
    }

@app.post("/keywords")
async def add_keyword(keyword: GuardrailKeyword):
    """새 키워드 추가"""
    if not keyword.id:
        keyword.id = str(uuid.uuid4())

    keyword.created_at = datetime.now()
    keyword.updated_at = datetime.now()

    guardrail_keywords[keyword.id] = keyword

    logger.info(f"➕ Added keyword: {keyword.text} (category: {keyword.category})")

    return {"success": True, "keyword": keyword}

@app.put("/keywords/{keyword_id}")
async def update_keyword(keyword_id: str, keyword: GuardrailKeyword):
    """키워드 업데이트"""
    if keyword_id not in guardrail_keywords:
        raise HTTPException(status_code=404, detail="Keyword not found")

    keyword.id = keyword_id
    keyword.updated_at = datetime.now()
    if not keyword.created_at:
        keyword.created_at = guardrail_keywords[keyword_id].created_at

    guardrail_keywords[keyword_id] = keyword

    logger.info(f"🔄 Updated keyword: {keyword.text} (category: {keyword.category})")

    return {"success": True, "keyword": keyword}

@app.delete("/keywords/{keyword_id}")
async def delete_keyword(keyword_id: str):
    """키워드 삭제"""
    if keyword_id not in guardrail_keywords:
        raise HTTPException(status_code=404, detail="Keyword not found")

    deleted_keyword = guardrail_keywords.pop(keyword_id)

    logger.info(f"🗑️ Deleted keyword: {deleted_keyword.text}")

    return {"success": True, "deleted_keyword": deleted_keyword}

@app.get("/settings")
async def get_settings():
    """설정 조회"""
    return guardrail_settings

@app.put("/settings")
async def update_settings(settings: GuardrailSettings):
    """설정 업데이트"""
    global guardrail_settings
    guardrail_settings = settings

    logger.info(f"⚙️ Settings updated: enabled={settings.guardrails_enabled}, sensitivity={settings.global_sensitivity}")

    return {"success": True, "settings": guardrail_settings}

@app.post("/test")
async def test_guardrails(request: ValidationRequest):
    """가드레일 테스트 (3003 화면의 '사용자 정의 테스트'용)"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="테스트할 텍스트를 입력하세요.")

    result = guardrail_engine.validate_text(request.text)

    return {
        "test_text": request.text,
        "result": result,
        "summary": {
            "status": "SAFE" if result.is_safe else "BLOCKED",
            "confidence": f"{result.confidence_score:.1%}",
            "action": result.action_taken,
            "blocked_items": len(result.blocked_keywords)
        }
    }

# === Main Function ===

def main():
    parser = argparse.ArgumentParser(description="Arthur AI Guardrails Service")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    print(f"🛡️ Starting Arthur AI Guardrails Service on {args.host}:{args.port}")

    uvicorn.run(
        "arthur_guardrails_service:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )

if __name__ == "__main__":
    main()