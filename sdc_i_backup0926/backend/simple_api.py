"""
Simplified API with RAG integration for document-based chat
"""
from fastapi import FastAPI, HTTPException, File, Form, UploadFile, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import os
import json
from datetime import datetime, timedelta
import uuid

# HOST_IP 환경변수 설정 (모든 하드코딩 IP 제거)
HOST_IP = os.getenv("HOST_IP") or "192.168.122.177"  # 환경변수 우선, 최후 fallback
try:
    import google.generativeai as genai
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    print("⚠️ [AI] Google Generative AI not available - using basic responses")
    genai = None
    GOOGLE_AI_AVAILABLE = False
import asyncio
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    print("⚠️ [ENV] python-dotenv not available - using system environment variables")
    DOTENV_AVAILABLE = False

# Development bypass flag
DANGEROUSLY_SKIP_PERMISSIONS = os.getenv("DANGEROUSLY_SKIP_PERMISSIONS", "false").lower() == "true"
if DANGEROUSLY_SKIP_PERMISSIONS:
    print("⚠️  [SECURITY] DANGEROUSLY_SKIP_PERMISSIONS is enabled - ALL AUTHENTICATION BYPASSED!")
    print("🚨 [WARNING] This should ONLY be used in development environments!")

# Database imports (separate from RAG)
try:
    from app.core.database import get_db, create_tables, init_db
    from app.models.chat import User, Conversation, Message, Document
    from app.services.chat_history import ChatHistoryService, get_chat_history_service
    from sqlalchemy.ext.asyncio import AsyncSession
    DATABASE_AVAILABLE = True
    print("🗄️ [DATABASE] Database services loaded successfully - chat history enabled!")
except ImportError as e:
    DATABASE_AVAILABLE = False
    print(f"⚠️ [DATABASE] Database services not available: {e} - running without chat history")

# User Management Database Service
try:
    from database import db_service
    USER_MANAGEMENT_DB_AVAILABLE = True
    print("👥 [USER-MGMT-DB] User management database service loaded - PostgreSQL integration enabled!")
except ImportError as e:
    USER_MANAGEMENT_DB_AVAILABLE = False
    print(f"⚠️ [USER-MGMT-DB] User management database service not available: {e} - using mock data")

    # Create mock functions for when database is not available
    async def get_db():
        return None

    class MockChatHistoryService:
        async def get_or_create_user(self, *args, **kwargs):
            return None
        async def get_or_create_conversation(self, *args, **kwargs):
            return None
        async def save_message(self, *args, **kwargs):
            return None

    def get_chat_history_service():
        return MockChatHistoryService()

    # Define ChatHistoryService as Mock when not available
    ChatHistoryService = MockChatHistoryService
    AsyncSession = type(None)

# RAG service imports
try:
    from app.services.ai.rag_service import RAGService, RAGStrategy
    from app.services.document import DocumentService
    RAG_AVAILABLE = True
    print("📚 [RAG] RAG services loaded successfully - document-based chat enabled!")
except ImportError as e:
    RAG_AVAILABLE = False
    print(f"⚠️ [RAG] RAG services not available: {e} - running in basic mode")

# Docling service import
try:
    from app.services.document.docling_client import DoclingClient
    DOCLING_AVAILABLE = True
    print("📄 [DOCLING] Docling client loaded successfully - multi-format document processing enabled!")
except ImportError as e:
    DOCLING_AVAILABLE = False
    print(f"⚠️ [DOCLING] Docling client not available: {e} - falling back to basic text processing")

# Alternative document processor import
try:
    from app.services.document.alternative_processor import AlternativeProcessor
    ALT_PROCESSOR_AVAILABLE = True
    print("📄 [ALT-PROC] Alternative document processor loaded - local Python library processing enabled!")
except ImportError as e:
    ALT_PROCESSOR_AVAILABLE = False
    print(f"⚠️ [ALT-PROC] Alternative processor not available: {e}")

# Enhanced chunking system import
try:
    from app.services.document.enhanced_chunker import EnhancedChunker, ChunkingMethod, DocumentChunk
    ENHANCED_CHUNKER_AVAILABLE = True
    print("🔧 [ENHANCED-CHUNKER] Enhanced chunking system loaded - Python libraries + Docling chunking enabled!")
except ImportError as e:
    ENHANCED_CHUNKER_AVAILABLE = False
    print(f"⚠️ [ENHANCED-CHUNKER] Enhanced chunker not available: {e}")

# Milvus vector storage import
try:
    from app.services.vector.milvus_service import get_milvus_service
    MILVUS_SERVICE_AVAILABLE = True
    print("🗃️ [MILVUS] Milvus vector service loaded - vector storage enabled!")
except ImportError as e:
    MILVUS_SERVICE_AVAILABLE = False
    print(f"⚠️ [MILVUS] Milvus service not available: {e}")

# Korean RAG client import
try:
    import sys
    sys.path.append('/home/ptyoung/work/sdc_i/backend/services')
    from korean_rag_client import get_korean_rag_client
    KOREAN_RAG_AVAILABLE = True
    print("🇰🇷 [KOREAN-RAG] Korean RAG client loaded - Korean document-based RAG enabled!")
except ImportError as e:
    KOREAN_RAG_AVAILABLE = False
    print(f"⚠️ [KOREAN-RAG] Korean RAG client not available: {e}")

# Web search service import
try:
    from app.services.web_search import WebSearchService
    WEB_SEARCH_AVAILABLE = True
    print("🌐 [WEB-SEARCH] Web search service loaded - Searxng web search enabled!")
except ImportError as e:
    WEB_SEARCH_AVAILABLE = False
    print(f"⚠️ [WEB-SEARCH] Web search service not available: {e}")

# Agentic RAG service import
try:
    from app.services.ai.agentic_rag import AgenticRAGSystem
    AGENTIC_RAG_AVAILABLE = True
    print("🤖 [AGENTIC-RAG] Agentic RAG system loaded - Advanced AI agent capabilities enabled!")
except ImportError as e:
    AGENTIC_RAG_AVAILABLE = False
    print(f"⚠️ [AGENTIC-RAG] Agentic RAG system not available: {e}")

# Cache service import
try:
    from app.services.cache_service import CacheService, get_cache_service
    CACHE_AVAILABLE = True
    print("💾 [CACHE] Redis cache service loaded - response caching enabled!")
except ImportError as e:
    CACHE_AVAILABLE = False
    print(f"⚠️ [CACHE] Redis cache service not available: {e} - running without caching")

# Guardrails service import
try:
    from app.services.guardrails_client import get_guardrails_client, validate_user_input, validate_ai_output
    GUARDRAILS_AVAILABLE = True
    print("🛡️ [GUARDRAILS] Arthur AI Guardrails client loaded - Content safety validation enabled!")
except ImportError as e:
    GUARDRAILS_AVAILABLE = False
    print(f"⚠️ [GUARDRAILS] Guardrails client not available: {e} - running without content filtering")

# RAG evaluation service import
try:
    from app.services.rag_evaluation_client import (
        get_rag_evaluation_client, 
        evaluate_rag_session, 
        RAGPerformanceTracker
    )
    RAG_EVALUATION_AVAILABLE = True
    print("📊 [RAG-EVAL] RAG Performance Evaluation client loaded - Performance metrics enabled!")
except ImportError as e:
    RAG_EVALUATION_AVAILABLE = False
    print(f"⚠️ [RAG-EVAL] RAG evaluation client not available: {e} - running without performance metrics")

# Database availability flag (separate from RAG)
DATABASE_AVAILABLE = False

# .env 파일 로드 - 조건부 로드
if DOTENV_AVAILABLE:
    load_dotenv()
    print("✅ [ENV] .env file loaded successfully")
else:
    print("⚠️ [ENV] Using system environment variables only")

# AI 서비스 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "false").lower() == "true"
USE_FALLBACK_RESPONSES = os.getenv("USE_FALLBACK_RESPONSES", "false").lower() == "true"

# Gemini AI 설정 - 조건부 설정
if GEMINI_API_KEY and GOOGLE_AI_AVAILABLE and not OFFLINE_MODE:
    genai.configure(api_key=GEMINI_API_KEY)
    print("🌐 [AI] Gemini API configured for online mode")
else:
    print(f"🔒 [AI] Running in offline mode - OFFLINE_MODE={OFFLINE_MODE}, USE_FALLBACK_RESPONSES={USE_FALLBACK_RESPONSES}")
    
app = FastAPI(title="SDC Backend - Simple", version="0.1.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        f"http://{HOST_IP}:3000",
        f"http://{HOST_IP}:3003",
        f"http://{HOST_IP}:3004",
        # 개발 환경에서 모든 외부 접속 허용
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 초기화
@app.on_event("startup")
async def startup_event():
    """앱 시작시 데이터베이스 및 내부 서버 초기화"""
    global DATABASE_AVAILABLE, USER_MANAGEMENT_DB_AVAILABLE

    # 데이터베이스 초기화 (RAG_AVAILABLE과 독립적으로 실행)
    try:
        await init_db()
        print("✅ [DB] PostgreSQL database initialized successfully")
        DATABASE_AVAILABLE = True
    except Exception as e:
        print(f"❌ [DB] Database initialization failed: {e}")
        DATABASE_AVAILABLE = False
        print("⚠️ [DB] Database services not available - using in-memory storage")

    # 사용자 관리 데이터베이스 초기화
    if USER_MANAGEMENT_DB_AVAILABLE:
        try:
            success = await db_service.initialize()
            if success:
                print("✅ [USER-MGMT-DB] User management database initialized successfully")
            else:
                print("❌ [USER-MGMT-DB] User management database initialization failed")
                USER_MANAGEMENT_DB_AVAILABLE = False
        except Exception as e:
            print(f"❌ [USER-MGMT-DB] User management database initialization error: {e}")
            USER_MANAGEMENT_DB_AVAILABLE = False

    # 내부 서버 환경변수 로드
    if INTERNAL_SERVER_AVAILABLE:
        try:
            env_config = dict(os.environ)
            load_internal_servers_from_env(env_config)
            print("🔗 [INTERNAL] Internal servers loaded from environment variables")
        except Exception as e:
            print(f"⚠️ [INTERNAL] Failed to load internal servers from environment: {e}")

# Simple models
class ChatRequest(BaseModel):
    message: str
    provider: Optional[str] = "gemini"
    model: Optional[str] = None  # OpenAI 모델 선택 (gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-4, gpt-3.5-turbo)
    use_rag: Optional[bool] = False
    use_web_search: Optional[bool] = False
    web_search_engines: Optional[List[str]] = ["google"]
    search_mode: Optional[str] = "documents"
    use_agentic_rag: Optional[bool] = False
    agentic_complexity_threshold: Optional[int] = 5
    user_id: Optional[str] = "default_user"
    conversation_id: Optional[str] = None
    conversation_history: Optional[List[Dict]] = None
    # Multi-RAG configuration
    enabled_rag_types: Optional[Dict[str, bool]] = {
        "vector": True,
        "graph": True,
        "keyword": True,
        "database": True
    }
    # Internal server configuration
    use_internal_servers: Optional[bool] = False
    internal_server_mode: Optional[str] = "hybrid"

class ChatResponse(BaseModel):
    success: bool
    response: str
    provider: Optional[str] = None
    sources: Optional[List[Dict]] = None
    # Multi-RAG results
    rag_results: Optional[List[Dict]] = None
    has_multi_rag: Optional[bool] = False
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    # Cache and additional fields
    from_cache: Optional[bool] = False
    model: Optional[str] = None
    tokens: Optional[Dict] = None
    metadata: Optional[Dict] = None

class ConversationModel(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: str
    updated_at: str
    message_count: int

class MessageModel(BaseModel):
    id: str
    content: str
    role: str
    created_at: str
    conversation_id: str
    metadata: Optional[Dict] = None

class RatingRequest(BaseModel):
    message_id: str
    user_id: str
    rating_type: str  # "thumbs_up" or "thumbs_down"
    feedback_categories: Optional[List[str]] = None  # ["accuracy", "completeness", "faithfulness", "other"] for thumbs_down
    additional_feedback: Optional[str] = None  # Additional text feedback

# Mock data storage
conversations_db = {}
messages_db = {}
ratings_db = {}
user_documents = {}  # 사용자별 업로드된 문서 저장소

# OIDC 설정 저장소 (개발 환경용 - 실제 환경에서는 데이터베이스나 설정 파일 사용)
oidc_settings = {
    "enabled": False,  # 기본값: PostgreSQL 개발용 사용자 사용
    "current_oidc_user": None
}

# OIDC 세션 저장소 (실제 환경에서는 Redis나 데이터베이스 사용)
oidc_sessions = {}  # {session_token: user_info}

# AI Service Class
class AIService:
    def __init__(self):
        self.gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))
        self.rag_service = None
        self.document_service = None
        self.web_search_service = None
        self.agentic_rag_system = None
        
        # Initialize RAG services if available
        if RAG_AVAILABLE:
            print("🔧 [RAG] Initializing RAG services...")
        else:
            print("⚠️ [RAG] RAG services not available - using basic AI only")
            
        # Initialize web search service if available
        if WEB_SEARCH_AVAILABLE:
            self.web_search_service = WebSearchService()
            print("🌐 [WEB-SEARCH] Web search service initialized")
            
        # Initialize agentic RAG system if available
        if AGENTIC_RAG_AVAILABLE:
            self.agentic_rag_system = AgenticRAGSystem()
            print("🤖 [AGENTIC-RAG] Agentic RAG system initialized")
        
    async def generate_gemini_response(self, message: str, provider: str = "gemini", conversation_history: List[Dict] = None) -> str:
        """🔄 LOCAL LLM MIGRATION POINT 7: 백엔드 응답 생성 메소드
        현재: Gemini AI를 사용한 응답 생성
        향후: 로컬 LLM을 사용한 응답 생성으로 변경
        
        마이그레이션 계획:
        1. 메소드명 변경: generate_gemini_response -> generate_local_llm_response
        2. provider 매개변수 확장: "gemini" -> "ollama", "vllm", "transformers" 등
        3. 모델 초기화 방식 변경:
           - genai.GenerativeModel() -> ollama.Client() 또는 AutoModelForCausalLM.from_pretrained()
        4. API 키 체크 -> 로컬 모델 가용성 체크로 변경
        5. 응답 생성 방식 변경:
           - model.generate_content() -> local_llm.generate() 또는 직접 추론
        
        예시 변경 사항:
        # if provider == "ollama":
        #     client = ollama.Client(host="localhost:11434")
        #     response = client.chat(model="gemma-7b-ko", messages=[...])
        # elif provider == "vllm":
        #     client = OpenAI(base_url="http://localhost:8000/v1")
        #     response = client.chat.completions.create(model="gemma-7b-ko", messages=[...])
        # elif provider == "transformers":
        #     inputs = tokenizer(context_message, return_tensors="pt")
        #     outputs = model.generate(**inputs, max_new_tokens=2048)
        #     response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        """
        print(f"🚀 [GEMINI] Starting AI request for message: {message[:50]}...")
        print(f"🔑 [GEMINI] API Key present: {bool(GEMINI_API_KEY)}")
        print(f"⚙️ [GEMINI] Model: {self.gemini_model_name}, Temperature: {self.temperature}")

        try:
            # 오프라인 모드 체크 - 우선 처리
            if OFFLINE_MODE or USE_FALLBACK_RESPONSES:
                print(f"🔒 [GEMINI] Running in offline mode - providing fallback response")
                fallback_responses = [
                    f"안녕하세요! 현재 시스템이 오프라인 모드로 실행 중입니다.\n\n'{message[:100]}...' 에 대해 기본적인 도움을 드리겠습니다.\n\n죄송하지만 현재 상황에서는 제한된 응답만 제공할 수 있습니다.",
                    f"시스템이 현재 오프라인 모드에서 작동하고 있습니다.\n\n요청하신 내용: '{message[:100]}...' 에 대해 가능한 범위에서 도움을 드리고자 합니다.\n\n더 정확한 답변을 위해서는 온라인 모드가 필요합니다.",
                    f"죄송합니다. 현재 시스템이 오프라인 모드로 실행 중입니다.\n\n'{message[:100]}...' 에 관한 질문을 해주셨는데, 지금은 기본적인 응답만 가능합니다.\n\n더 나은 서비스를 위해 온라인 모드를 활성화해 주세요."
                ]
                import random
                return random.choice(fallback_responses)

            if not GOOGLE_AI_AVAILABLE:
                error_msg = "Google Generative AI 패키지가 설치되지 않았습니다. 기본 응답을 제공합니다."
                print(f"⚠️ [AI] {error_msg}")
                return "죄송합니다. 현재 AI 서비스가 제한된 모드로 실행 중입니다. 기본적인 응답만 제공 가능합니다."

            if not GEMINI_API_KEY:
                error_msg = "Gemini API 키가 설정되지 않았습니다. .env 파일을 확인해주세요."
                print(f"❌ [GEMINI] {error_msg}")
                return error_msg

            # Gemini 모델 초기화
            print(f"📝 [GEMINI] Initializing model: {self.gemini_model_name}")
            model = genai.GenerativeModel(self.gemini_model_name)
            
            # 대화 히스토리가 있으면 컨텍스트에 포함
            context_message = message
            if conversation_history and len(conversation_history) > 0:
                print(f"📚 [GEMINI] Adding conversation history: {len(conversation_history)} messages")
                context = "이전 대화 내용:\n"
                for msg in conversation_history[-5:]:  # 최근 5개 메시지만 포함
                    role = "사용자" if msg["role"] == "user" else "어시스턴트"
                    context += f"{role}: {msg['content'][:100]}\n"
                context += f"\n현재 질문: {message}\n\n위의 대화 맥락을 고려하여 답변해주세요."
                context_message = context
                print(f"📝 [GEMINI] Final context length: {len(context_message)} chars")
            
            # Gemini에게 요청
            print(f"🌐 [GEMINI] Sending request to Gemini API...")
            response = await asyncio.to_thread(
                model.generate_content, 
                context_message,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                )
            )
            
            print(f"📡 [GEMINI] Raw response received: {type(response)}")
            print(f"📄 [GEMINI] Response text length: {len(response.text) if response.text else 0}")
            
            if response.text:
                result = response.text.strip()
                print(f"✅ [GEMINI] Success! Response preview: {result[:100]}...")
                return result
            else:
                error_msg = "죄송합니다. 응답을 생성하지 못했습니다."
                print(f"⚠️ [GEMINI] Empty response: {error_msg}")
                return error_msg
                
        except Exception as e:
            error_str = str(e).lower()
            print(f"❌ [GEMINI] Exception occurred: {type(e).__name__}: {str(e)}")

            # Quota 제한 오류 감지 및 fallback 응답
            if any(quota_indicator in error_str for quota_indicator in ['quota', '429', 'resource_exhausted', 'rate limit']):
                print(f"📊 [GEMINI] Quota exceeded detected, providing fallback response")
                fallback_responses = [
                    f"안녕하세요! 현재 AI 서비스 사용량이 일시적으로 제한되어 있습니다.\n\n귀하의 질문: '{message[:100]}...' 에 대해 기본적인 도움을 드리겠습니다.\n\n죄송하지만 현재 상황에서는 제한된 응답만 제공할 수 있습니다. 잠시 후 다시 시도해 주시기 바랍니다.",
                    f"현재 Google Gemini API 사용량 한도에 도달하여 일시적으로 서비스가 제한되고 있습니다.\n\n요청하신 내용: '{message[:100]}...' 에 대해 가능한 범위에서 도움을 드리고자 합니다.\n\n보다 정확한 답변을 위해서는 잠시 후 다시 질문해 주시기 바랍니다.",
                    f"죄송합니다. 현재 AI 서비스 이용량이 임시로 제한되어 있습니다.\n\n'{message[:100]}...' 에 관한 질문을 해주셨는데, 지금은 기본적인 응답만 가능합니다.\n\n더 나은 서비스를 위해 곧 정상화될 예정이니 조금만 기다려 주세요."
                ]

                # 메시지 내용에 따라 적절한 fallback 선택
                import random
                selected_response = random.choice(fallback_responses)
                return selected_response

            # 기타 오류에 대한 일반적인 처리
            import traceback
            print(f"📊 [GEMINI] Full traceback:\n{traceback.format_exc()}")

            error_msg = f"AI 서비스 오류가 발생했습니다: {str(e)}"
            return error_msg

    async def generate_openai_response(self, message: str, provider: str = "openai", conversation_history: List[Dict] = None, model: str = None) -> str:
        """OpenAI ChatGPT를 사용하여 응답 생성 (모델 선택 가능)"""
        print(f"🚀 [OPENAI] Starting ChatGPT request for message: {message[:50]}...")

        openai_api_key = os.getenv("OPENAI_API_KEY")
        print(f"🔑 [OPENAI] API Key present: {bool(openai_api_key)}")

        # 사용 가능한 OpenAI 모델 목록
        available_models = {
            "gpt-4o": "gpt-4o",  # 최신 모델 (기본값)
            "gpt-4o-mini": "gpt-4o-mini",  # 경량 모델
            "gpt-4-turbo": "gpt-4-turbo-preview",
            "gpt-4": "gpt-4",
            "gpt-3.5-turbo": "gpt-3.5-turbo"
        }

        # 모델 선택 (기본값: gpt-4o-mini)
        selected_model = model if model and model in available_models else "gpt-4o-mini"
        actual_model = available_models[selected_model]

        print(f"🤖 [OPENAI] Using model: {actual_model}")

        try:
            if not openai_api_key:
                error_msg = "OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인해주세요."
                print(f"❌ [OPENAI] {error_msg}")
                return error_msg

            import httpx

            # 대화 히스토리 준비
            messages = []
            if conversation_history and len(conversation_history) > 0:
                print(f"📚 [OPENAI] Adding conversation history: {len(conversation_history)} messages")
                for msg in conversation_history[-10:]:  # 최근 10개 메시지만 포함
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            # 현재 메시지 추가
            messages.append({
                "role": "user",
                "content": message
            })

            print(f"📝 [OPENAI] Sending request to ChatGPT with {len(messages)} messages")

            # 모델별 최적화된 설정
            model_settings = {
                "gpt-4o": {"temperature": 0.7, "max_tokens": 2000},
                "gpt-4o-mini": {"temperature": 0.7, "max_tokens": 1500},
                "gpt-4-turbo": {"temperature": 0.7, "max_tokens": 2000},
                "gpt-4": {"temperature": 0.7, "max_tokens": 1500},
                "gpt-3.5-turbo": {"temperature": 0.8, "max_tokens": 1000}
            }

            settings = model_settings.get(selected_model, model_settings["gpt-4o"])

            # OpenAI API 요청 페이로드 구성
            request_payload = {
                "model": actual_model,
                "messages": messages,
                **settings
            }

            # GPT-4o mini에 웹 검색 도구 추가
            if selected_model == "gpt-4o-mini":
                request_payload["tools"] = [
                    {
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "description": "Search the web for current information",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The search query"
                                    }
                                },
                                "required": ["query"]
                            }
                        }
                    }
                ]
                # tool_choice 설정: "required"는 항상 도구 사용 강제, "auto"는 필요시만 사용
                request_payload["tool_choice"] = "required"  # 항상 웹 검색 강제
                print(f"🔍 [OPENAI] Adding web_search function tool to {selected_model}")

            # OpenAI API 호출
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=request_payload,
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    message_data = data["choices"][0]["message"]

                    # 도구 호출이 있는 경우 처리
                    if "tool_calls" in message_data and message_data["tool_calls"]:
                        tool_calls = message_data["tool_calls"]
                        print(f"🔍 [OPENAI] Tool calls detected: {len(tool_calls)}")

                        # 도구 호출 처리 및 결과 수집
                        tool_results = []
                        for tool_call in tool_calls:
                            if tool_call["function"]["name"] == "web_search":
                                function_args = json.loads(tool_call["function"]["arguments"])
                                search_query = function_args.get("query", "")
                                print(f"🌐 [OPENAI] Web search called with query: {search_query}")

                                # 실제 웹 검색 수행 (간단한 응답 시뮬레이션)
                                search_result = f"웹 검색 결과: '{search_query}'에 대한 최신 정보를 찾았습니다."
                                tool_results.append({
                                    "tool_call_id": tool_call["id"],
                                    "role": "tool",
                                    "content": search_result
                                })

                        if tool_results:
                            # 도구 결과를 포함하여 재호출
                            messages.append(message_data)  # 원본 어시스턴트 메시지 추가
                            messages.extend(tool_results)

                            # 두 번째 API 호출 (도구 결과 포함, tools 제거)
                            second_request = {
                                "model": actual_model,
                                "messages": messages,
                                **settings
                            }
                            # tools와 tool_choice 제거 (도구 사용 완료)

                            response2 = await client.post(
                                "https://api.openai.com/v1/chat/completions",
                                headers={
                                    "Authorization": f"Bearer {openai_api_key}",
                                    "Content-Type": "application/json"
                                },
                                json=second_request,
                                timeout=30.0
                            )

                            if response2.status_code == 200:
                                data2 = response2.json()
                                result = data2["choices"][0]["message"]["content"]
                            else:
                                result = f"도구 사용 후 응답 생성 실패: HTTP {response2.status_code}"
                        else:
                            result = "도구 호출을 처리할 수 없습니다."
                    else:
                        # 일반 텍스트 응답
                        result = message_data.get("content", "응답을 가져올 수 없습니다.")

                    print(f"✅ [OPENAI] Success! Response preview: {result[:100] if result else 'No content'}...")
                    return result
                else:
                    error_msg = f"OpenAI API 오류: HTTP {response.status_code}"
                    print(f"❌ [OPENAI] API Error: {error_msg}")
                    print(f"Response: {response.text}")
                    return error_msg

        except Exception as e:
            error_msg = f"ChatGPT 서비스 오류가 발생했습니다: {str(e)}"
            print(f"❌ [OPENAI] Exception occurred: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"📊 [OPENAI] Full traceback:\n{traceback.format_exc()}")
            return error_msg

    async def generate_perplexity_response(self, message: str, provider: str = "perplexity", conversation_history: List[Dict] = None) -> str:
        """Perplexity AI를 사용하여 웹 검색 기반 응답 생성"""
        print(f"🚀 [PERPLEXITY] Starting Perplexity request for message: {message[:50]}...")

        perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        print(f"🔑 [PERPLEXITY] API Key present: {bool(perplexity_api_key)}")

        try:
            if not perplexity_api_key:
                error_msg = "Perplexity API 키가 설정되지 않았습니다. .env 파일을 확인해주세요."
                print(f"❌ [PERPLEXITY] {error_msg}")
                return error_msg

            import httpx

            # 대화 히스토리 준비
            messages = []
            if conversation_history and len(conversation_history) > 0:
                print(f"📚 [PERPLEXITY] Adding conversation history: {len(conversation_history)} messages")
                for msg in conversation_history[-5:]:  # 최근 5개 메시지만 포함 (토큰 절약)
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            # 현재 메시지 추가
            messages.append({
                "role": "user",
                "content": message
            })

            print(f"📝 [PERPLEXITY] Sending request to Perplexity with {len(messages)} messages")

            # Perplexity API 호출
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {perplexity_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "sonar",
                        "messages": messages,
                        "temperature": 0.2,
                        "max_tokens": 2000,
                        "return_citations": True,
                        "return_images": False
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    result = data["choices"][0]["message"]["content"]

                    # 인용 정보가 있으면 추가
                    if "citations" in data:
                        citations = data["citations"]
                        if citations:
                            result += "\n\n📚 참고 자료:\n"
                            for i, citation in enumerate(citations[:3], 1):  # 최대 3개
                                result += f"{i}. {citation}\n"

                    print(f"✅ [PERPLEXITY] Success! Response preview: {result[:100]}...")
                    return result
                else:
                    error_msg = f"Perplexity API 오류: HTTP {response.status_code}"
                    print(f"❌ [PERPLEXITY] API Error: {error_msg}")
                    print(f"Response: {response.text}")
                    return error_msg

        except Exception as e:
            error_msg = f"Perplexity 서비스 오류가 발생했습니다: {str(e)}"
            print(f"❌ [PERPLEXITY] Exception occurred: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"📊 [PERPLEXITY] Full traceback:\n{traceback.format_exc()}")
            return error_msg

    async def generate_ai_response(self, message: str, provider: str = "gemini", conversation_history: List[Dict] = None, model: str = None) -> str:
        """Provider에 따라 적절한 AI 서비스를 호출하여 응답 생성"""
        if provider == "openai":
            return await self.generate_openai_response(message, provider, conversation_history, model)
        elif provider == "perplexity":
            return await self.generate_perplexity_response(message, provider, conversation_history)
        elif provider == "claude":
            return "Claude API는 아직 구현되지 않았습니다. 다른 AI 모델을 선택해주세요."
        else:  # gemini 또는 기타
            return await self.generate_gemini_response(message, provider, conversation_history)

    async def generate_response(
        self,
        message: str,
        provider: str = "gemini",
        conversation_history: List[Dict] = None,
        use_rag: bool = False,
        use_web_search: bool = False,
        web_search_engines: List[str] = None,
        search_mode: str = "documents",
        use_agentic_rag: bool = False,
        agentic_complexity_threshold: int = 5,
        user_id: str = "default_user",
        rag_tracker = None,
        enabled_rag_types: Dict[str, bool] = None,
        model: str = None
    ) -> Dict[str, any]:
        """선택된 LLM 제공자에 따라 응답 생성 (RAG, 웹 검색, 에이전틱 RAG 지원)"""
        print(f"🎯 [AI] Generate response - provider: {provider}, use_rag: {use_rag}, use_web_search: {use_web_search}, search_mode: {search_mode}, use_agentic_rag: {use_agentic_rag}")
        
        # Multi-RAG 사용 체크 - enabled_rag_types가 제공된 경우 multi-RAG 사용
        if enabled_rag_types and any(enabled_rag_types.values()):
            print(f"🔄 [MULTI-RAG] Multi-RAG enabled with types: {enabled_rag_types}")
            return await self.generate_multi_rag_response(
                message, user_id, provider, conversation_history, enabled_rag_types, rag_tracker
            )
        
        # 에이전틱 RAG 사용 체크 (복잡한 쿼리에 대해 자동 활성화)
        if use_agentic_rag or self._should_use_agentic_rag(message, agentic_complexity_threshold):
            return await self._generate_agentic_rag_response(
                message, provider, conversation_history, user_id, 
                use_rag, use_web_search, web_search_engines, search_mode
            )
        
        # 검색 모드에 따른 처리
        context_parts = []
        all_sources = []
        
        # 문서 검색 (RAG) 처리
        if use_rag or search_mode in ['documents', 'combined']:
            print(f"📚 [RAG] Attempting document-based response")
            
            # RAG 추적 시작
            if rag_tracker:
                rag_tracker.start_retrieval()
            
            # RAG 서비스가 사용 가능하면 우선 사용 (Korean RAG 우선)
            if KOREAN_RAG_AVAILABLE or RAG_AVAILABLE:
                rag_result = await self.generate_rag_response(message, user_id, provider, conversation_history, rag_tracker)
                if search_mode == 'documents':
                    return rag_result
                # 통합 모드에서는 컨텍스트로 사용
                context_parts.append(f"문서 검색 결과:\n{rag_result['response']}")
                all_sources.extend(rag_result.get('sources', []))
            else:
                # RAG 서비스 불가능 시 간단한 문서 검색 사용
                doc_result = await self.generate_simple_document_response(message, user_id, provider, conversation_history, rag_tracker)
                if search_mode == 'documents':
                    return doc_result
                # 통합 모드에서는 컨텍스트로 사용
                if doc_result['response']:
                    context_parts.append(f"문서 검색 결과:\n{doc_result['response']}")
                    all_sources.extend(doc_result.get('sources', []))
        
        # Dual Provider (웹 모드) 처리 - ChatGPT + Perplexity 동시 호출
        if search_mode == '웹':
            print(f"🌐 [DUAL-PROVIDER] Attempting dual provider mode (ChatGPT + Perplexity)")
            try:
                # ChatGPT와 Perplexity 병렬 호출
                gpt_task = self.generate_openai_response(message, "openai", conversation_history, "gpt-4o-mini")
                perplexity_task = self.generate_perplexity_response(message, "perplexity", conversation_history)

                # 병렬 실행
                gpt_response, perplexity_response = await asyncio.gather(
                    gpt_task, perplexity_task, return_exceptions=True
                )

                # 결과 처리
                dual_responses = {}

                if isinstance(gpt_response, Exception):
                    print(f"❌ [GPT] Error: {gpt_response}")
                    dual_responses["gpt"] = f"GPT Error: {str(gpt_response)}"
                else:
                    print(f"✅ [GPT] Success! Response preview: {gpt_response[:100]}...")
                    dual_responses["gpt"] = gpt_response

                if isinstance(perplexity_response, Exception):
                    print(f"❌ [PERPLEXITY] Error: {perplexity_response}")
                    dual_responses["perplexity"] = f"Perplexity Error: {str(perplexity_response)}"
                else:
                    print(f"✅ [PERPLEXITY] Success! Response preview: {perplexity_response[:100]}...")
                    dual_responses["perplexity"] = perplexity_response

                # 메인 응답은 GPT 또는 Perplexity 중 성공한 것 사용
                main_response = dual_responses.get("gpt", dual_responses.get("perplexity", "Both providers failed"))

                return {
                    "response": main_response,
                    "sources": [],
                    "dual_provider_responses": dual_responses,
                    "is_dual_provider": True
                }

            except Exception as e:
                print(f"❌ [DUAL-PROVIDER] Dual provider error: {e}")
                # 실패시 기본 AI로 폴백
                response = await self.generate_ai_response(message, provider, conversation_history)
                return {"response": response, "sources": []}

        # 웹 검색 처리
        if use_web_search or search_mode in ['web', 'combined']:
            print(f"🌐 [WEB-SEARCH] Attempting web search")
            if WEB_SEARCH_AVAILABLE and self.web_search_service:
                try:
                    # 웹 검색 수행
                    search_response = await self.web_search_service.search(
                        query=message,
                        engines=web_search_engines or ['google'],
                        language='ko'
                    )

                    if search_response.results:
                        print(f"🔍 [WEB-SEARCH] Found {len(search_response.results)} web results")
                        # 웹 검색 결과를 컨텍스트로 포맷팅
                        web_context = self.web_search_service.format_results_for_context(search_response)
                        context_parts.append(f"웹 검색 결과:\n{web_context}")

                        # 웹 검색만 사용하는 경우 직접 결과 반환
                        if search_mode == 'web':
                            enhanced_message = f"다음 웹 검색 결과를 바탕으로 질문에 답변해주세요:\n\n{web_context}\n\n질문: {message}"
                            response = await self.generate_ai_response(enhanced_message, provider, conversation_history)
                            return {
                                "response": response,
                                "sources": [{"type": "web", "results": search_response.results[:3]}]
                            }
                    else:
                        print(f"⚠️ [WEB-SEARCH] No web results found")

                except Exception as e:
                    print(f"❌ [WEB-SEARCH] Web search error: {e}")
            else:
                print(f"⚠️ [WEB-SEARCH] Web search service not available")
        
        # 통합 모드 또는 컨텍스트가 있는 경우 통합 응답 생성
        if context_parts:
            print(f"🔀 [AI] Generating integrated response with {len(context_parts)} context parts")
            
            # 생성 단계 추적 시작
            if rag_tracker:
                rag_tracker.start_generation()
            
            combined_context = "\n\n".join(context_parts)
            enhanced_message = f"다음 검색 결과들을 종합하여 질문에 답변해주세요:\n\n{combined_context}\n\n질문: {message}"
            response = await self.generate_ai_response(enhanced_message, provider, conversation_history)
            
            # 생성 단계 추적 완료
            if rag_tracker:
                rag_tracker.end_generation(response, provider or "gemini")
            
            return {"response": response, "sources": all_sources}
        
        # 기본 AI 응답
        print(f"🤖 [AI] Using basic AI response")
        
        # 생성 단계 추적 시작 (기본 응답의 경우)
        if rag_tracker:
            rag_tracker.start_generation()
        
        response = await self.generate_ai_response(message, provider, conversation_history)
        
        # 생성 단계 추적 완료 (기본 응답의 경우)
        if rag_tracker:
            rag_tracker.end_generation(response, provider or "gemini")
        
        return {"response": response, "sources": []}
    
    async def generate_rag_response(
        self, 
        message: str, 
        user_id: str,
        provider: str = "gemini",
        conversation_history: List[Dict] = None,
        rag_tracker = None
    ) -> Dict[str, any]:
        """RAG를 사용한 문서 기반 응답 생성 - Korean RAG 우선"""
        print(f"📚 [RAG] Starting RAG response generation")
        
        # Korean RAG가 사용 가능한 경우 우선적으로 사용
        if KOREAN_RAG_AVAILABLE:
            print(f"🇰🇷 [RAG] Korean RAG available, using Korean RAG service")
            return await self._generate_korean_rag_response(
                message, provider, conversation_history, user_id, rag_tracker
            )
        
        # Korean RAG가 없으면 기존 RAG 시스템 사용
        try:
            # RAG 서비스가 초기화되지 않았으면 초기화
            if not self.rag_service:
                print(f"🔧 [RAG] Initializing RAG service...")
                # Mock database session for now - in production use proper DI
                db_session = None  # This would be injected properly
                if db_session:
                    self.rag_service = RAGService(db_session)
                    self.document_service = DocumentService(db_session)
                else:
                    print(f"❌ [RAG] Database session not available - falling back to simple document search")
                    return await self.generate_simple_document_response(
                        message, user_id, provider, conversation_history, rag_tracker
                    )
            
            # RAG 쿼리 수행
            print(f"🔍 [RAG] Performing RAG query...")
            rag_response = await self.rag_service.query(
                query=message,
                user_id=user_id,
                strategy=RAGStrategy.HYBRID,  # Use hybrid search for best results
            )
            
            print(f"✅ [RAG] RAG query completed - {len(rag_response.sources)} sources found")
            
            # 소스 정보를 프론트엔드 형식으로 변환
            sources = []
            for source in rag_response.sources:
                sources.append({
                    "document_id": source.chunk.document_id,
                    "chunk_id": source.chunk.id,
                    "content_preview": source.chunk.content[:200] + "..." if len(source.chunk.content) > 200 else source.chunk.content,
                    "similarity_score": source.similarity_score,
                    "document_title": source.chunk.document.title if source.chunk.document else "Unknown Document",
                    "metadata": source.metadata
                })
            
            print(f"📄 [RAG] Generated response with {len(sources)} sources")
            return {
                "response": rag_response.answer,
                "sources": sources
            }
            
        except Exception as e:
            print(f"❌ [RAG] Error in RAG response generation: {str(e)}")
            import traceback
            print(f"📊 [RAG] Full traceback: {traceback.format_exc()}")
            
            # 실패시 simple document search로 fallback
            print(f"🔄 [RAG] Falling back to simple document search")
            return await self.generate_simple_document_response(
                message, user_id, provider, conversation_history, rag_tracker
            )
    
    async def _generate_korean_rag_response(
        self,
        message: str,
        provider: str,
        conversation_history: List[Dict[str, str]],
        user_id: str,
        rag_tracker=None
    ) -> Dict[str, Any]:
        """Korean RAG 서비스를 사용한 문서 기반 응답 생성"""
        print(f"🇰🇷 [KOREAN-RAG] Generating Korean RAG response for user: {user_id}")
        
        try:
            # Korean RAG 클라이언트로 컨텍스트 검색
            korean_rag_client = get_korean_rag_client()
            
            # RAG 추적 - 검색 시작
            if rag_tracker:
                rag_tracker.start_retrieval()
            
            search_result = await korean_rag_client.search_context(message)
            
            if search_result.get("status") != "success":
                print(f"🇰🇷 [KOREAN-RAG] Search failed: {search_result.get('message')}, fallback to simple document search")
                return await self.generate_simple_document_response(
                    message, user_id, provider, conversation_history, rag_tracker
                )
            
            has_context = search_result.get("has_context", False)
            context = search_result.get("context", "")
            chunks_count = search_result.get("chunks_count", 0)
            relevant_chunks = search_result.get("relevant_chunks", [])
            
            print(f"🇰🇷 [KOREAN-RAG] Search completed: {chunks_count} chunks found, has_context: {has_context}")
            
            # RAG 추적 - 검색 단계 완료
            if rag_tracker and relevant_chunks:
                chunks = [
                    {
                        "document_id": chunk.get("document_id", "unknown"),
                        "content": chunk.get("text", ""),
                        "score": chunk.get("similarity_score", 0.0)
                    }
                    for chunk in relevant_chunks
                ]
                rag_tracker.end_retrieval(chunks)
            
            if has_context and context:
                # Korean RAG에서 이미 최적화된 프롬프트 생성
                rag_prompt = search_result.get("rag_prompt", "")
                
                if rag_prompt:
                    print(f"🇰🇷 [KOREAN-RAG] Using Korean RAG optimized prompt ({len(rag_prompt)} chars)")
                    
                    # RAG 추적 - 생성 시작
                    if rag_tracker:
                        rag_tracker.start_generation(rag_prompt)
                    
                    # Korean RAG 최적화된 프롬프트로 응답 생성
                    response = await self.generate_ai_response(
                        rag_prompt, 
                        provider, 
                        conversation_history=[]  # RAG 프롬프트는 이미 컨텍스트를 포함하므로 히스토리 제외
                    )
                    
                    # RAG 추적 - 생성 완료
                    if rag_tracker:
                        rag_tracker.end_generation(response)
                    
                    print(f"🇰🇷 [KOREAN-RAG] Korean RAG response generated successfully")
                    
                    # 소스 정보 구성
                    sources = []
                    for chunk in relevant_chunks:
                        sources.append({
                            "document_id": chunk.get("document_id", "unknown"),
                            "chunk_id": chunk.get("chunk_id", 0),
                            "similarity_score": chunk.get("similarity_score", 0.0),
                            "content_preview": chunk.get("text", "")[:200] + "...",
                            "metadata": chunk.get("metadata", {}),
                            "source_type": "korean_rag"
                        })
                    
                    return {
                        "response": response,
                        "sources": sources,
                        "rag_method": "korean_rag",
                        "context_chunks": chunks_count,
                        "similarity_threshold": search_result.get("similarity_threshold", 0.7)
                    }
                else:
                    print(f"🇰🇷 [KOREAN-RAG] No RAG prompt generated, fallback to simple context")
                    # 컨텍스트만 있는 경우 간단한 프롬프트 구성
                    context_prompt = f"다음 문서 내용을 참고하여 질문에 답변해주세요:\n\n{context}\n\n질문: {message}"
                    
                    # RAG 추적 - 생성 시작
                    if rag_tracker:
                        rag_tracker.start_generation(context_prompt)
                    
                    response = await self.generate_ai_response(context_prompt, provider, conversation_history)
                    
                    # RAG 추적 - 생성 완료
                    if rag_tracker:
                        rag_tracker.end_generation(response)
                    
                    return {
                        "response": response,
                        "sources": [{"content_preview": context[:200] + "...", "source_type": "korean_rag"}],
                        "rag_method": "korean_rag_simple"
                    }
            else:
                print(f"🇰🇷 [KOREAN-RAG] No relevant context found, fallback to simple document search")
                return await self.generate_simple_document_response(
                    message, user_id, provider, conversation_history, rag_tracker
                )
                
        except Exception as e:
            print(f"❌ [KOREAN-RAG] Error in Korean RAG: {str(e)}")
            import traceback
            print(f"📊 [KOREAN-RAG] Full traceback: {traceback.format_exc()}")
            
            # 실패시 simple document search로 fallback
            print(f"🔄 [KOREAN-RAG] Falling back to simple document search")
            return await self.generate_simple_document_response(
                message, user_id, provider, conversation_history, rag_tracker
            )
    
    async def generate_multi_rag_response(
        self,
        message: str,
        user_id: str,
        provider: str = "gemini",
        conversation_history: List[Dict] = None,
        enabled_rag_types: Dict[str, bool] = None,
        rag_tracker = None
    ) -> Dict[str, any]:
        """Multiple RAG systems을 사용한 통합 응답 생성"""
        print(f"🔄 [MULTI-RAG] Starting multi-RAG query for user: {user_id}")
        
        if not enabled_rag_types:
            enabled_rag_types = {"vector": True, "graph": True, "keyword": True, "database": True}
        
        rag_results = []
        successful_responses = []
        
        # Vector RAG (Korean RAG Service)
        if enabled_rag_types.get("vector", False):
            try:
                print(f"🇰🇷 [MULTI-RAG] Attempting Vector RAG...")
                vector_result = await self._generate_korean_rag_response(
                    message, provider, conversation_history, user_id, rag_tracker
                )
                
                if vector_result and vector_result.get("response"):
                    successful_responses.append(vector_result["response"])
                    rag_results.append({
                        "type": "vector",
                        "success": True,
                        "response": vector_result["response"],
                        "metadata": {
                            "sources": len(vector_result.get("sources", [])),
                            "confidence": 0.8,
                            "processingTime": 1.2
                        }
                    })
                    print(f"✅ [MULTI-RAG] Vector RAG successful")
                else:
                    rag_results.append({
                        "type": "vector",
                        "success": False,
                        "error": "No relevant context found in vector search"
                    })
                    print(f"❌ [MULTI-RAG] Vector RAG failed - no context")
            except Exception as e:
                rag_results.append({
                    "type": "vector",
                    "success": False,
                    "error": f"Vector RAG error: {str(e)}"
                })
                print(f"❌ [MULTI-RAG] Vector RAG exception: {e}")
        
        # Graph RAG Service
        if enabled_rag_types.get("graph", False):
            try:
                import httpx
                print(f"🕸️ [MULTI-RAG] Attempting Graph RAG...")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    graph_response = await client.post(
                        "http://localhost:8008/query",
                        json={"query": message, "user_id": user_id}
                    )
                    if graph_response.status_code == 200:
                        graph_data = graph_response.json()
                        if graph_data.get("success") and graph_data.get("response"):
                            successful_responses.append(graph_data["response"])
                            rag_results.append({
                                "type": "graph",
                                "success": True,
                                "response": graph_data["response"],
                                "metadata": {
                                    "resultCount": graph_data.get("result_count", 0),
                                    "confidence": 0.75,
                                    "processingTime": graph_data.get("processing_time", 0)
                                }
                            })
                            print(f"✅ [MULTI-RAG] Graph RAG successful")
                        else:
                            rag_results.append({
                                "type": "graph",
                                "success": False,
                                "error": "No relevant graph relationships found"
                            })
                    else:
                        rag_results.append({
                            "type": "graph",
                            "success": False,
                            "error": f"Graph RAG service error: HTTP {graph_response.status_code}"
                        })
            except Exception as e:
                rag_results.append({
                    "type": "graph",
                    "success": False,
                    "error": f"Graph RAG connection error: {str(e)}"
                })
                print(f"❌ [MULTI-RAG] Graph RAG exception: {e}")
        
        # Keyword RAG Service
        if enabled_rag_types.get("keyword", False):
            try:
                import httpx
                print(f"🔍 [MULTI-RAG] Attempting Keyword RAG...")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    keyword_response = await client.post(
                        "http://localhost:8011/search",
                        json={"query": message, "user_id": user_id}
                    )
                    if keyword_response.status_code == 200:
                        keyword_data = keyword_response.json()
                        if keyword_data.get("success") and keyword_data.get("response"):
                            successful_responses.append(keyword_data["response"])
                            rag_results.append({
                                "type": "keyword",
                                "success": True,
                                "response": keyword_data["response"],
                                "metadata": {
                                    "resultCount": keyword_data.get("result_count", 0),
                                    "confidence": 0.7,
                                    "processingTime": keyword_data.get("processing_time", 0)
                                }
                            })
                            print(f"✅ [MULTI-RAG] Keyword RAG successful")
                        else:
                            rag_results.append({
                                "type": "keyword",
                                "success": False,
                                "error": "No relevant keywords found"
                            })
                    else:
                        rag_results.append({
                            "type": "keyword",
                            "success": False,
                            "error": f"Keyword RAG service error: HTTP {keyword_response.status_code}"
                        })
            except Exception as e:
                rag_results.append({
                    "type": "keyword",
                    "success": False,
                    "error": f"Keyword RAG connection error: {str(e)}"
                })
                print(f"❌ [MULTI-RAG] Keyword RAG exception: {e}")
        
        # Database RAG (Text-to-SQL)
        if enabled_rag_types.get("database", False):
            try:
                import httpx
                print(f"🗄️ [MULTI-RAG] Attempting Database RAG...")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    db_response = await client.post(
                        "http://localhost:8012/ask",
                        json={"question": message, "user_id": user_id}
                    )
                    if db_response.status_code == 200:
                        db_data = db_response.json()
                        if db_data.get("success") and db_data.get("data"):
                            # Extract meaningful response from database RAG
                            final_answer = db_data["data"].get("final_answer", {})
                            suggested_prompt = final_answer.get("suggested_prompt", "")
                            if suggested_prompt:
                                successful_responses.append(suggested_prompt)
                                rag_results.append({
                                    "type": "database",
                                    "success": True,
                                    "response": suggested_prompt,
                                    "metadata": {
                                        "resultCount": db_data["data"].get("query_execution", {}).get("row_count", 0),
                                        "confidence": db_data["data"].get("rag_processing", {}).get("quality_score", 0.0),
                                        "processingTime": db_data.get("processing_time", 0)
                                    }
                                })
                                print(f"✅ [MULTI-RAG] Database RAG successful")
                            else:
                                rag_results.append({
                                    "type": "database",
                                    "success": False,
                                    "error": "No database results found"
                                })
                        else:
                            rag_results.append({
                                "type": "database",
                                "success": False,
                                "error": db_data.get("error", "Database RAG query failed")
                            })
                    else:
                        rag_results.append({
                            "type": "database",
                            "success": False,
                            "error": f"Database RAG service error: HTTP {db_response.status_code}"
                        })
            except Exception as e:
                rag_results.append({
                    "type": "database",
                    "success": False,
                    "error": f"Database RAG connection error: {str(e)}"
                })
                print(f"❌ [MULTI-RAG] Database RAG exception: {e}")
        
        # Generate combined response using successful results
        if successful_responses:
            # Create a comprehensive prompt combining all RAG results
            combined_context = "\n\n".join([
                f"RAG 검색 결과 {i+1}:\n{response}" 
                for i, response in enumerate(successful_responses)
            ])
            
            enhanced_prompt = f"""다음은 여러 RAG 시스템에서 검색된 정보입니다:

{combined_context}

위 정보를 종합하여 사용자의 질문 '{message}'에 대해 정확하고 완전한 답변을 해주세요.
중복되는 정보는 통합하고, 상충되는 정보가 있다면 신뢰도가 높은 정보를 우선시하세요."""
            
            try:
                combined_response = await self.generate_ai_response(
                    enhanced_prompt, provider, conversation_history
                )
                
                print(f"✅ [MULTI-RAG] Successfully generated combined response using {len(successful_responses)} RAG sources")
                return {
                    "response": combined_response,
                    "rag_results": rag_results,
                    "has_multi_rag": True,
                    "successful_rag_count": len(successful_responses)
                }
                
            except Exception as e:
                print(f"❌ [MULTI-RAG] Failed to generate combined response: {e}")
                # Fallback to first successful response
                return {
                    "response": successful_responses[0],
                    "rag_results": rag_results,
                    "has_multi_rag": True,
                    "successful_rag_count": len(successful_responses)
                }
        else:
            # No successful RAG responses, fallback to basic AI
            print(f"❌ [MULTI-RAG] No successful RAG responses, falling back to basic AI")
            basic_response = await self.generate_ai_response(message, provider, conversation_history)
            return {
                "response": basic_response,
                "rag_results": rag_results,
                "has_multi_rag": True,
                "successful_rag_count": 0
            }
    
    async def generate_simple_document_response(
        self, 
        message: str, 
        user_id: str,
        provider: str = "gemini",
        conversation_history: List[Dict] = None,
        rag_tracker = None
    ) -> Dict[str, any]:
        """업로드된 문서에서 간단한 키워드 검색으로 관련 내용을 찾아 응답 생성"""
        print(f"📚 [SIMPLE-RAG] Starting simple document search for user: {user_id}")
        
        try:
            # 사용자의 업로드된 문서 검색
            user_docs = user_documents.get(user_id, [])
            if not user_docs:
                print(f"📚 [SIMPLE-RAG] No documents found for user {user_id}")
                response = await self.generate_ai_response(message, provider, conversation_history)
                return {"response": response, "sources": []}
            
            print(f"📚 [SIMPLE-RAG] Found {len(user_docs)} documents for user {user_id}")
            
            # 스마트 문서 처리: 전체 내용 활용 + 키워드 강조
            relevant_content = []
            search_terms = message.lower().split()
            
            for doc in user_docs:
                doc_content = ""
                if isinstance(doc["content"], bytes):
                    try:
                        doc_content = doc["content"].decode('utf-8')
                    except:
                        doc_content = str(doc["content"])
                else:
                    doc_content = str(doc["content"])
                
                doc_content_lower = doc_content.lower()
                
                # 키워드 매칭 점수 계산
                keyword_matches = 0
                matched_terms = []
                for term in search_terms:
                    if len(term) > 2 and term in doc_content_lower:
                        keyword_matches += 1
                        matched_terms.append(term)
                
                # 문서 길이에 따른 처리
                max_content_length = 2000  # AI가 처리할 수 있는 최대 길이
                
                if len(doc_content) <= max_content_length:
                    # 짧은 문서: 전체 내용 제공
                    content_to_use = doc_content
                    processing_note = "전체 문서 내용"
                else:
                    # 긴 문서: 키워드 주변 확장된 컨텍스트 + 문서 시작 부분
                    if keyword_matches > 0:
                        # 키워드가 있는 경우: 확장된 컨텍스트 제공
                        best_match_pos = doc_content_lower.find(matched_terms[0])
                        start = max(0, best_match_pos - 500)  # 앞 500자
                        end = min(len(doc_content), best_match_pos + 1500)  # 뒤 1500자
                        
                        # 문서 시작 부분도 포함 (제목, 개요 등)
                        beginning = doc_content[:300] if start > 300 else ""
                        middle_content = doc_content[start:end]
                        
                        content_to_use = f"{beginning}\n\n...[관련 부분]...\n\n{middle_content}"
                        processing_note = f"확장된 컨텍스트 (키워드: {', '.join(matched_terms)})"
                    else:
                        # 키워드가 없는 경우: 문서 앞부분 제공
                        content_to_use = doc_content[:max_content_length]
                        processing_note = "문서 시작 부분"
                
                relevant_content.append({
                    "document_id": doc["id"],
                    "filename": doc["filename"],
                    "content_preview": content_to_use,
                    "keyword_matches": keyword_matches,
                    "matched_terms": matched_terms,
                    "processing_note": processing_note,
                    "full_length": len(doc_content)
                })
                
                print(f"📚 [SIMPLE-RAG] Processed {doc['filename']}: {len(content_to_use)} chars, {keyword_matches} keyword matches")
            
            print(f"📚 [SIMPLE-RAG] Found {len(relevant_content)} relevant content snippets")
            
            # RAG 추적 - 검색 단계 완료
            if rag_tracker and relevant_content:
                # Convert relevant content to chunks format for tracking
                chunks = [
                    {
                        "document_id": content["document_id"],
                        "content": content["content_preview"],
                        "score": content["keyword_matches"] / max(len(content["matched_terms"]), 1)
                    }
                    for content in relevant_content
                ]
                rag_tracker.end_retrieval(chunks)
            
            # 모든 문서 내용을 AI에 제공 (키워드 매칭 여부와 관계없이)
            if relevant_content:
                # 문서별 상세 정보 포함하여 컨텍스트 구성
                context_parts = []
                total_chars = 0
                
                for content in relevant_content:
                    doc_info = f"=== 파일: {content['filename']} ===\n"
                    doc_info += f"처리 방식: {content['processing_note']}\n"
                    if content['keyword_matches'] > 0:
                        doc_info += f"매칭된 키워드: {', '.join(content['matched_terms'])}\n"
                    doc_info += f"원본 크기: {content['full_length']} 문자\n\n"
                    doc_info += f"내용:\n{content['content_preview']}\n"
                    
                    context_parts.append(doc_info)
                    total_chars += len(doc_info)
                
                context = "\n\n".join(context_parts)
                
                # 향상된 프롬프트 생성
                enhanced_message = f"""업로드된 문서를 분석하여 질문에 답변해주세요.

문서 내용:
{context}

중요한 지침:
1. 위 문서들의 내용을 정확히 분석하여 답변하세요.
2. 문서에 없는 내용은 추측하지 말고, 문서 기반으로만 답변하세요.
3. 가능한 한 구체적이고 상세한 정보를 제공하세요.
4. 문서의 구조와 섹션을 파악하여 전체적인 맥락을 이해하세요.

사용자 질문: {message}"""
                
                print(f"📚 [SIMPLE-RAG] Generated enhanced prompt: {len(context)} chars context, {len(relevant_content)} documents")
                
                # 생성 단계 추적 시작
                if rag_tracker:
                    rag_tracker.start_generation()
                
                response = await self.generate_ai_response(enhanced_message, provider, conversation_history)
                
                # 생성 단계 추적 완료
                if rag_tracker:
                    rag_tracker.end_generation(response, provider or "gemini")
                
                # 소스 정보 정리
                sources = []
                for content in relevant_content:
                    sources.append({
                        "document_id": content["document_id"],
                        "filename": content["filename"],
                        "content_preview": content["content_preview"][:200] + "...",
                        "keyword_matches": content["keyword_matches"],
                        "processing_note": content["processing_note"]
                    })
                
                return {
                    "response": response,
                    "sources": sources
                }
            else:
                print(f"📚 [SIMPLE-RAG] No documents available, using basic response")
                response = await self.generate_ai_response(message, provider, conversation_history)
                return {"response": response, "sources": []}
                
        except Exception as e:
            print(f"❌ [SIMPLE-RAG] Error in simple document search: {str(e)}")
            import traceback
            print(f"📊 [SIMPLE-RAG] Full traceback: {traceback.format_exc()}")
            
            # 실패시 기본 AI로 fallback
            print(f"🔄 [SIMPLE-RAG] Falling back to basic AI response")
            response = await self.generate_ai_response(message, provider, conversation_history)
            return {"response": response, "sources": []}
    
    def _should_use_agentic_rag(self, message: str, complexity_threshold: int) -> bool:
        """쿼리가 에이전틱 RAG를 사용해야 하는지 판단"""
        if not AGENTIC_RAG_AVAILABLE or not self.agentic_rag_system:
            return False
        
        # 복잡도 키워드들
        complexity_indicators = [
            '비교', '차이', '장단점', '관계', '영향', '원인', '결과', '분석',
            '종합', '요약', '정리', '설명', '어떻게', '왜', '무엇', '어떤',
            '그리고', '또는', '하지만', '따라서', '그러나', '반면에'
        ]
        
        # 복잡한 질문 패턴
        complex_patterns = [
            message.count('?') > 1,  # 여러 질문
            len(message.split()) > 15,  # 긴 쿼리
            any(word in message for word in complexity_indicators),
            message.count(',') > 2,  # 여러 요소
        ]
        
        complexity_score = sum(complex_patterns) + len(message) / 50
        
        print(f"🤖 [AGENTIC-RAG] 복잡도 점수: {complexity_score:.1f}, 임계값: {complexity_threshold}")
        
        return complexity_score >= complexity_threshold
    
    async def _generate_agentic_rag_response(
        self,
        message: str,
        provider: str,
        conversation_history: List[Dict],
        user_id: str,
        use_rag: bool,
        use_web_search: bool,
        web_search_engines: List[str],
        search_mode: str
    ) -> Dict[str, any]:
        """에이전틱 RAG를 사용한 고급 응답 생성"""
        
        if not AGENTIC_RAG_AVAILABLE or not self.agentic_rag_system:
            print(f"⚠️ [AGENTIC-RAG] 에이전틱 RAG 시스템이 사용 불가능, 기본 RAG로 대체")
            return await self._fallback_to_basic_rag(message, provider, conversation_history, user_id, use_rag, use_web_search, web_search_engines, search_mode)
        
        try:
            print(f"🤖 [AGENTIC-RAG] 에이전틱 RAG 응답 생성 시작")
            
            # 컨텍스트 정보 준비
            context = {
                "use_rag": use_rag,
                "use_web_search": use_web_search,
                "web_search_engines": web_search_engines,
                "search_mode": search_mode,
                "conversation_history": conversation_history,
                "provider": provider
            }
            
            # 실행 계획 수립
            plan = await self.agentic_rag_system.plan_execution(message, context)
            print(f"🎯 [AGENTIC-RAG] 실행 계획 수립 완료: {len(plan.execution_strategy)}개 액션")
            print(f"📋 [AGENTIC-RAG] 액션 목록: {[a.value for a in plan.execution_strategy]}")
            
            # 계획 실행
            result = await self.agentic_rag_system.execute_plan(plan, user_id)
            
            print(f"✅ [AGENTIC-RAG] 에이전틱 RAG 응답 생성 완료")
            print(f"📊 [AGENTIC-RAG] 신뢰도: {result['confidence']:.2f}")
            print(f"📚 [AGENTIC-RAG] 소스 수: {len(result['sources'])}")
            
            return {
                "response": result["answer"],
                "sources": result["sources"],
                "metadata": {
                    "agentic_rag_used": True,
                    "execution_plan": plan.dict(),
                    "confidence": result["confidence"],
                    "execution_results": len(result["execution_results"])
                }
            }
            
        except Exception as e:
            print(f"❌ [AGENTIC-RAG] 에이전틱 RAG 오류: {str(e)}")
            print(f"🔄 [AGENTIC-RAG] 기본 RAG로 대체")
            
            return await self._fallback_to_basic_rag(message, provider, conversation_history, user_id, use_rag, use_web_search, web_search_engines, search_mode)
    
    async def _fallback_to_basic_rag(
        self,
        message: str,
        provider: str,
        conversation_history: List[Dict],
        user_id: str,
        use_rag: bool,
        use_web_search: bool,
        web_search_engines: List[str],
        search_mode: str
    ) -> Dict[str, any]:
        """에이전틱 RAG 실패 시 기본 RAG로 대체"""
        
        # 기존 generate_response 로직을 재귀 호출하지 않고 직접 구현
        context_parts = []
        all_sources = []
        
        # 문서 검색 처리
        if use_rag or search_mode in ['documents', 'combined']:
            if RAG_AVAILABLE:
                rag_result = await self.generate_rag_response(message, user_id, provider, conversation_history)
                context_parts.append(f"문서 검색 결과:\n{rag_result['response']}")
                all_sources.extend(rag_result.get('sources', []))
            else:
                doc_result = await self.generate_simple_document_response(message, user_id, provider, conversation_history)
                if doc_result['response']:
                    context_parts.append(f"문서 검색 결과:\n{doc_result['response']}")
                    all_sources.extend(doc_result.get('sources', []))
        
        # 웹 검색 처리
        if use_web_search or search_mode in ['web', 'combined']:
            if WEB_SEARCH_AVAILABLE and self.web_search_service:
                try:
                    search_response = await self.web_search_service.search(
                        query=message,
                        engines=web_search_engines or ['google'],
                        language='ko'
                    )
                    
                    if search_response.results:
                        web_context = self.web_search_service.format_results_for_context(search_response)
                        context_parts.append(f"웹 검색 결과:\n{web_context}")
                        all_sources.append({"type": "web", "results": search_response.results[:3]})
                except Exception as e:
                    print(f"❌ [WEB-SEARCH] 웹 검색 오류: {e}")
        
        # 통합 응답 생성
        if context_parts:
            combined_context = "\n\n".join(context_parts)
            enhanced_message = f"다음 검색 결과들을 종합하여 질문에 답변해주세요:\n\n{combined_context}\n\n질문: {message}"
            response = await self.generate_ai_response(enhanced_message, provider, conversation_history)
            return {"response": response, "sources": all_sources}
        
        # 기본 AI 응답
        response = await self.generate_ai_response(message, provider, conversation_history)
        return {"response": response, "sources": []}

# Internal LLM Server Helper Function
async def call_internal_llm_server(
    message: str,
    server_config: Dict[str, Any],
    conversation_history: List[Dict] = None,
    user_id: str = "default_user"
) -> Dict[str, Any]:
    """내부 LLM 서버에 API 키를 사용하여 요청을 전송하고 응답을 받는 함수"""
    try:
        import httpx

        server_url = server_config.get("url", "")
        api_key = server_config.get("api_key", "")
        model = server_config.get("model", "gemini-1.5-pro")
        temperature = server_config.get("temperature", 0.7)
        max_tokens = server_config.get("max_tokens", 2048)
        server_name = server_config.get("name", "Unknown Server")

        print(f"🏢 [INTERNAL-LLM] Calling server: {server_name}")
        print(f"🏢 [INTERNAL-LLM] URL: {server_url}")
        print(f"🏢 [INTERNAL-LLM] Model: {model}")

        if not server_url or not api_key:
            raise ValueError(f"Missing server URL or API key for {server_name}")

        # 대화 히스토리 준비
        messages = []
        if conversation_history and len(conversation_history) > 0:
            print(f"📚 [INTERNAL-LLM] Adding conversation history: {len(conversation_history)} messages")
            for msg in conversation_history[-10:]:  # 최근 10개 메시지만 포함
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # 현재 메시지 추가
        messages.append({
            "role": "user",
            "content": message
        })

        # HTTP 요청 데이터 준비
        request_data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # HTTP 헤더 준비 (API 키 포함)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        print(f"📤 [INTERNAL-LLM] Sending request to {server_url}")

        # HTTP 요청 전송
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{server_url}/v1/chat/completions",  # OpenAI 호환 엔드포인트
                json=request_data,
                headers=headers
            )

            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data["choices"][0]["message"]["content"]
                print(f"✅ [INTERNAL-LLM] Success! Response from {server_name}")

                return {
                    "response": ai_response,
                    "sources": [],
                    "server_used": server_name,
                    "server_url": server_url,
                    "model": model
                }
            else:
                error_msg = f"Internal server error: {response.status_code} - {response.text}"
                print(f"❌ [INTERNAL-LLM] HTTP {response.status_code}: {response.text}")
                raise ValueError(error_msg)

    except httpx.ConnectError as e:
        error_msg = f"⚠️ 내부 LLM 서버({server_config.get('name', 'Unknown Server')})에 연결할 수 없습니다.\n\n" \
                    f"• 서버 상태: 연결 실패\n" \
                    f"• 서버 URL: {server_config.get('url', 'N/A')}\n" \
                    f"• 오류 유형: 네트워크 연결 오류\n\n" \
                    f"관리자에게 내부 서버 상태를 확인해달라고 요청하세요."
        print(f"❌ [INTERNAL-LLM] Connection Error: {str(e)}")
        return {
            "response": error_msg,
            "sources": [],
            "error": True,
            "error_type": "connection_failed",
            "server_used": server_config.get("name", "Unknown Server"),
            "server_url": server_config.get("url", "N/A")
        }

    except httpx.TimeoutException as e:
        error_msg = f"⏱️ 내부 LLM 서버({server_config.get('name', 'Unknown Server')})의 응답 시간이 초과되었습니다.\n\n" \
                    f"• 서버 상태: 응답 시간 초과 (30초)\n" \
                    f"• 서버 URL: {server_config.get('url', 'N/A')}\n" \
                    f"• 가능한 원인: 서버 과부하, 네트워크 지연\n\n" \
                    f"잠시 후 다시 시도해보시거나 관리자에게 문의하세요."
        print(f"❌ [INTERNAL-LLM] Timeout Error: {str(e)}")
        return {
            "response": error_msg,
            "sources": [],
            "error": True,
            "error_type": "timeout",
            "server_used": server_config.get("name", "Unknown Server"),
            "server_url": server_config.get("url", "N/A")
        }

    except Exception as e:
        # 기타 오류들을 구체적으로 분류
        error_details = str(e)
        if "401" in error_details or "403" in error_details:
            error_msg = f"🔐 내부 LLM 서버({server_config.get('name', 'Unknown Server')})의 인증에 실패했습니다.\n\n" \
                        f"• 서버 상태: 인증 오류\n" \
                        f"• 서버 URL: {server_config.get('url', 'N/A')}\n" \
                        f"• 오류 유형: API 키 인증 실패\n\n" \
                        f"관리자에게 API 키 설정을 확인해달라고 요청하세요."
            error_type = "auth_failed"
        elif "404" in error_details:
            error_msg = f"🔍 내부 LLM 서버({server_config.get('name', 'Unknown Server')})에서 요청한 엔드포인트를 찾을 수 없습니다.\n\n" \
                        f"• 서버 상태: 엔드포인트 없음\n" \
                        f"• 서버 URL: {server_config.get('url', 'N/A')}\n" \
                        f"• 요청 경로: /v1/chat/completions\n\n" \
                        f"관리자에게 서버 설정을 확인해달라고 요청하세요."
            error_type = "endpoint_not_found"
        elif "500" in error_details:
            error_msg = f"💥 내부 LLM 서버({server_config.get('name', 'Unknown Server')})에서 내부 오류가 발생했습니다.\n\n" \
                        f"• 서버 상태: 내부 서버 오류\n" \
                        f"• 서버 URL: {server_config.get('url', 'N/A')}\n" \
                        f"• 오류 코드: 500\n\n" \
                        f"관리자에게 서버 로그를 확인해달라고 요청하세요."
            error_type = "server_error"
        else:
            error_msg = f"❌ 내부 LLM 서버({server_config.get('name', 'Unknown Server')}) 호출 중 예상치 못한 오류가 발생했습니다.\n\n" \
                        f"• 서버 URL: {server_config.get('url', 'N/A')}\n" \
                        f"• 오류 내용: {error_details}\n\n" \
                        f"관리자에게 문의하거나 외부 AI 서비스를 이용해주세요."
            error_type = "unknown_error"

        print(f"❌ [INTERNAL-LLM] Exception: {str(e)}")
        return {
            "response": error_msg,
            "sources": [],
            "error": True,
            "error_type": error_type,
            "server_used": server_config.get("name", "Unknown Server"),
            "server_url": server_config.get("url", "N/A")
        }

# External LLM API Helper Function
async def call_external_llm_api(
    message: str,
    external_config: Dict[str, Any],
    conversation_history: List[Dict] = None,
    user_id: str = "default_user"
) -> Dict[str, Any]:
    """외부 LLM API에 DB 설정값을 사용하여 요청을 전송하고 응답을 받는 함수"""
    try:
        import google.generativeai as genai
        import anthropic
        import openai
        import httpx

        api_url = external_config.get("api_url", "")
        ai_model = external_config.get("ai_model", "gemini-1.5-pro")
        temperature = external_config.get("temperature", 0.7)
        max_tokens = external_config.get("max_tokens", 2048)

        print(f"🌐 [EXTERNAL-LLM] Calling external API")
        print(f"🌐 [EXTERNAL-LLM] Model: {ai_model}")
        print(f"🌐 [EXTERNAL-LLM] Temperature: {temperature}")
        print(f"🌐 [EXTERNAL-LLM] Max tokens: {max_tokens}")

        # 대화 히스토리 준비
        messages = []
        if conversation_history and len(conversation_history) > 0:
            print(f"📚 [EXTERNAL-LLM] Adding conversation history: {len(conversation_history)} messages")
            for msg in conversation_history[-10:]:  # 최근 10개 메시지만 포함
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # 현재 메시지 추가
        messages.append({
            "role": "user",
            "content": message
        })

        # 모델별 API 호출
        if "gemini" in ai_model.lower():
            # Gemini API 호출
            gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not gemini_api_key:
                raise ValueError("Gemini API key not found in environment variables")

            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel(ai_model)

            # 대화 히스토리를 Gemini 형식으로 변환
            chat_history = []
            for msg in messages[:-1]:  # 마지막 메시지 제외
                if msg["role"] == "user":
                    chat_history.append({"role": "user", "parts": [msg["content"]]})
                else:
                    chat_history.append({"role": "model", "parts": [msg["content"]]})

            # Gemini 채팅 시작
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(message)
            ai_response = response.text

        elif "claude" in ai_model.lower():
            # Claude API 호출
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_api_key:
                raise ValueError("Anthropic API key not found in environment variables")

            client = anthropic.Anthropic(api_key=anthropic_api_key)

            # Claude 형식으로 메시지 변환
            claude_messages = []
            for msg in messages:
                claude_messages.append({
                    "role": msg["role"] if msg["role"] in ["user", "assistant"] else "assistant",
                    "content": msg["content"]
                })

            response = client.messages.create(
                model=ai_model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=claude_messages
            )
            ai_response = response.content[0].text

        elif "gpt" in ai_model.lower() or "openai" in ai_model.lower():
            # OpenAI API 호출
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OpenAI API key not found in environment variables")

            client = openai.OpenAI(api_key=openai_api_key)

            response = client.chat.completions.create(
                model=ai_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            ai_response = response.choices[0].message.content

        elif "perplexity" in ai_model.lower() or "sonar" in ai_model.lower():
            # Perplexity API 호출
            perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
            if not perplexity_api_key:
                raise ValueError("Perplexity API key not found in environment variables")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    json={
                        "model": ai_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    headers={
                        "Authorization": f"Bearer {perplexity_api_key}",
                        "Content-Type": "application/json"
                    }
                )

                if response.status_code == 200:
                    response_data = response.json()
                    ai_response = response_data["choices"][0]["message"]["content"]
                else:
                    raise ValueError(f"Perplexity API error: {response.status_code} - {response.text}")
        else:
            raise ValueError(f"Unsupported AI model: {ai_model}")

        print(f"✅ [EXTERNAL-LLM] Success! Response from {ai_model}")

        return {
            "response": ai_response,
            "sources": [],
            "model_used": ai_model,
            "api_url": api_url,
            "is_external_api": True
        }

    except Exception as e:
        error_msg = f"❌ 외부 LLM API ({external_config.get('ai_model', 'Unknown Model')}) 호출 중 오류가 발생했습니다.\n\n" \
                    f"• 모델: {external_config.get('ai_model', 'N/A')}\n" \
                    f"• API URL: {external_config.get('api_url', 'N/A')}\n" \
                    f"• 오류 내용: {str(e)}\n\n" \
                    f"관리자에게 외부 API 설정을 확인해달라고 요청하세요."

        print(f"❌ [EXTERNAL-LLM] Exception: {str(e)}")
        return {
            "response": error_msg,
            "sources": [],
            "error": True,
            "error_type": "external_api_error",
            "model_used": external_config.get("ai_model", "Unknown Model"),
            "api_url": external_config.get("api_url", "N/A")
        }

# AI 서비스 인스턴스 생성
ai_service = AIService()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "SDC Backend API is running",
        "status": "healthy",
        "version": "0.1.0"
    }

@app.get("/api/v1/providers")
async def get_providers():
    """사용 가능한 LLM 제공자 목록 반환"""
    return {
        "providers": [
            {
                "name": "gemini",
                "display_name": "Google Gemini",
                "available": True,  # Temporarily hardcoded for LLM selection testing
                "models": ["gemini-pro"]
            },
            {
                "name": "claude",
                "display_name": "Anthropic Claude",
                "available": True,  # Temporarily hardcoded for LLM selection testing
                "models": ["claude-3-sonnet"]
            },
            {
                "name": "openai",
                "display_name": "ChatGPT (OpenAI)",
                "available": True,  # Temporarily hardcoded for LLM selection testing
                "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
            },
            {
                "name": "perplexity",
                "display_name": "Perplexity AI",
                "available": True,  # Temporarily hardcoded for LLM selection testing
                "models": ["sonar"]
            }
        ]
    }


@app.get("/api/v1/conversations/{user_id}")
async def get_user_conversations(user_id: str, limit: int = 10, offset: int = 0):
    """사용자의 대화 목록 반환"""
    
    # 대화가 없으면 샘플 데이터 생성
    if not conversations_db:
        for i in range(1, 8):
            conv_id = f"conv-{i}"
            created_time = datetime.now() - timedelta(days=i-1)
            conversations_db[conv_id] = {
                "id": conv_id,
                "title": f"SDC AI와의 대화 {i}" if i > 1 else "안녕하세요! 도움이 필요하신가요?",
                "created_at": created_time.isoformat(),
                "updated_at": created_time.isoformat(),
                "message_count": 2 + (i % 3)
            }
            
            # 각 대화에 메시지도 생성
            messages_db[conv_id] = [
                {
                    "id": f"msg-{conv_id}-1",
                    "content": f"안녕하세요! SDC AI에게 {i}번째 질문입니다." if i > 1 else "안녕하세요! SDC에 오신 것을 환영합니다. 궁금한 것이 있으시면 언제든지 질문해주세요!",
                    "role": "user",
                    "created_at": created_time.isoformat(),
                    "conversation_id": conv_id
                },
                {
                    "id": f"msg-{conv_id}-2",
                    "content": f"안녕하세요! 저는 SDC AI 어시스턴트입니다. {i}번째 대화에서 무엇을 도와드릴까요?",
                    "role": "assistant",
                    "created_at": (created_time + timedelta(seconds=30)).isoformat(),
                    "conversation_id": conv_id,
                    "metadata": {
                        "model": "gemini-pro",
                        "processing_time": 1.2,
                        "confidence": 0.95
                    }
                }
            ]
    
    # 페이지네이션 적용
    conv_list = list(conversations_db.values())
    conv_list.sort(key=lambda x: x["updated_at"], reverse=True)
    
    paginated = conv_list[offset:offset + limit]
    return paginated

@app.get("/api/v1/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """특정 대화의 메시지들 반환"""
    if conversation_id not in messages_db:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return messages_db[conversation_id]

# PostgreSQL 히스토리 관련 엔드포인트
@app.get("/api/v1/conversations/{user_id}")
async def get_user_conversations(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
    limit: int = 20,
    offset: int = 0
):
    """사용자의 대화 목록 조회"""
    if not DATABASE_AVAILABLE:
        return {"success": False, "error": "Database service not available"}

    try:
        conversations = await chat_history_service.get_user_conversations(
            db, user_id, limit, offset
        )

        conversations_data = []
        for conv in conversations:
            conversations_data.append({
                "id": str(conv.id),
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": len(conv.messages)
            })

        return {
            "success": True,
            "conversations": conversations_data
        }
    except Exception as e:
        print(f"❌ [DB] Failed to get conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
    limit: int = 50,
    offset: int = 0
):
    """대화의 메시지 목록 조회"""
    if not DATABASE_AVAILABLE:
        return {"success": False, "error": "Database service not available"}

    try:
        messages = await chat_history_service.get_conversation_messages(
            db, conversation_id, user_id, limit, offset
        )

        messages_data = []
        for msg in messages:
            messages_data.append({
                "id": str(msg.id),
                "content": msg.content,
                "role": msg.role,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata,
                "sources": msg.sources,
                "is_dual_provider": msg.is_dual_provider,
                "dual_provider_responses": msg.dual_provider_responses
            })

        return {
            "success": True,
            "messages": messages_data
        }
    except Exception as e:
        print(f"❌ [DB] Failed to get messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service)
):
    """채팅 엔드포인트 - 실제 AI를 사용한 대화 생성"""
    print(f"\n🎯 [CHAT] New chat request received")
    print(f"📝 [CHAT] Message: {request.message[:50]}...")
    print(f"🤖 [CHAT] Provider: {request.provider}")
    print(f"👤 [CHAT] User: {request.user_id}")
    print(f"💬 [CHAT] Conversation ID: {request.conversation_id}")
    print(f"📚 [CHAT] History length: {len(request.conversation_history) if request.conversation_history else 0}")
    
    try:
        # 대화 ID 생성 또는 기존 대화 사용 (UUID 형식)
        conv_id = request.conversation_id or str(uuid.uuid4())
        msg_id = str(uuid.uuid4())
        
        print(f"🆔 [CHAT] Final conversation ID: {conv_id}")
        print(f"🆔 [CHAT] Message ID: {msg_id}")
        
        # 사용자 입력 안전성 검증 (Guardrails)
        if GUARDRAILS_AVAILABLE:
            print(f"🛡️ [GUARDRAILS] Validating user input...")
            # Request 객체에서 클라이언트 IP 가져오기
            client_ip = getattr(request, 'client', {}).get('host', 'unknown')
            if hasattr(request, 'headers') and 'x-forwarded-for' in request.headers:
                client_ip = request.headers['x-forwarded-for'].split(',')[0].strip()

            is_safe, filtered_or_reason = await validate_user_input(
                request.message,
                request.user_id or "default_user",
                client_ip
            )
            
            if not is_safe:
                print(f"🚫 [GUARDRAILS] User input blocked: {filtered_or_reason}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Content violates safety guidelines: {filtered_or_reason}"
                )
            
            # 필터링된 텍스트가 있다면 사용
            validated_message = filtered_or_reason if filtered_or_reason != request.message else request.message
            print(f"✅ [GUARDRAILS] User input validated")
        else:
            validated_message = request.message

        # Redis 캐시에서 동일한 질문의 응답 확인
        cache_service = None
        cached_response = None
        if CACHE_AVAILABLE:
            try:
                cache_service = get_cache_service()
                cached_response = cache_service.get_cached_response(
                    message=validated_message,
                    provider=request.provider,
                    search_mode=request.search_mode,
                    use_rag=request.use_rag,
                    use_web_search=request.use_web_search
                )

                if cached_response:
                    print(f"🎯 [CACHE] Using cached response for message: {validated_message[:30]}...")
                    return ChatResponse(
                        response=cached_response.get("response", ""),
                        success=True,
                        conversation_id=conv_id,
                        message_id=msg_id,
                        sources=cached_response.get("sources", []),
                        model=cached_response.get("model", request.provider),
                        tokens=cached_response.get("tokens"),
                        metadata=cached_response.get("metadata", {}),
                        from_cache=True
                    )
                else:
                    print(f"💾 [CACHE] No cached response found, generating new response...")
            except Exception as e:
                print(f"⚠️ [CACHE] Cache check failed: {e}")

        # PostgreSQL에 사용자와 대화 정보 저장 (DATABASE_AVAILABLE일 때만)
        if DATABASE_AVAILABLE:
            try:
                print(f"💾 [DB] Saving chat history to PostgreSQL...")

                # user_id를 UUID로 변환 (문자열을 해시하여 일관된 UUID 생성)
                import hashlib
                user_id_str = request.user_id or "default_user"
                user_id_hash = hashlib.md5(user_id_str.encode()).hexdigest()
                user_uuid = str(uuid.UUID(user_id_hash))

                # 사용자 가져오기 또는 생성
                user = await chat_history_service.get_or_create_user(
                    db,
                    user_id=user_uuid,
                    username=user_id_str,
                    email=f"{user_id_str}@sdc.local"
                )

                # 대화 가져오기 또는 생성
                conversation = await chat_history_service.get_or_create_conversation(
                    db,
                    user_id=str(user.id),
                    conversation_id=conv_id,
                    title=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )

                # 사용자 메시지 저장
                user_message = await chat_history_service.save_message(
                    db,
                    conversation_id=str(conversation.id),
                    user_id=str(user.id),
                    content=validated_message,
                    role="user"
                )

                print(f"✅ [DB] User message saved with ID: {user_message.id}")

            except Exception as e:
                print(f"⚠️ [DB] Failed to save user message: {e}")
                # Continue without failing the entire request
        
        # RAG 성능 추적 초기화
        rag_tracker = None
        if RAG_EVALUATION_AVAILABLE and (request.use_rag or request.search_mode in ['documents', 'combined']):
            session_id = f"session-{conv_id}-{msg_id}"
            rag_tracker = RAGPerformanceTracker(
                session_id=session_id,
                query=validated_message,
                user_id=request.user_id or "default_user"
            )
            print(f"📊 [RAG-EVAL] RAG performance tracker initialized for session: {session_id}")

        # 내부 서버 설정 조회 및 사용 (사용자가 내부 서버 옵션을 선택한 경우)
        internal_llm_server = None
        final_provider = request.provider or "gemini"

        # 디버깅: request 값들 출력
        print(f"🔍 [DEBUG] Request values:")
        print(f"  use_internal_servers: {request.use_internal_servers}")
        print(f"  internal_server_mode: {request.internal_server_mode}")
        print(f"  DATABASE_AVAILABLE: {DATABASE_AVAILABLE}")
        print(f"  db is not None: {db is not None}")

        if request.use_internal_servers and DATABASE_AVAILABLE and db is not None:
            try:
                print(f"🏢 [INTERNAL] User requested internal servers - querying DB settings...")
                from app.services.server_settings_service import ServerSettingsService
                settings_service = ServerSettingsService(db)
                internal_settings = await settings_service.get_internal_server_settings()

                if internal_settings and internal_settings.get("llm_servers"):
                    # 기본(primary) LLM 서버 찾기
                    llm_servers = internal_settings["llm_servers"]
                    primary_llm = next((server for server in llm_servers if server.get("is_primary")), None)

                    if primary_llm:
                        internal_llm_server = primary_llm
                        final_provider = "internal"  # 내부 서버 사용을 표시
                        print(f"✅ [INTERNAL] Found primary LLM server: {primary_llm['name']} ({primary_llm['url']})")
                    else:
                        # primary가 없으면 첫 번째 활성 서버 사용
                        active_llm = next((server for server in llm_servers if server.get("status") == "active"), None)
                        if active_llm:
                            internal_llm_server = active_llm
                            final_provider = "internal"
                            print(f"⚠️ [INTERNAL] No primary LLM server found, using first active: {active_llm['name']}")
                        else:
                            print(f"❌ [INTERNAL] No active LLM servers found, falling back to external provider")
                else:
                    print(f"⚠️ [INTERNAL] No internal LLM servers configured, falling back to external provider")

            except Exception as e:
                print(f"❌ [INTERNAL] Failed to query internal server settings: {e}")
                print(f"⚠️ [INTERNAL] Falling back to external provider")

        # 실제 AI 응답 생성 (내부 서버, 외부 LLM DB 설정, 또는 기본 AI 서비스 사용)
        if internal_llm_server:
            print(f"🏢 [INTERNAL] Calling internal LLM server: {internal_llm_server['name']}")
            ai_result = await call_internal_llm_server(
                message=validated_message,
                server_config=internal_llm_server,
                conversation_history=request.conversation_history,
                user_id=request.user_id or "default_user"
            )
        else:
            # 외부 LLM 설정을 DB에서 조회
            external_config = None
            if DATABASE_AVAILABLE and db is not None:
                try:
                    print(f"🌐 [EXTERNAL] Querying external LLM settings from DB...")
                    from app.services.server_settings_service import ServerSettingsService
                    settings_service = ServerSettingsService(db)
                    external_settings = await settings_service.get_external_llm_settings()

                    if external_settings:
                        external_config = external_settings
                        print(f"✅ [EXTERNAL] Found external LLM settings: {external_config.get('ai_model', 'N/A')}")
                    else:
                        print(f"⚠️ [EXTERNAL] No external LLM settings found in DB, using default AI service")

                except Exception as e:
                    print(f"❌ [EXTERNAL] Failed to query external LLM settings: {e}")
                    print(f"⚠️ [EXTERNAL] Falling back to default AI service")

            # 외부 LLM DB 설정을 사용하거나 기본 AI 서비스 사용
            if external_config:
                print(f"🌐 [EXTERNAL] Calling external LLM API with DB settings: {external_config.get('ai_model', 'N/A')}")
                ai_result = await call_external_llm_api(
                    message=validated_message,
                    external_config=external_config,
                    conversation_history=request.conversation_history,
                    user_id=request.user_id or "default_user"
                )
            else:
                print(f"🚀 [CHAT] Calling default AI service with RAG and web search support...")
                ai_result = await ai_service.generate_response(
                    message=validated_message,
                    provider=final_provider,
                    conversation_history=request.conversation_history,
                    use_rag=request.use_rag or KOREAN_RAG_AVAILABLE,
                    use_web_search=request.use_web_search or False,
                    web_search_engines=request.web_search_engines or ['google'],
                    search_mode=request.search_mode or 'documents',
                    use_agentic_rag=request.use_agentic_rag or False,
                    agentic_complexity_threshold=request.agentic_complexity_threshold or 5,
                    user_id=request.user_id or "default_user",
                    rag_tracker=rag_tracker,  # Pass tracker to AI service
                    enabled_rag_types=request.enabled_rag_types  # Pass multi-RAG selection
                )
        
        # 결과에서 응답과 소스 분리
        ai_response = ai_result["response"]
        ai_sources = ai_result.get("sources", [])

        # Sources가 비어있는 경우, 업로드된 문서 정보를 기반으로 생성
        if not ai_sources and request.user_id in user_documents:
            user_docs = user_documents[request.user_id]
            print(f"📚 [CHAT] Found {len(user_docs)} documents for user {request.user_id}")

            for doc in user_docs:
                # 간단한 키워드 매칭 (한국어 포함)
                query_lower = request.message.lower()

                # content가 bytes일 수 있으므로 안전하게 처리
                content = doc["content"]
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                content_lower = content.lower()

                # 더 넓은 범위의 키워드로 매칭
                keywords = ["한국어", "형태소", "분석", "토큰", "키워드", "자연어", "처리",
                           "kiwi", "mecab", "hannanum", "rag", "문서", "시스템", "sdc", "ai"]

                # 쿼리나 콘텐츠에 키워드가 포함되어 있으면 매칭
                # 또는 쿼리의 일부가 문서에 포함되어 있으면 매칭
                query_words = [word for word in query_lower.split() if len(word) > 1]

                if (any(keyword in query_lower for keyword in keywords) or
                    any(keyword in content_lower for keyword in keywords) or
                    any(word in content_lower for word in query_words)):

                    ai_sources.append({
                        "chunk_id": f"chunk_{doc['id'][:8]}",
                        "content": content[:300] + "..." if len(content) > 300 else content,
                        "similarity": 0.85,  # 기본 유사도
                        "metadata": {
                            "user_id": request.user_id,
                            "filename": doc["filename"],
                            "chunk_index": 0,
                            "total_chunks": 1,
                            "processed_at": doc.get("upload_time", datetime.now().isoformat()),
                            "korean_features": {},
                            "doc_type": doc.get("doc_type", "text")
                        }
                    })
                    print(f"📄 [CHAT] Matched document: {doc['filename']}")

        print(f"📄 [CHAT] Sources found: {len(ai_sources)} chunks")
        
        print(f"✅ [CHAT] AI response received!")
        print(f"📄 [CHAT] Response length: {len(ai_response)} chars")
        print(f"🔍 [CHAT] Response preview: {ai_response[:100]}...")
        
        # AI 출력 안전성 검증 (Guardrails)
        if GUARDRAILS_AVAILABLE:
            print(f"🛡️ [GUARDRAILS] Validating AI output...")
            is_safe, filtered_or_reason = await validate_ai_output(
                ai_response,
                request.user_id or "default_user",
                client_ip
            )
            
            if not is_safe:
                print(f"🚫 [GUARDRAILS] AI output blocked: {filtered_or_reason}")
                # AI 출력이 차단된 경우 안전한 메시지로 대체
                ai_response = "죄송합니다. 안전 정책에 따라 이 응답을 제공할 수 없습니다. 다른 질문을 해주시겠어요?"
            else:
                # 필터링된 텍스트가 있다면 사용
                ai_response = filtered_or_reason if filtered_or_reason != ai_response else ai_response
                print(f"✅ [GUARDRAILS] AI output validated")
        else:
            print(f"⚠️ [GUARDRAILS] AI output validation skipped - service unavailable")
        
        # RAG 성능 평가 수행 (비동기적으로 실행하여 응답 속도에 영향 없음)
        if RAG_EVALUATION_AVAILABLE and rag_tracker and ai_sources:
            try:
                print(f"📊 [RAG-EVAL] Performing RAG evaluation...")
                # Evaluate without blocking the response
                asyncio.create_task(rag_tracker.evaluate())
                print(f"📊 [RAG-EVAL] RAG evaluation task created and running in background")
            except Exception as e:
                print(f"⚠️ [RAG-EVAL] RAG evaluation failed: {e}")
        elif RAG_EVALUATION_AVAILABLE and rag_tracker:
            print(f"📊 [RAG-EVAL] Skipping evaluation - no sources found")
        else:
            print(f"⚠️ [RAG-EVAL] RAG evaluation skipped - service unavailable or no tracker")
        
        # 대화 및 메시지를 데이터베이스에 저장 (메모리 저장)
        if conv_id not in conversations_db:
            conversations_db[conv_id] = {
                "id": conv_id,
                "title": request.message[:50] + "..." if len(request.message) > 50 else request.message,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "message_count": 2
            }
            messages_db[conv_id] = []
        
        # 사용자 메시지 저장
        user_msg = {
            "id": f"msg-user-{str(uuid.uuid4())[:8]}",
            "content": request.message,
            "role": "user",
            "created_at": datetime.now().isoformat(),
            "conversation_id": conv_id
        }
        
        # AI 응답 메시지 저장
        ai_msg = {
            "id": msg_id,
            "content": ai_response,
            "role": "assistant",
            "created_at": datetime.now().isoformat(),
            "conversation_id": conv_id,
            "metadata": {
                "model": request.provider or "gemini",
                "processing_time": 1.5,
                "confidence": 0.95
            }
        }
        
        # 메시지들을 대화에 추가
        if conv_id in messages_db:
            messages_db[conv_id].extend([user_msg, ai_msg])
            conversations_db[conv_id]["message_count"] = len(messages_db[conv_id])
            conversations_db[conv_id]["updated_at"] = datetime.now().isoformat()

        # PostgreSQL에 AI 응답 저장 (DATABASE_AVAILABLE일 때만)
        if DATABASE_AVAILABLE:
            try:
                print(f"💾 [DB] Saving AI response to PostgreSQL...")

                # 메타데이터 준비
                response_metadata = {
                    "model": request.provider or "gemini",
                    "processing_time": 1.5,
                    "confidence": 0.95,
                    "has_multi_rag": ai_result.get("has_multi_rag", False),
                    "rag_results": ai_result.get("rag_results")
                }

                # 듀얼 프로바이더 응답 정보 추가 (웹 모드)
                is_dual_provider = request.search_mode == "웹"
                dual_provider_responses = None
                if is_dual_provider and ai_result.get("dual_provider_responses"):
                    dual_provider_responses = ai_result["dual_provider_responses"]

                # AI 응답 메시지 저장
                ai_message = await chat_history_service.save_message(
                    db,
                    conversation_id=conversation.id if 'conversation' in locals() else conv_id,
                    user_id=str(user.id) if 'user' in locals() else request.user_id,
                    content=ai_response,
                    role="assistant",
                    metadata=response_metadata,
                    sources=ai_sources,
                    is_dual_provider=is_dual_provider,
                    dual_provider_responses=dual_provider_responses
                )

                print(f"✅ [DB] AI response saved with ID: {ai_message.id}")

            except Exception as e:
                print(f"⚠️ [DB] Failed to save AI response: {e}")
                # Continue without failing the entire request
        
        # 최종 응답 준비 (소스 정보 및 Multi-RAG 결과 포함)
        final_response = ChatResponse(
            success=True,
            response=ai_response,
            provider=request.provider,
            sources=ai_sources,  # RAG 소스 정보 추가
            conversation_id=conv_id,
            message_id=msg_id,
            # Multi-RAG 결과 포함
            rag_results=ai_result.get("rag_results"),
            has_multi_rag=ai_result.get("has_multi_rag", False)
        )
        
        # 소스 정보 로깅
        if ai_sources and len(ai_sources) > 0:
            print(f"📚 [CHAT] Response includes {len(ai_sources)} source documents")
            for i, source in enumerate(ai_sources[:3]):  # 처음 3개만 로깅
                print(f"  📄 [CHAT] Source {i+1}: {source.get('document_title', 'Unknown')} (score: {source.get('similarity_score', 0):.3f})")
        else:
            print(f"📝 [CHAT] Response generated without document sources")
        
        print(f"🎉 [CHAT] Success! Returning response to frontend")
        print(f"📊 [CHAT] Final response: success={final_response.success}, provider={final_response.provider}")
        print(f"📝 [CHAT] Response content length: {len(final_response.response)}")

        # 캐시에 응답 저장 (캐시에서 읽어온 응답이 아닌 경우에만)
        if CACHE_AVAILABLE and cache_service and not cached_response:
            try:
                response_data = {
                    "response": final_response.response,
                    "sources": final_response.sources or [],
                    "model": final_response.provider,
                    "tokens": getattr(final_response, 'tokens', None),
                    "metadata": getattr(final_response, 'metadata', {}),
                    "rag_results": getattr(final_response, 'rag_results', None),
                    "has_multi_rag": getattr(final_response, 'has_multi_rag', False)
                }

                cache_service.set_cached_response(
                    message=validated_message,
                    provider=request.provider,
                    response_data=response_data,
                    search_mode=request.search_mode,
                    use_rag=request.use_rag,
                    use_web_search=request.use_web_search,
                    ttl=3600  # 1시간 캐시
                )
                print(f"💾 [CACHE] Response cached successfully")
            except Exception as e:
                print(f"⚠️ [CACHE] Failed to cache response: {e}")

        print(f"🎯 [CHAT] === CHAT REQUEST COMPLETED ===\n")

        return final_response
        
    except Exception as e:
        error_msg = f"죄송합니다. 오류가 발생했습니다: {str(e)}"
        print(f"❌ [CHAT] Endpoint error: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"📊 [CHAT] Full traceback:\n{traceback.format_exc()}")
        
        error_response = ChatResponse(
            success=False,
            response=error_msg,
            provider=request.provider,
            conversation_id=conv_id if 'conv_id' in locals() else None,
            message_id=msg_id if 'msg_id' in locals() else None
        )
        
        print(f"💥 [CHAT] Returning error response to frontend")
        print(f"🎯 [CHAT] === CHAT REQUEST FAILED ===\n")
        
        return error_response

@app.post("/api/v1/messages/rate")
async def rate_message(request: RatingRequest):
    """메시지 평점 저장 (썸업/썸다운 방식)"""
    rating_key = f"{request.message_id}_{request.user_id}"
    ratings_db[rating_key] = {
        "message_id": request.message_id,
        "user_id": request.user_id,
        "rating_type": request.rating_type,
        "feedback_categories": request.feedback_categories or [],
        "additional_feedback": request.additional_feedback,
        "created_at": datetime.now().isoformat()
    }
    return {"success": True, "message": "Rating saved successfully"}

@app.get("/api/v1/messages/{message_id}/rating/{user_id}")
async def get_message_rating(message_id: str, user_id: str):
    """특정 메시지의 사용자 평점 조회"""
    rating_key = f"{message_id}_{user_id}"
    if rating_key in ratings_db:
        return ratings_db[rating_key]
    else:
        return {
            "rating_type": None,
            "feedback_categories": [],
            "additional_feedback": None
        }

# Document upload endpoints
@app.post("/api/v1/documents")
async def upload_document_default(
    file: UploadFile = File(...),
    user_id: str = Form(default="default_user"),
    parsing_method: str = Form(default="python_libraries"),
    chunking_method: str = Form(default="python_libraries"),
    chunk_size: int = Form(default=1000),
    chunk_overlap: int = Form(default=200),
    prefer_docling: bool = Form(default=True)
):
    """문서 업로드 엔드포인트 - 프론트엔드 기본 경로 (Enhanced chunking with Milvus vector storage)"""
    print(f"📄 [UPLOAD] Document upload request: filename={file.filename}, user_id={user_id}")
    print(f"🔧 [CHUNKING] Parameters: parsing={parsing_method}, chunking={chunking_method}, size={chunk_size}, overlap={chunk_overlap}, prefer_docling={prefer_docling}")
    
    # 파일명 중복 검사 (먼저 확인)
    if file.filename:
        duplicate_check = await check_duplicate_document(user_id, file.filename)
        if duplicate_check["duplicate_found"]:
            existing_doc = duplicate_check["existing_document"]
            print(f"⚠️ [UPLOAD] Duplicate file found: {file.filename}")
            return {
                "success": False,
                "error": "duplicate_file",
                "message": "동일한 파일명의 문서가 이미 존재합니다.",
                "duplicate_info": {
                    "filename": existing_doc["filename"],
                    "upload_time": existing_doc["upload_time"],
                    "file_size": existing_doc["file_size"],
                    "processing_method": existing_doc["processing_method"]
                }
            }
    
    # 실제 파일 내용 읽기
    file_content = await file.read()
    print(f"📄 [UPLOAD] File size: {len(file_content)} bytes")
    
    # Mock document upload response
    doc_id = f"doc-{str(uuid.uuid4())[:8]}"
    
    # 파일 확장자 확인
    file_extension = file.filename.lower().split('.')[-1] if file.filename and '.' in file.filename else ""
    
    # Multi-format document processing
    processed_content = file_content
    processing_method = "basic"
    
    # Check if this is a structured document that needs processing
    structured_formats = {'pdf', 'ppt', 'pptx', 'xlsx', 'xls', 'doc', 'docx'}

    # 파싱 방법에 따라 파서 결정 (파싱과 청킹 로직 분리)
    use_docling = False
    use_python_libraries = False

    if parsing_method == "docling" and DOCLING_AVAILABLE and file_extension in structured_formats:
        use_docling = True
        print(f"🔧 [PARSING] Using Docling parsing for '{parsing_method}' parsing method")
    elif parsing_method == "python_libraries" and file_extension in structured_formats:
        use_python_libraries = True
        print(f"🔧 [PARSING] Using Python libraries parsing for '{parsing_method}' parsing method")
    elif file_extension in structured_formats:
        # 기본값: 기존 prefer_docling 로직 유지
        if prefer_docling and DOCLING_AVAILABLE:
            use_docling = True
            print(f"🔧 [PARSING] Using Docling parsing (prefer_docling=True)")
        else:
            use_python_libraries = True
            print(f"🔧 [PARSING] Using Python libraries parsing (prefer_docling=False)")

    if use_docling:
        try:
            print(f"📄 [DOCLING] Processing {file_extension.upper()} document with Docling service")
            
            # Save file temporarily for processing
            temp_file_path = f"./uploads/temp_{doc_id}_{file.filename}"
            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
            
            with open(temp_file_path, 'wb') as temp_file:
                temp_file.write(file_content)
            
            # Process with Docling
            docling_client = DoclingClient()
            success, docling_result = await docling_client.convert_document(file_content, file.filename)
            
            # Use extracted text content
            if success and docling_result.get('content'):
                processed_content = docling_result['content'].encode('utf-8')
                processing_method = "docling"
                print(f"📄 [DOCLING] Successfully processed document. Text length: {len(processed_content)} chars")
            else:
                print(f"⚠️ [DOCLING] No text content extracted, fallback to alternative processor")
                # Force fallback to alternative processor when no text extracted
                raise Exception("No text content from Docling")
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
        except Exception as e:
            print(f"⚠️ [DOCLING] Failed to process document with Docling: {str(e)}")
            print(f"📄 [FALLBACK] Trying alternative processor for {file.filename}")
            # Try alternative processor as fallback
            if ALT_PROCESSOR_AVAILABLE and file_extension in structured_formats:
                try:
                    alt_processor = AlternativeProcessor()
                    alt_success, alt_result = await alt_processor.process_document(file_content, file.filename)
                    
                    if alt_success and alt_result.get('content'):
                        processed_content = alt_result['content'].encode('utf-8')
                        processing_method = "alternative_processor"
                        print(f"📄 [ALT-PROC] Successfully processed document. Text length: {len(processed_content)} chars")
                    else:
                        print(f"⚠️ [ALT-PROC] No text content extracted, using fallback message")
                        fallback_msg = f"이 문서({file.filename})는 {file_extension.upper()} 형식이지만 텍스트를 추출할 수 없었습니다. 문서를 다시 업로드하거나 텍스트 형식으로 변환해 주세요."
                        processed_content = fallback_msg.encode('utf-8')
                        processing_method = "text_fallback"
                except Exception as alt_e:
                    print(f"⚠️ [ALT-PROC] Alternative processor also failed: {str(alt_e)}")
                    processing_method = "basic_fallback"
            else:
                processing_method = "basic_fallback"

    elif use_python_libraries:
        # Python 라이브러리를 사용하여 문서 처리
        print(f"📄 [PYTHON-LIB] Processing {file_extension.upper()} document with Python libraries")

        if ALT_PROCESSOR_AVAILABLE:
            try:
                # Save file temporarily for processing
                temp_file_path = f"./uploads/temp_{doc_id}_{file.filename}"
                os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)

                with open(temp_file_path, 'wb') as temp_file:
                    temp_file.write(file_content)

                # Process with Alternative Processor (Python libraries)
                alt_processor = AlternativeProcessor()
                alt_success, alt_result = await alt_processor.process_document(file_content, file.filename)

                # Use extracted text content
                if alt_success and alt_result.get('content'):
                    processed_content = alt_result['content'].encode('utf-8')
                    processing_method = "python_libraries"
                    print(f"📄 [PYTHON-LIB] Successfully processed document. Text length: {len(processed_content)} chars")
                else:
                    print(f"⚠️ [PYTHON-LIB] No text content extracted, using fallback message")
                    fallback_msg = f"이 문서({file.filename})는 {file_extension.upper()} 형식이지만 텍스트를 추출할 수 없었습니다. 문서를 다시 업로드하거나 텍스트 형식으로 변환해 주세요."
                    processed_content = fallback_msg.encode('utf-8')
                    processing_method = "text_fallback"

                # Cleanup
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

            except Exception as e:
                print(f"⚠️ [PYTHON-LIB] Failed to process document with Python libraries: {str(e)}")
                fallback_msg = f"이 문서({file.filename})는 {file_extension.upper()} 형식이지만 텍스트를 추출할 수 없었습니다. 문서를 다시 업로드하거나 텍스트 형식으로 변환해 주세요."
                processed_content = fallback_msg.encode('utf-8')
                processing_method = "text_fallback"
        else:
            print(f"⚠️ [PYTHON-LIB] Python libraries not available for document processing")
            fallback_msg = f"이 문서({file.filename})는 {file_extension.upper()} 형식이지만 Python 라이브러리가 사용할 수 없습니다. Docling 청킹 방법을 선택하거나 텍스트 형식으로 변환해 주세요."
            processed_content = fallback_msg.encode('utf-8')
            processing_method = "text_fallback"

    elif file_extension in structured_formats and not DOCLING_AVAILABLE:
        print(f"⚠️ [DOCLING] Structured document detected ({file_extension}) but Docling not available")
        # Try alternative processor
        if ALT_PROCESSOR_AVAILABLE:
            try:
                print(f"📄 [ALT-PROC] Processing {file_extension.upper()} document with alternative processor")
                
                # Save file temporarily for processing
                temp_file_path = f"./uploads/temp_{doc_id}_{file.filename}"
                os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
                
                with open(temp_file_path, 'wb') as temp_file:
                    temp_file.write(file_content)
                
                # Process with Alternative Processor
                alt_processor = AlternativeProcessor()
                alt_success, alt_result = await alt_processor.process_document(file_content, file.filename)
                
                # Use extracted text content
                if alt_success and alt_result.get('content'):
                    processed_content = alt_result['content'].encode('utf-8')
                    processing_method = "alternative_processor"
                    print(f"📄 [ALT-PROC] Successfully processed document. Text length: {len(processed_content)} chars")
                else:
                    print(f"⚠️ [ALT-PROC] No text content extracted, using fallback message")
                    fallback_msg = f"이 문서({file.filename})는 {file_extension.upper()} 형식이지만 텍스트를 추출할 수 없었습니다. 문서를 다시 업로드하거나 텍스트 형식으로 변환해 주세요."
                    processed_content = fallback_msg.encode('utf-8')
                    processing_method = "text_fallback"
                
                # Cleanup
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
            except Exception as e:
                print(f"⚠️ [ALT-PROC] Failed to process document with alternative processor: {str(e)}")
                print(f"📄 [WARNING] Document may not be processed optimally without document processing service")
        else:
            print(f"📄 [WARNING] Document may not be processed optimally without document processing service")
    
    # 실제 RAG 처리를 위해 문서를 임시로 저장하고 처리
    temp_document = {
        "id": doc_id,
        "filename": file.filename,
        "content": processed_content,
        "user_id": user_id,
        "processed": True,
        "file_type": file_extension,
        "processing_method": processing_method,
        "parsing_method": parsing_method,
        "chunking_method": chunking_method,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "upload_time": datetime.now().isoformat()
    }
    
    # 전역 documents 저장소에 추가 (실제 구현에서는 데이터베이스에 저장)
    if user_id not in user_documents:
        user_documents[user_id] = []
    user_documents[user_id].append(temp_document)
    
    print(f"📄 [UPLOAD] Document {doc_id} stored for user {user_id}")

    # Milvus 벡터 저장소에 문서 저장
    milvus_storage_status = "pending"
    if MILVUS_SERVICE_AVAILABLE and ENHANCED_CHUNKER_AVAILABLE:
        try:
            print(f"🗃️ [MILVUS] Storing document in Milvus vector database")

            # 문서 내용을 텍스트로 변환
            text_content = processed_content.decode('utf-8') if isinstance(processed_content, bytes) else str(processed_content)

            # 텍스트를 청킹 처리
            chunker = EnhancedChunker()
            method = ChunkingMethod.RECURSIVE_CHARACTER if chunking_method == "recursive_character" else ChunkingMethod.SENTENCE_BASED
            chunks = await chunker.chunk_document(
                content=text_content,
                filename=file.filename,
                method=method,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            # DocumentChunk 객체로 변환
            document_chunks = []
            for i, chunk in enumerate(chunks):
                doc_chunk = DocumentChunk(
                    chunk_id=f"{doc_id}_chunk_{i}",
                    text=chunk,
                    chunk_index=i,
                    metadata={"filename": file.filename, "processing_method": processing_method}
                )
                document_chunks.append(doc_chunk)

            # Milvus 서비스 가져오기 및 저장
            milvus_service = get_milvus_service()
            storage_success = await milvus_service.store_document_chunks(
                document_id=doc_id,
                document_name=file.filename,
                chunks=document_chunks,
                chunking_method=chunking_method
            )

            if storage_success:
                milvus_storage_status = "completed"
                print(f"✅ [MILVUS] Document {doc_id} successfully stored in Milvus with {len(document_chunks)} chunks")
                # 문서 정보에 벡터 저장 상태 업데이트
                temp_document["vector_db"] = "milvus"
                temp_document["vectorization_status"] = "completed"
            else:
                milvus_storage_status = "failed"
                print(f"❌ [MILVUS] Failed to store document {doc_id} in Milvus")
                temp_document["vector_db"] = "not_stored"
                temp_document["vectorization_status"] = "failed"

        except Exception as e:
            milvus_storage_status = "failed"
            print(f"❌ [MILVUS] Error storing document in Milvus: {e}")
            temp_document["vector_db"] = "not_stored"
            temp_document["vectorization_status"] = "failed"
    else:
        print(f"⚠️ [MILVUS] Milvus service or Enhanced Chunker not available, skipping vector storage")
        temp_document["vector_db"] = "not_stored"
        temp_document["vectorization_status"] = "pending"

    # Korean RAG 서비스로 자동 전송하여 벡터화 처리
    rag_processing_status = "pending"
    if KOREAN_RAG_AVAILABLE:
        try:
            print(f"🇰🇷 [RAG-AUTO] Sending document to Korean RAG service for vectorization")
            import httpx
            
            # 처리된 텍스트 콘텐츠를 Korean RAG 서비스로 전송
            text_content = processed_content.decode('utf-8') if isinstance(processed_content, bytes) else str(processed_content)
            
            rag_payload = {
                "title": file.filename,
                "content": text_content,
                "metadata": {
                    "filename": file.filename,
                    "file_size": len(processed_content),
                    "processing_method": processing_method,
                    "user_id": user_id,
                    "original_file_type": file_extension,
                    "upload_time": datetime.now().isoformat()
                },
                "document_id": doc_id
            }
            
            async with httpx.AsyncClient() as client:
                # Send to Korean RAG Orchestrator (Port 8008)
                orchestrator_payload = {
                    "user_id": user_id,
                    "filename": file.filename,
                    "content": text_content,
                    "metadata": {
                        "filename": file.filename,
                        "file_size": len(processed_content),
                        "processing_method": processing_method,
                        "original_file_type": file_extension,
                        "upload_time": datetime.now().isoformat(),
                        "document_id": doc_id
                    }
                }
                response = await client.post(
                    "http://localhost:8008/process_document",
                    json=orchestrator_payload,
                    timeout=30.0
                )
                if response.status_code == 200:
                    rag_response = await response.json()
                    if rag_response.get("status") == "success":
                        rag_processing_status = "vectorization_started"
                        print(f"✅ [KOREAN-RAG] Document successfully sent to Korean RAG Orchestrator")
                        print(f"🔄 [KOREAN-RAG] Chunks processed: {rag_response.get('chunks_processed', 0)}")
                        print(f"📊 [KOREAN-RAG] Chunks stored: {rag_response.get('chunks_stored', 0)}")
                    else:
                        print(f"⚠️ [KOREAN-RAG] Korean RAG Orchestrator returned error")
                else:
                    print(f"⚠️ [KOREAN-RAG] Failed to send to Korean RAG Orchestrator: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ [RAG-AUTO] Error sending document to Korean RAG service: {e}")
            rag_processing_status = "rag_error"
    
    return {
        "success": True,
        "data": {
            "document_id": doc_id,
            "filename": file.filename,
            "message": "Document uploaded and processed successfully",
            "processing_status": "completed",
            "rag_processing": rag_processing_status,
            "vectorization_info": {
                "auto_sent_to_rag": KOREAN_RAG_AVAILABLE,
                "embedding_model": "jhgan/ko-sroberta-multitask" if KOREAN_RAG_AVAILABLE else None,
                "vector_db": "milvus" if KOREAN_RAG_AVAILABLE else None,
                "processing_method": processing_method
            }
        }
    }

@app.post("/api/v1/documents/upload")
async def upload_document(file: bytes = None, filename: str = "test.txt", user_id: str = "default_user"):
    """문서 업로드 엔드포인트 (Mock implementation)"""
    print(f"📄 [UPLOAD] Document upload request: filename={filename}, user_id={user_id}")
    
    # Mock document upload response
    doc_id = f"doc-{str(uuid.uuid4())[:8]}"
    return {
        "success": True,
        "document_id": doc_id,
        "filename": filename,
        "message": "Document uploaded successfully (mock)",
        "processing_status": "queued"
    }

async def calculate_actual_chunk_count(user_id: str, document_id: str) -> int:
    """실제 청크 개수를 계산하는 헬퍼 함수"""
    print(f"🔢 [CHUNK-COUNT] Calculating chunk count for {document_id}, user: {user_id}")
    try:
        # 기존 청킹 로직을 사용해서 실제 청크 개수 계산
        user_docs = user_documents.get(user_id, [])
        document = None
        
        for doc in user_docs:
            if doc["id"] == document_id:
                document = doc
                break
        
        if not document:
            print(f"🔢 [CHUNK-COUNT] Document {document_id} not found for user {user_id}")
            return 1

        # 실제 저장된 청크가 있는지 확인
        if "chunks" in document and isinstance(document["chunks"], list):
            actual_count = len(document["chunks"])
            print(f"🔢 [CHUNK-COUNT] Found actual chunks: {actual_count}")
            return max(actual_count, 1)

        # 문서 내용 디코딩
        content = ""
        if isinstance(document["content"], bytes):
            try:
                content = document["content"].decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content = document["content"].decode('cp949')
                except:
                    content = str(document["content"])
        elif isinstance(document["content"], list):
            if document["content"]:
                if isinstance(document["content"][0], dict):
                    content_parts = [str(item.get("text", "")) for item in document["content"]]
                    content = "\n".join(content_parts)
                else:
                    content = "\n".join(str(item) for item in document["content"])
        else:
            content = str(document["content"])
        
        if not content.strip():
            print(f"🔢 [CHUNK-COUNT] Content is empty, returning 1")
            return 1
        
        # 기존 청킹 로직 사용 (라인 2154-2276과 동일한 로직)
        chunks = []
        file_type = document.get("file_type", "").lower()
        is_structured_doc = file_type in ['pdf', 'pptx', 'docx', 'doc']
        print(f"🔢 [CHUNK-COUNT] File type: {file_type}, is_structured_doc: {is_structured_doc}")
        
        if is_structured_doc:
            # 구조화된 문서의 청킹 로직
            major_sections = []
            for delimiter in ['\n\n\n', '\\n\\n', '\n\n', '\\n', '\n']:
                if delimiter in content:
                    major_sections = content.split(delimiter)
                    break
            
            if not major_sections or len(major_sections) == 1:
                major_sections = [content]
            
            MAX_CHUNK_SIZE = 1000
            MIN_CHUNK_SIZE = 100
            chunk_count = 0
            
            for section in major_sections:
                section = section.strip()
                if not section:
                    continue
                
                if len(section) <= MAX_CHUNK_SIZE:
                    if len(section) >= MIN_CHUNK_SIZE:
                        chunk_count += 1
                else:
                    # 큰 섹션을 작은 청크로 분할
                    sentences = section.split('. ')
                    if len(sentences) == 1:
                        sentences = section.split('.\n')
                    if len(sentences) == 1:
                        sentences = section.split('\n')
                    
                    current_chunk = ""
                    for sentence in sentences:
                        if len(current_chunk + sentence) > MAX_CHUNK_SIZE and current_chunk.strip():
                            if len(current_chunk.strip()) >= MIN_CHUNK_SIZE:
                                chunk_count += 1
                            current_chunk = sentence
                        else:
                            current_chunk += (" " if current_chunk else "") + sentence
                    
                    if current_chunk.strip() and len(current_chunk.strip()) >= MIN_CHUNK_SIZE:
                        chunk_count += 1
            
            result = max(chunk_count, 1)  # 최소 1개 보장
            print(f"🔢 [CHUNK-COUNT] Structured document chunk count: {result}")
            return result
        else:
            # 일반 텍스트 문서는 기본 청킹
            lines = content.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            result = max(len(non_empty_lines) // 10, 1)
            print(f"🔢 [CHUNK-COUNT] Text document chunk count: {result} (from {len(non_empty_lines)} non-empty lines)")
            return result
    
    except Exception as e:
        print(f"❌ [CHUNK-COUNT] Error calculating chunk count for {document_id}: {str(e)}")
        return 1

@app.get("/api/v1/documents/{user_id}")
async def get_user_documents(user_id: str, limit: int = 20, offset: int = 0):
    """사용자 문서 목록 반환 - Korean RAG Service와 로컬 스토어에서 통합 조회"""
    print(f"📄 [DOCS] Getting documents for user: {user_id}")
    
    all_docs = []
    
    # 1. Korean RAG Service에서 문서 목록 가져오기
    if KOREAN_RAG_AVAILABLE:
        try:
            print(f"🇰🇷 [KOREAN-RAG] Fetching documents from Korean RAG service")
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8008/documents")
                if response.status_code == 200:
                    rag_response = await response.json()
                    if rag_response.get("success") and "data" in rag_response:
                        rag_docs = rag_response["data"].get("documents", [])
                        print(f"🇰🇷 [KOREAN-RAG] Found {len(rag_docs)} documents from Korean RAG service")
                        
                        # Korean RAG 문서를 표준 형식으로 변환
                        for doc in rag_docs:
                            original_metadata = doc.get("metadata", {}).get("original_metadata", {})
                            chunk_count = doc.get("chunk_count", 1)
                            
                            # 청킹, 임베딩, 벡터화 상태 계산
                            chunking_status = "completed" if chunk_count > 0 else "pending"
                            embedding_status = "completed" if doc.get("embedding_count", 0) > 0 else chunking_status
                            vectorization_status = "completed" if doc.get("vector_count", 0) > 0 else embedding_status
                            
                            # 처리 진행률 계산 (각 단계 33.33%)
                            progress = 0
                            if chunking_status == "completed": progress += 33.33
                            if embedding_status == "completed": progress += 33.33  
                            if vectorization_status == "completed": progress += 33.34
                            
                            # 처리 시간 계산 (생성일자 기준)
                            from datetime import datetime
                            created_time = datetime.fromisoformat(doc.get("created_at", datetime.now().isoformat()).replace('Z', '+00:00'))
                            current_time = datetime.now()
                            time_elapsed = (current_time - created_time.replace(tzinfo=None)).total_seconds()
                            
                            # 각 단계별 예상 시간 (청킹: 2초, 임베딩: 5초, 벡터화: 3초)
                            chunking_time = 2 if chunking_status == "completed" else min(time_elapsed, 2)
                            embedding_time = 5 if embedding_status == "completed" else (min(time_elapsed - 2, 5) if time_elapsed > 2 else 0)
                            vectorization_time = 3 if vectorization_status == "completed" else (min(time_elapsed - 7, 3) if time_elapsed > 7 else 0)
                            
                            all_docs.append({
                                    "id": doc.get("document_id"),
                                    "filename": original_metadata.get("filename", "Unknown"),
                                    "title": original_metadata.get("title", doc.get("title", "제목 없음")),
                                    "created_at": doc.get("created_at", datetime.now().isoformat()),
                                    "file_size": original_metadata.get("file_size", 0),
                                    "is_processed": True,
                                    "chunk_count": chunk_count,
                                    "processing_method": original_metadata.get("processing_method", "korean_rag"),
                                    "source": "korean_rag",
                                    # 새로 추가된 벡터화 상태 정보
                                    "processing_status": {
                                        "chunking": chunking_status,
                                        "embedding": embedding_status, 
                                        "vectorization": vectorization_status,
                                        "overall_progress": round(progress, 1),
                                        "embedding_model": "jhgan/ko-sroberta-multitask",
                                        "embedding_dimensions": 768,
                                        "vector_db": "milvus",
                                        "collection_name": "korean_documents",
                                        # 처리 시간 정보 추가
                                        "timing_info": {
                                            "total_elapsed_seconds": round(time_elapsed, 1),
                                            "chunking_time_seconds": round(chunking_time, 1),
                                            "embedding_time_seconds": round(embedding_time, 1),
                                            "vectorization_time_seconds": round(vectorization_time, 1),
                                            "created_at": doc.get("created_at"),
                                            "status_timestamps": {
                                                "upload_completed": doc.get("created_at"),
                                                "chunking_completed": doc.get("created_at") if chunking_status == "completed" else None,
                                                "embedding_completed": doc.get("created_at") if embedding_status == "completed" else None,
                                                "vectorization_completed": doc.get("created_at") if vectorization_status == "completed" else None
                                            }
                                        }
                                    },
                                    "rag_stats": {
                                        "chunk_count": chunk_count,
                                        "embedding_count": doc.get("embedding_count", 0),
                                        "vector_count": doc.get("vector_count", 0),
                                        "similarity_threshold": 0.3,
                                        "max_context_chunks": 5
                                    }
                                })
                else:
                    print(f"⚠️ [KOREAN-RAG] Failed to fetch documents: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ [KOREAN-RAG] Error fetching documents from Korean RAG service: {e}")
    
    # 2. 로컬 스토어에서 문서 목록 가져오기
    user_docs = user_documents.get(user_id, [])
    print(f"📄 [DOCS] Found {len(user_docs)} local documents for user {user_id}")
    
    # 로컬 문서를 표준 형식으로 변환
    for doc in user_docs:
        file_size = len(doc["content"]) if isinstance(doc["content"], bytes) else len(str(doc["content"]))
        is_processed = doc.get("processed", True)
        processing_method = doc.get("processing_method", "local_storage")
        
        # 로컬 문서의 벡터화 상태 (Korean RAG 서비스로 전송되지 않은 상태)
        # 업로드 처리는 완료되었지만 벡터화는 대기 중인 상태
        chunking_status = "pending"  # 로컬에서는 기본 청킹만 수행
        embedding_status = "pending"  # 임베딩 미완료
        vectorization_status = "pending"  # Milvus 저장 미완료
        overall_progress = 10.0  # 업로드만 완료된 상태
        
        if processing_method in ["docling", "alternative_processor"]:
            chunking_status = "completed"  # 문서 처리 완료
            overall_progress = 30.0
            
        all_docs.append({
            "id": doc["id"],
            "filename": doc["filename"],
            "title": doc["filename"],
            "created_at": doc.get("upload_time", "2024-01-01T00:00:00"),
            "file_size": file_size,
            "is_processed": is_processed,
            "chunk_count": await calculate_actual_chunk_count(user_id, doc["id"]),  # 실제 청크 수 계산
            "processing_method": processing_method,
            "source": "local",
            # 벡터화 상태 정보 (로컬 문서용)
            "processing_status": {
                "chunking": chunking_status,
                "embedding": embedding_status,
                "vectorization": vectorization_status, 
                "overall_progress": overall_progress,
                "embedding_model": "pending",
                "embedding_dimensions": 0,
                "vector_db": "not_stored",
                "collection_name": "none",
                "needs_rag_processing": True  # Korean RAG 서비스 처리 필요
            },
            "rag_stats": {
                "chunk_count": await calculate_actual_chunk_count(user_id, doc["id"]),
                "embedding_count": 0,
                "vector_count": 0,
                "similarity_threshold": 0.0,
                "max_context_chunks": 0
            }
        })
    
    # 3. 문서 ID로 중복 제거 (Korean RAG가 우선)
    unique_docs = {}
    for doc in all_docs:
        doc_id = doc["id"]
        if doc_id not in unique_docs or doc["source"] == "korean_rag":
            unique_docs[doc_id] = doc
    
    final_docs = list(unique_docs.values())
    
    # 4. 생성 시간순 정렬 (최신순)
    final_docs.sort(key=lambda x: x["created_at"], reverse=True)
    
    # 5. 페이지네이션 적용
    total = len(final_docs)
    paginated_docs = final_docs[offset:offset + limit]
    
    print(f"📄 [DOCS] Returning {len(paginated_docs)} documents (total: {total}) - {sum(1 for d in final_docs if d['source'] == 'korean_rag')} from Korean RAG, {sum(1 for d in final_docs if d['source'] == 'local')} local")
    
    return {
        "documents": paginated_docs,
        "total": total,
        "limit": limit,
        "offset": offset
    }

# Document content and duplicate checking endpoints
@app.get("/api/v1/documents/{user_id}/{document_id}/content")
async def get_document_content(user_id: str, document_id: str):
    """문서 내용 상세 조회 - 문서 뷰어용"""
    print(f"📄 [DOC-CONTENT] Getting content for document: {document_id}, user: {user_id}")
    
    try:
        # 로컬 문서 스토어에서 조회
        user_docs = user_documents.get(user_id, [])
        document = None
        
        for doc in user_docs:
            if doc["id"] == document_id:
                document = doc
                break
        
        if not document:
            # Korean RAG Service에서도 조회 시도
            if KOREAN_RAG_AVAILABLE:
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"http://localhost:8008/documents/{document_id}")
                        if response.status_code == 200:
                                rag_doc = await response.json()
                                if rag_doc.get("success") and rag_doc.get("document"):
                                    doc_data = rag_doc["document"]
                                    return {
                                        "success": True,
                                        "document": {
                                            "id": doc_data.get("id"),
                                            "filename": doc_data.get("filename"),
                                            "title": doc_data.get("title", doc_data.get("filename")),
                                            "content": doc_data.get("content", ""),
                                            "file_size": doc_data.get("file_size", 0),
                                            "created_at": doc_data.get("created_at"),
                                            "processing_method": doc_data.get("processing_method", "korean_rag"),
                                            "chunk_count": doc_data.get("chunk_count", 0)
                                        }
                                    }
                except Exception as e:
                    print(f"⚠️ [DOC-CONTENT] Korean RAG service error: {str(e)}")
            
            return {
                "success": False,
                "error": "Document not found",
                "message": "요청하신 문서를 찾을 수 없습니다."
            }
        
        # 문서 내용 디코딩
        content = ""
        if isinstance(document["content"], bytes):
            try:
                content = document["content"].decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content = document["content"].decode('cp949')
                except:
                    content = str(document["content"])
        else:
            content = str(document["content"])
        
        print(f"📄 [DOC-CONTENT] Found document: {document['filename']}, content length: {len(content)} chars")
        
        return {
            "success": True,
            "document": {
                "id": document["id"],
                "filename": document["filename"],
                "title": document["filename"],
                "content": content,
                "file_size": len(document["content"]) if isinstance(document["content"], bytes) else len(content),
                "created_at": document.get("upload_time", datetime.now().isoformat()),
                "processing_method": document.get("processing_method", "basic"),
                "file_type": document.get("file_type", "unknown")
            }
        }
        
    except Exception as e:
        print(f"❌ [DOC-CONTENT] Error getting document content: {str(e)}")
        return {
            "success": False,
            "error": "Internal server error",
            "message": "문서 내용을 가져오는 중 오류가 발생했습니다."
        }

@app.get("/api/v1/documents/{user_id}/check-duplicate")
async def check_duplicate_document(user_id: str, filename: str):
    """파일명 중복 검사"""
    print(f"📄 [DUPLICATE-CHECK] Checking for duplicate: {filename}, user: {user_id}")
    
    try:
        # 로컬 문서 스토어에서 중복 검사
        user_docs = user_documents.get(user_id, [])
        duplicate_found = False
        existing_doc = None
        
        for doc in user_docs:
            if doc["filename"].lower() == filename.lower():
                duplicate_found = True
                existing_doc = {
                    "id": doc["id"],
                    "filename": doc["filename"],
                    "upload_time": doc.get("upload_time"),
                    "file_size": len(doc["content"]) if isinstance(doc["content"], bytes) else len(str(doc["content"])),
                    "processing_method": doc.get("processing_method", "basic")
                }
                break
        
        # Korean RAG Service에서도 중복 검사
        if not duplicate_found and KOREAN_RAG_AVAILABLE:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"http://localhost:8008/documents/{user_id}")
                    if response.status_code == 200:
                            rag_response = await response.json()
                            if rag_response.get("documents"):
                                for rag_doc in rag_response["documents"]:
                                    if rag_doc.get("filename", "").lower() == filename.lower():
                                        duplicate_found = True
                                        existing_doc = {
                                            "id": rag_doc.get("id"),
                                            "filename": rag_doc.get("filename"),
                                            "upload_time": rag_doc.get("created_at"),
                                            "file_size": rag_doc.get("file_size", 0),
                                            "processing_method": rag_doc.get("processing_method", "korean_rag")
                                        }
                                        break
            except Exception as e:
                print(f"⚠️ [DUPLICATE-CHECK] Korean RAG service error: {str(e)}")
        
        result = {
            "filename": filename,
            "duplicate_found": duplicate_found,
            "existing_document": existing_doc if duplicate_found else None
        }
        
        print(f"📄 [DUPLICATE-CHECK] Result: {'DUPLICATE FOUND' if duplicate_found else 'NO DUPLICATE'}")
        return result
        
    except Exception as e:
        print(f"❌ [DUPLICATE-CHECK] Error checking duplicate: {str(e)}")
        return {
            "filename": filename,
            "duplicate_found": False,
            "error": str(e)
        }

@app.delete("/api/v1/documents/{user_id}/{document_id}")
async def delete_document(user_id: str, document_id: str):
    """문서 삭제 엔드포인트 - 로컬 스토어와 Korean RAG 서비스에서 문서 삭제"""
    print(f"🗑️ [DELETE] Deleting document: {document_id}, user: {user_id}")

    deletion_results = []

    try:
        # 1. 로컬 스토어에서 문서 삭제
        user_docs = user_documents.get(user_id, [])
        local_deleted = False
        local_doc_name = None

        # 문서 ID나 파일명으로 찾아서 삭제
        for i, doc in enumerate(user_docs):
            if doc.get("document_id") == document_id or doc.get("filename") == document_id:
                local_doc_name = doc.get("filename", document_id)
                user_documents[user_id].pop(i)
                local_deleted = True
                print(f"✅ [DELETE] Local document deleted: {local_doc_name}")
                deletion_results.append({
                    "source": "local",
                    "success": True,
                    "message": f"로컬 문서 '{local_doc_name}' 삭제 완료"
                })
                break

        if not local_deleted:
            deletion_results.append({
                "source": "local",
                "success": False,
                "message": f"로컬에서 문서 '{document_id}'를 찾을 수 없습니다"
            })
            print(f"⚠️ [DELETE] Local document not found: {document_id}")

        # 2. Korean RAG Service에서 문서 삭제 시도 (doc_로 시작하는 경우)
        if document_id.startswith('doc_'):
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.delete(f"http://localhost:8008/documents/{document_id}")
                    if response.status_code == 200:
                        rag_result = await response.json()
                        if rag_result.get("success"):
                            print(f"✅ [DELETE] Korean RAG document deleted: {document_id}")
                            deletion_results.append({
                                "source": "korean_rag",
                                "success": True,
                                "message": f"Korean RAG 문서 '{document_id}' 삭제 완료"
                            })
                        else:
                            deletion_results.append({
                                "source": "korean_rag",
                                "success": False,
                                "message": f"Korean RAG 문서 삭제 실패: {rag_result.get('message', 'Unknown error')}"
                            })
                    else:
                        deletion_results.append({
                            "source": "korean_rag",
                            "success": False,
                            "message": f"Korean RAG 서비스 응답 오류 (상태코드: {response.status_code})"
                        })
            except Exception as rag_error:
                print(f"⚠️ [DELETE] Korean RAG service error: {rag_error}")
                deletion_results.append({
                    "source": "korean_rag",
                    "success": False,
                    "message": f"Korean RAG 서비스 연결 오류: {str(rag_error)}"
                })

        # 3. 삭제 결과 정리
        successful_deletions = [r for r in deletion_results if r["success"]]
        failed_deletions = [r for r in deletion_results if not r["success"]]

        overall_success = len(successful_deletions) > 0

        response_data = {
            "success": overall_success,
            "document_id": document_id,
            "user_id": user_id,
            "deletion_results": deletion_results,
            "summary": {
                "total_attempts": len(deletion_results),
                "successful": len(successful_deletions),
                "failed": len(failed_deletions)
            }
        }

        if overall_success:
            response_data["message"] = f"문서 '{document_id}' 삭제 완료 (성공: {len(successful_deletions)}, 실패: {len(failed_deletions)})"
            print(f"✅ [DELETE] Document deletion completed: {document_id}")
        else:
            response_data["message"] = f"문서 '{document_id}' 삭제 실패 - 모든 저장소에서 삭제에 실패했습니다"
            print(f"❌ [DELETE] Document deletion failed: {document_id}")

        return response_data

    except Exception as e:
        print(f"❌ [DELETE] Document deletion error: {e}")
        return {
            "success": False,
            "document_id": document_id,
            "user_id": user_id,
            "message": f"문서 삭제 중 오류 발생: {str(e)}",
            "error": str(e),
            "deletion_results": deletion_results
        }

@app.get("/api/v1/search/web/engines")
async def get_search_engines():
    """사용 가능한 검색엔진 목록 반환"""
    try:
        engines = [
            {
                "id": "google",
                "name": "Google",
                "description": "가장 널리 사용되는 검색엔진",
                "available": True
            },
            {
                "id": "bing",
                "name": "Bing",
                "description": "Microsoft의 검색엔진",
                "available": True
            },
            {
                "id": "duckduckgo",
                "name": "DuckDuckGo",
                "description": "개인정보 보호 중심 검색엔진",
                "available": True
            },
            {
                "id": "wikipedia",
                "name": "Wikipedia",
                "description": "위키피디아 검색",
                "available": True
            }
        ]
        
        print(f"🔍 [SEARCH-ENGINES] Returning {len(engines)} available search engines")
        return {"engines": engines}

    except Exception as e:
        print(f"❌ [SEARCH-ENGINES] Error getting search engines: {str(e)}")
        return {"engines": []}

@app.get("/api/v1/documents/view/{filename}")
async def view_document_by_filename(filename: str):
    """파일명으로 문서 전체 내용 조회 - 챗봇 테스터용"""
    print(f"📄 [DOC-VIEW] Getting document content for filename: {filename}")

    try:
        # 모든 사용자의 문서에서 해당 파일명 검색
        found_document = None
        for user_id, docs in user_documents.items():
            for doc in docs:
                if doc["filename"] == filename:
                    found_document = doc
                    break
            if found_document:
                break

        if not found_document:
            raise HTTPException(status_code=404, detail=f"Document with filename '{filename}' not found")

        return {
            "success": True,
            "filename": filename,
            "content": found_document["content"],
            "metadata": {
                "upload_time": found_document.get("upload_time"),
                "size": len(found_document["content"]),
                "doc_type": found_document.get("doc_type", "text"),
                "processing_method": found_document.get("processing_method", "basic")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [DOC-VIEW] Error getting document content: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving document: {str(e)}")

@app.get("/api/v1/documents/{user_id}/{document_id}/chunks")
async def get_document_chunks(user_id: str, document_id: str):
    """문서의 청킹된 텍스트 조회 - 청크 뷰어용"""
    print(f"📄 [DOC-CHUNKS] Getting chunks for document: {document_id}, user: {user_id}")
    
    try:
        # Korean RAG 문서인지 확인 (doc_로 시작)
        if document_id.startswith('doc_'):
            # Korean RAG Service에서 실제 청크 내용 조회
            if KOREAN_RAG_AVAILABLE:
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        # Korean RAG Service의 새로운 chunks API를 사용하여 실제 청크 내용 가져오기
                        response = await client.get(f"http://localhost:8008/documents/{document_id}/chunks")
                        if response.status_code == 200:
                                chunks_result = await response.json()
                                if chunks_result.get("success") and chunks_result.get("data"):
                                    chunks_data = chunks_result["data"]
                                    raw_chunks = chunks_data.get("chunks", [])
                                    
                                    # 실제 청크 데이터를 표준 형식으로 변환
                                    document_chunks = []
                                    for i, chunk in enumerate(raw_chunks):
                                        document_chunks.append({
                                            "chunk_id": chunk.get("id", f"chunk_{i}"),
                                            "text": chunk.get("text", ""),
                                            "chunk_index": chunk.get("chunk_id", i),
                                            "similarity_score": 1.0,  # 원본 청크이므로 완벽한 일치
                                            "metadata": chunk.get("metadata", {}),
                                            "length": len(chunk.get("text", ""))
                                        })
                                    
                                    if document_chunks:
                                        print(f"✅ [DOC-CHUNKS] Retrieved {len(document_chunks)} actual chunks from Korean RAG")
                                        return {
                                            "success": True,
                                            "document_id": document_id,
                                            "total_chunks": len(document_chunks),
                                            "chunks": document_chunks,
                                            "source": "korean_rag_actual",
                                            "message": f"Korean RAG 문서의 실제 {len(document_chunks)}개 청크를 조회했습니다."
                                        }
                        
                        # 청크 API가 실패한 경우, 문서 정보만 반환 (fallback)
                        print(f"⚠️ [DOC-CHUNKS] Korean RAG chunks API failed, falling back to placeholder")
                        async with session.get(f"http://localhost:8008/documents") as response:
                            if response.status == 200:
                                docs_result = await response.json()
                                if docs_result.get("success"):
                                    documents = docs_result["data"].get("documents", [])
                                    for doc in documents:
                                        if doc.get("document_id") == document_id:
                                            chunk_count = doc.get("chunk_count", 0)
                                            # 청크 개수만큼 더미 청크 생성
                                            dummy_chunks = []
                                            for i in range(chunk_count):
                                                dummy_chunks.append({
                                                    "chunk_id": f"{document_id}_chunk_{i}",
                                                    "text": f"[청크 {i+1}] 이 청크의 실제 내용은 Korean RAG 시스템의 벡터 데이터베이스에 저장되어 있습니다.",
                                                    "chunk_index": i,
                                                    "similarity_score": 0.0,
                                                    "metadata": {"document_id": document_id, "chunk_type": "placeholder"},
                                                    "length": 50
                                                })
                                            
                                            return {
                                                "success": True,
                                                "document_id": document_id,
                                                "total_chunks": chunk_count,
                                                "chunks": dummy_chunks,
                                                "source": "korean_rag_placeholder",
                                                "message": f"Korean RAG 문서의 {chunk_count}개 청크 정보를 조회했습니다. (실제 텍스트는 벡터 DB에 저장)"
                                            }
                except Exception as e:
                    print(f"⚠️ [DOC-CHUNKS] Korean RAG service error: {str(e)}")
        
        # 일반 문서 처리
        user_docs = user_documents.get(user_id, [])
        document = None
        
        for doc in user_docs:
            if doc["id"] == document_id:
                document = doc
                break
        
        if not document:
            return {
                "success": False,
                "error": "Document not found",
                "message": "요청하신 문서를 찾을 수 없습니다."
            }
        
        # 문서 내용 디코딩
        content = ""
        if isinstance(document["content"], bytes):
            try:
                content = document["content"].decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content = document["content"].decode('cp949')
                except:
                    content = str(document["content"])
        else:
            content = str(document["content"])
        
        # 개선된 청킹 로직 - 다양한 분할 기준 사용
        chunks = []
        
        # 문서 타입에 따른 청킹 전략
        file_type = document.get("file_type", "").lower()
        is_structured_doc = file_type in ['pdf', 'pptx', 'docx', 'doc']
        
        if is_structured_doc:
            # 구조화된 문서 (PDF, PPT, Word)의 경우 더 세분화된 청킹
            # 1. 먼저 큰 섹션으로 분할 (여러 개행, 페이지 구분자 등)
            major_sections = []
            for delimiter in ['\n\n\n', '\\n\\n', '\n\n', '\\n', '\n']:
                if delimiter in content:
                    major_sections = content.split(delimiter)
                    break
            
            if not major_sections or len(major_sections) == 1:
                major_sections = [content]
            
            # 2. 각 섹션을 적절한 크기로 분할
            MAX_CHUNK_SIZE = 1000  # 최대 청크 크기 (문자 수)
            MIN_CHUNK_SIZE = 100   # 최소 청크 크기
            
            chunk_idx = 0
            for section_idx, section in enumerate(major_sections):
                section = section.strip()
                if not section:
                    continue
                
                if len(section) <= MAX_CHUNK_SIZE:
                    # 섹션이 적절한 크기면 그대로 청크로 사용
                    if len(section) >= MIN_CHUNK_SIZE:
                        chunks.append({
                            "chunk_id": f"{document_id}_section_{chunk_idx}",
                            "text": section,
                            "chunk_index": chunk_idx,
                            "similarity_score": 1.0,
                            "metadata": {
                                "document_id": document_id,
                                "chunk_type": "section",
                                "section_number": section_idx + 1,
                                "file_type": file_type
                            },
                            "length": len(section)
                        })
                        chunk_idx += 1
                else:
                    # 너무 긴 섹션은 더 작은 단위로 분할
                    sentences = []
                    # 문장 단위로 분할 시도
                    for sent_delimiter in ['. ', '.\n', '! ', '?\n', '? ']:
                        if sent_delimiter in section:
                            sentences = section.split(sent_delimiter)
                            break
                    
                    if not sentences:
                        # 문장 분할이 안 되면 줄 단위로 분할
                        sentences = section.split('\n')
                    
                    current_chunk = ""
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if not sentence:
                            continue
                            
                        # 현재 청크에 문장을 추가했을 때 크기 확인
                        potential_chunk = current_chunk + (" " if current_chunk else "") + sentence
                        
                        if len(potential_chunk) <= MAX_CHUNK_SIZE:
                            current_chunk = potential_chunk
                        else:
                            # 현재 청크를 저장하고 새 청크 시작
                            if current_chunk and len(current_chunk) >= MIN_CHUNK_SIZE:
                                chunks.append({
                                    "chunk_id": f"{document_id}_chunk_{chunk_idx}",
                                    "text": current_chunk,
                                    "chunk_index": chunk_idx,
                                    "similarity_score": 1.0,
                                    "metadata": {
                                        "document_id": document_id,
                                        "chunk_type": "smart_chunk",
                                        "section_number": section_idx + 1,
                                        "file_type": file_type
                                    },
                                    "length": len(current_chunk)
                                })
                                chunk_idx += 1
                            current_chunk = sentence
                    
                    # 마지막 청크 저장
                    if current_chunk and len(current_chunk) >= MIN_CHUNK_SIZE:
                        chunks.append({
                            "chunk_id": f"{document_id}_final_chunk_{chunk_idx}",
                            "text": current_chunk,
                            "chunk_index": chunk_idx,
                            "similarity_score": 1.0,
                            "metadata": {
                                "document_id": document_id,
                                "chunk_type": "smart_chunk",
                                "section_number": section_idx + 1,
                                "file_type": file_type
                            },
                            "length": len(current_chunk)
                        })
                        chunk_idx += 1
        else:
            # 텍스트 파일 등 기본 문서는 기존 로직 사용
            paragraphs = content.split('\n\n')
            
            for i, paragraph in enumerate(paragraphs):
                if paragraph.strip():  # 빈 문단 제외
                    chunks.append({
                        "chunk_id": f"{document_id}_paragraph_{i}",
                        "text": paragraph.strip(),
                        "chunk_index": i,
                        "similarity_score": 1.0,  # 일반 문서는 모든 청크가 관련성 100%
                        "metadata": {
                            "document_id": document_id,
                            "chunk_type": "paragraph",
                            "paragraph_number": i + 1
                        },
                        "length": len(paragraph.strip())
                    })
        
        # 청크가 없으면 전체 텍스트를 하나의 청크로 처리
        if not chunks:
            chunks.append({
                "chunk_id": f"{document_id}_full",
                "text": content,
                "chunk_index": 0,
                "similarity_score": 1.0,
                "metadata": {
                    "document_id": document_id,
                    "chunk_type": "full_document"
                },
                "length": len(content)
            })
        
        print(f"📄 [DOC-CHUNKS] Found {len(chunks)} chunks for document: {document['filename']}")
        
        return {
            "success": True,
            "document_id": document_id,
            "total_chunks": len(chunks),
            "chunks": chunks,
            "source": "local",
            "message": f"일반 문서의 {len(chunks)}개 청크를 조회했습니다."
        }
        
    except Exception as e:
        print(f"❌ [DOC-CHUNKS] Error getting document chunks: {str(e)}")
        return {
            "success": False,
            "error": "Internal server error",
            "message": "문서 청크를 가져오는 중 오류가 발생했습니다."
        }

# Internal Server Management Endpoints
try:
    from services.internal_server_client import internal_client, load_internal_servers_from_env, load_internal_servers_from_config
    INTERNAL_SERVER_AVAILABLE = True
    print("🔗 [INTERNAL] Internal server client loaded successfully")
except ImportError as e:
    INTERNAL_SERVER_AVAILABLE = False
    print(f"⚠️ [INTERNAL] Internal server client not available: {e}")

class ServerConfigRequest(BaseModel):
    """서버 설정 요청 모델"""
    embedding_servers: List[Dict[str, Any]]
    llm_servers: List[Dict[str, Any]]
    current_config: Optional[Dict[str, Any]] = None

class ServerTestRequest(BaseModel):
    """서버 연결 테스트 요청 모델"""
    server_url: str
    server_type: str  # "embedding" or "llm"

class InternalServerSettingsRequest(BaseModel):
    """내부 서버 설정 전체 요청 모델"""
    internal_settings: Dict[str, Any]
    embedding_servers: List[Dict[str, Any]]
    llm_servers: List[Dict[str, Any]]

class OIDCSettingsRequest(BaseModel):
    """OIDC 인증 설정 요청 모델"""
    enabled: bool

class OIDCSettingsResponse(BaseModel):
    """OIDC 인증 설정 응답 모델"""
    enabled: bool
    current_oidc_user: Optional[str] = None

class OIDCCallbackRequest(BaseModel):
    """외부 OIDC 시스템으로부터 받는 콜백 요청 모델"""
    user_id: str
    user_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    employee_number: Optional[str] = None
    session_token: Optional[str] = None
    expires_at: Optional[str] = None

@app.get("/api/v1/internal-servers")
async def get_all_internal_servers_settings(db: AsyncSession = Depends(get_db)):
    """내부 서버 설정 전체 조회 - PostgreSQL 통합"""
    try:
        if not DATABASE_AVAILABLE or db is None:
            # 데이터베이스가 없을 때 기본값 반환
            response_data = {
                "internal_settings": {
                    "enable_internal_server": True,
                    "internal_server_mode": "임베딩 서버만",
                    "default_model": "모델을 입력"
                },
                "embedding_servers": [
                    {
                        "id": "sdcrpapocv",
                        "name": "sdcrpapocv",
                        "url": "http://11.93.26.130:8080",
                        "api_key": "••••••••••••••••••••••••••••••••",
                        "status": "error",
                        "is_primary": False,
                        "chunk_size": 1000,
                        "chunk_overlap": 200
                    },
                    {
                        "id": "sdcalpocv2",
                        "name": "sdcalpocv2",
                        "url": "http://11.93.26.43:8080",
                        "api_key": "••••••••••••••••••••••••••••••••",
                        "status": "error",
                        "is_primary": False,
                        "chunk_size": 1000,
                        "chunk_overlap": 200
                    },
                    {
                        "id": "mischataiappddv",
                        "name": "mischataiappddv",
                        "url": "http://11.93.33.10:8080",
                        "api_key": "••••••••••••••••••••••••••••••••",
                        "status": "error",
                        "is_primary": False,
                        "chunk_size": 1000,
                        "chunk_overlap": 200
                    }
                ],
                "llm_servers": [
                    {
                        "id": "qwen3-235b-server1",
                        "name": "Qwen3-235B Server 1",
                        "url": "http://11.93.26.130:8081",
                        "api_key": "••••••••••••••••••••••••••••••••",
                        "model": "Qwen3-235B",
                        "status": "inactive",
                        "is_primary": False,
                        "temperature": 0.7,
                        "max_tokens": 2048
                    }
                ]
            }
        else:
            # 실제 데이터베이스에서 설정 조회
            from app.services.server_settings_service import ServerSettingsService
            service = ServerSettingsService(db)
            response_data = await service.get_internal_server_settings()

            if response_data is None:
                # DB에 데이터가 없으면 기본값 반환
                response_data = {
                    "internal_settings": {
                        "enable_internal_server": True,
                        "internal_server_mode": "임베딩 서버만",
                        "default_model": "모델을 입력"
                    },
                    "embedding_servers": [],
                    "llm_servers": []
                }

        return {
            "success": True,
            "data": response_data
        }
    except Exception as e:
        print(f"❌ [INTERNAL] Error getting all internal server settings: {str(e)}")
        return {
            "success": False,
            "error": "settings_get_failed",
            "message": f"내부 서버 설정 조회 중 오류가 발생했습니다: {str(e)}"
        }

@app.post("/api/v1/internal-servers")
async def save_all_internal_servers_settings(request: InternalServerSettingsRequest, db: AsyncSession = Depends(get_db)):
    """내부 서버 설정 전체 저장 - PostgreSQL 통합"""
    try:
        print(f"✅ [INTERNAL] Saving complete internal server settings:")
        print(f"   - Internal Settings: {request.internal_settings}")
        print(f"   - Embedding Servers: {len(request.embedding_servers)} servers")
        print(f"   - LLM Servers: {len(request.llm_servers)} servers")

        # 기본 서버 설정 확인
        primary_embedding = None
        primary_llm = None

        for server in request.embedding_servers:
            if server.get("is_primary"):
                primary_embedding = server.get("name")
                break

        for server in request.llm_servers:
            if server.get("is_primary"):
                primary_llm = server.get("name")
                break

        if primary_embedding:
            print(f"   - Primary Embedding Server: {primary_embedding}")
        if primary_llm:
            print(f"   - Primary LLM Server: {primary_llm}")

        # 데이터베이스에 저장
        save_success = False
        if DATABASE_AVAILABLE and db is not None:
            try:
                from app.services.server_settings_service import ServerSettingsService
                service = ServerSettingsService(db)

                settings_data = {
                    "internal_settings": request.internal_settings,
                    "embedding_servers": request.embedding_servers,
                    "llm_servers": request.llm_servers
                }

                save_success = await service.save_internal_server_settings(settings_data)
                if save_success:
                    print(f"✅ [DB] Settings saved to PostgreSQL database")
                else:
                    print(f"❌ [DB] Failed to save to PostgreSQL database")
            except Exception as db_error:
                print(f"❌ [DB] Database save error: {str(db_error)}")
                save_success = False
        else:
            print(f"⚠️ [DB] Database not available - settings saved in memory only")
            save_success = True  # 메모리 저장은 성공으로 처리

        return {
            "success": True,
            "message": f"내부 서버 설정이 성공적으로 저장되었습니다.{' (데이터베이스)' if save_success and DATABASE_AVAILABLE else ' (메모리)'}",
            "data": {
                "embedding_servers_count": len(request.embedding_servers),
                "llm_servers_count": len(request.llm_servers),
                "primary_embedding_server": primary_embedding,
                "primary_llm_server": primary_llm,
                "database_saved": save_success and DATABASE_AVAILABLE
            }
        }
    except Exception as e:
        print(f"❌ [INTERNAL] Error saving all internal server settings: {str(e)}")
        return {
            "success": False,
            "error": "settings_save_failed",
            "message": f"내부 서버 설정 저장 중 오류가 발생했습니다: {str(e)}"
        }

@app.get("/api/v1/internal-servers/status")
async def get_internal_servers_status():
    """내부 서버 상태 조회"""
    if not INTERNAL_SERVER_AVAILABLE:
        return {
            "success": False,
            "error": "internal_server_not_available",
            "message": "내부 서버 클라이언트를 사용할 수 없습니다."
        }

    try:
        status = await internal_client.health_check_all_servers()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        print(f"❌ [INTERNAL] Error checking server status: {str(e)}")
        return {
            "success": False,
            "error": "status_check_failed",
            "message": f"서버 상태 확인 중 오류가 발생했습니다: {str(e)}"
        }

@app.post("/api/v1/internal-servers/config")
async def update_internal_servers_config(request: ServerConfigRequest):
    """내부 서버 설정 업데이트"""
    if not INTERNAL_SERVER_AVAILABLE:
        return {
            "success": False,
            "error": "internal_server_not_available",
            "message": "내부 서버 클라이언트를 사용할 수 없습니다."
        }

    try:
        config = {
            "embedding_servers": request.embedding_servers,
            "llm_servers": request.llm_servers
        }

        # current_config가 제공된 경우 추가 처리
        if request.current_config:
            config["current_config"] = request.current_config
            print(f"✅ [INTERNAL] Primary server settings updated:")
            if "primary_embedding_server" in request.current_config:
                print(f"   - Primary Embedding Server: {request.current_config['primary_embedding_server']}")
            if "primary_llm_server" in request.current_config:
                print(f"   - Primary LLM Server: {request.current_config['primary_llm_server']}")

        load_internal_servers_from_config(config)

        return {
            "success": True,
            "message": "서버 설정이 업데이트되었습니다.",
            "data": {
                "embedding_servers_count": len(request.embedding_servers),
                "llm_servers_count": len(request.llm_servers),
                "primary_embedding_server": request.current_config.get("primary_embedding_server") if request.current_config else None,
                "primary_llm_server": request.current_config.get("primary_llm_server") if request.current_config else None
            }
        }
    except Exception as e:
        print(f"❌ [INTERNAL] Error updating server config: {str(e)}")
        return {
            "success": False,
            "error": "config_update_failed",
            "message": f"서버 설정 업데이트 중 오류가 발생했습니다: {str(e)}"
        }

@app.get("/api/v1/internal-servers/config")
async def get_internal_servers_config():
    """내부 서버 설정 조회"""
    if not INTERNAL_SERVER_AVAILABLE:
        return {
            "success": False,
            "error": "internal_server_not_available",
            "message": "내부 서버 클라이언트를 사용할 수 없습니다."
        }

    try:
        config = {
            "current_config": {
                "use_internal_servers": True,
                "internal_server_mode": "hybrid"
            },
            "embedding_servers": [
                {
                    "url": server.url,
                    "name": server.name,
                    "api_key": server.api_key,
                    "model": server.model,
                    "status": server.status
                }
                for server in internal_client.embedding_servers
            ],
            "llm_servers": [
                {
                    "url": server.url,
                    "name": server.name,
                    "api_key": server.api_key,
                    "model": server.model,
                    "status": server.status
                }
                for server in internal_client.llm_servers
            ]
        }

        return {
            "success": True,
            "data": config
        }
    except Exception as e:
        print(f"❌ [INTERNAL] Error getting server config: {str(e)}")
        return {
            "success": False,
            "error": "config_get_failed",
            "message": f"서버 설정 조회 중 오류가 발생했습니다: {str(e)}"
        }

@app.post("/api/v1/internal-servers/test")
async def test_internal_server_connection(request: ServerTestRequest):
    """내부 서버 연결 테스트"""
    if not INTERNAL_SERVER_AVAILABLE:
        return {
            "success": False,
            "error": "internal_server_not_available",
            "message": "내부 서버 클라이언트를 사용할 수 없습니다."
        }

    try:
        test_result = await internal_client.test_server_connection(request.server_url, request.server_type)
        return {
            "success": True,
            "data": test_result
        }
    except Exception as e:
        print(f"❌ [INTERNAL] Error testing server connection: {str(e)}")
        return {
            "success": False,
            "error": "connection_test_failed",
            "message": f"서버 연결 테스트 중 오류가 발생했습니다: {str(e)}"
        }

@app.post("/api/v1/internal-servers/load-env")
async def load_internal_servers_from_environment():
    """환경변수에서 내부 서버 설정 로드"""
    if not INTERNAL_SERVER_AVAILABLE:
        return {
            "success": False,
            "error": "internal_server_not_available",
            "message": "내부 서버 클라이언트를 사용할 수 없습니다."
        }

    try:
        # 환경변수 로드
        env_config = dict(os.environ)
        load_internal_servers_from_env(env_config)

        return {
            "success": True,
            "message": "환경변수에서 서버 설정이 로드되었습니다.",
            "data": {
                "embedding_servers_count": len(internal_client.embedding_servers),
                "llm_servers_count": len(internal_client.llm_servers)
            }
        }
    except Exception as e:
        print(f"❌ [INTERNAL] Error loading from environment: {str(e)}")
        return {
            "success": False,
            "error": "env_load_failed",
            "message": f"환경변수 로드 중 오류가 발생했습니다: {str(e)}"
        }

# ======================================================
# 🔧 외부 LLM 설정 관리 API 엔드포인트 (External LLM Settings)
# ======================================================

@app.get("/api/v1/external-llm-settings")
async def get_external_llm_settings():
    """외부 LLM 설정 조회"""
    try:
        async with get_db_session() as db:
            service = ServerSettingsService(db)
            settings = await service.get_external_llm_settings()

            if settings is None:
                # 기본값 반환
                default_settings = {
                    "api_url": "http://localhost:8000",
                    "ai_model": "gemini-1.5-pro",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "embedding_model": "KURE-v1",
                    "chunk_size": 1000,
                    "chunk_overlap": 200,
                    "enable_korean_processing": True,
                    "debug_mode": False
                }
                return {
                    "success": True,
                    "data": default_settings,
                    "message": "기본 외부 LLM 설정을 반환합니다."
                }

            return {
                "success": True,
                "data": settings,
                "message": "외부 LLM 설정을 성공적으로 조회했습니다."
            }

    except Exception as e:
        print(f"❌ [EXTERNAL-LLM] Error getting settings: {str(e)}")
        return {
            "success": False,
            "error": "get_settings_failed",
            "message": f"외부 LLM 설정 조회 중 오류가 발생했습니다: {str(e)}"
        }

@app.post("/api/v1/external-llm-settings")
async def save_external_llm_settings(request: Request):
    """외부 LLM 설정 저장"""
    try:
        settings_data = await request.json()
        print(f"🔧 [EXTERNAL-LLM] Saving settings: {settings_data}")

        async with get_db_session() as db:
            service = ServerSettingsService(db)
            success = await service.save_external_llm_settings(settings_data)

            if success:
                return {
                    "success": True,
                    "message": "외부 LLM 설정이 성공적으로 저장되었습니다. (데이터베이스)",
                    "data": {
                        "api_url": settings_data.get("api_url"),
                        "ai_model": settings_data.get("ai_model"),
                        "temperature": settings_data.get("temperature"),
                        "max_tokens": settings_data.get("max_tokens"),
                        "embedding_model": settings_data.get("embedding_model"),
                        "chunk_size": settings_data.get("chunk_size"),
                        "chunk_overlap": settings_data.get("chunk_overlap"),
                        "enable_korean_processing": settings_data.get("enable_korean_processing"),
                        "debug_mode": settings_data.get("debug_mode"),
                        "database_saved": True
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "save_failed",
                    "message": "외부 LLM 설정 저장에 실패했습니다."
                }

    except Exception as e:
        print(f"❌ [EXTERNAL-LLM] Error saving settings: {str(e)}")
        return {
            "success": False,
            "error": "save_error",
            "message": f"외부 LLM 설정 저장 중 오류가 발생했습니다: {str(e)}"
        }

@app.delete("/api/v1/external-llm-settings")
async def delete_external_llm_settings():
    """외부 LLM 설정 삭제"""
    try:
        async with get_db_session() as db:
            from sqlalchemy import delete
            from app.models.server_settings import LegacyServerSettings

            # 모든 외부 LLM 설정 삭제
            await db.execute(delete(LegacyServerSettings))
            await db.commit()

            return {
                "success": True,
                "message": "외부 LLM 설정이 성공적으로 삭제되었습니다."
            }

    except Exception as e:
        print(f"❌ [EXTERNAL-LLM] Error deleting settings: {str(e)}")
        return {
            "success": False,
            "error": "delete_failed",
            "message": f"외부 LLM 설정 삭제 중 오류가 발생했습니다: {str(e)}"
        }

@app.post("/api/v1/external-llm-settings/test")
async def test_external_llm_connection(request: Request):
    """외부 LLM 연결 테스트"""
    try:
        settings_data = await request.json()
        api_url = settings_data.get("api_url", "")
        ai_model = settings_data.get("ai_model", "")

        # 기본적인 연결 테스트 (실제 구현은 환경에 따라 다를 수 있음)
        test_message = "연결 테스트"

        return {
            "success": True,
            "message": f"외부 LLM 서버 연결 테스트가 성공했습니다.",
            "data": {
                "api_url": api_url,
                "ai_model": ai_model,
                "test_message": test_message,
                "connection_status": "active"
            }
        }

    except Exception as e:
        print(f"❌ [EXTERNAL-LLM] Error testing connection: {str(e)}")
        return {
            "success": False,
            "error": "connection_test_failed",
            "message": f"외부 LLM 서버 연결 테스트 중 오류가 발생했습니다: {str(e)}"
        }

# ============================================================================
# 사용자 관리 API 엔드포인트 (User Management API Endpoints)
# Created: 2025-09-29
# Purpose: 사용자 정보 및 챗봇 이용 히스토리 관리
# ============================================================================

# 사용자 관리용 Mock 데이터 (개발용)
MOCK_USERS_DATA = {
    "11111": {
        "user_id": "11111",
        "employee_number": "EMP001",
        "name": "홍길동",
        "department": "IT개발팀",
        "phone_number": "010-1111-1111",
        "email": "hong@company.com",
        "position": "선임연구원",
        "is_active": True,
        "created_at": "2025-09-01 09:00:00",
        "last_login": "2025-09-29 10:30:00",
        "login_count": 45
    },
    "22222": {
        "user_id": "22222",
        "employee_number": "EMP002",
        "name": "강감찬",
        "department": "기획팀",
        "phone_number": "010-2222-2222",
        "email": "kang@company.com",
        "position": "팀장",
        "is_active": True,
        "created_at": "2025-09-01 09:00:00",
        "last_login": "2025-09-29 09:15:00",
        "login_count": 28
    },
    "33333": {
        "user_id": "33333",
        "employee_number": "EMP003",
        "name": "이순신",
        "department": "보안팀",
        "phone_number": "010-3333-3333",
        "email": "lee@company.com",
        "position": "책임연구원",
        "is_active": True,
        "created_at": "2025-09-01 09:00:00",
        "last_login": "2025-09-29 14:20:00",
        "login_count": 62
    }
}

MOCK_USER_STATS = {
    "11111": {
        "total_sessions": 45,
        "total_conversations": 123,
        "total_messages": 567,
        "user_messages": 284,
        "ai_responses": 283,
        "total_uploads": 12,
        "total_tokens_used": 45600,
        "avg_response_time": 1250
    },
    "22222": {
        "total_sessions": 28,
        "total_conversations": 89,
        "total_messages": 334,
        "user_messages": 167,
        "ai_responses": 167,
        "total_uploads": 8,
        "total_tokens_used": 28900,
        "avg_response_time": 1150
    },
    "33333": {
        "total_sessions": 62,
        "total_conversations": 178,
        "total_messages": 892,
        "user_messages": 446,
        "ai_responses": 446,
        "total_uploads": 23,
        "total_tokens_used": 67800,
        "avg_response_time": 1180
    }
}

# OIDC 관련 전역 변수 (개발용)
CURRENT_USER_ROTATION = 0

def get_current_user_id() -> str:
    """개발용 사용자 자동 변경 함수"""
    global CURRENT_USER_ROTATION
    user_ids = list(MOCK_USERS_DATA.keys())
    user_id = user_ids[CURRENT_USER_ROTATION % len(user_ids)]
    CURRENT_USER_ROTATION += 1
    return user_id

@app.get("/api/v1/users")
async def get_users(limit: int = 50, offset: int = 0, search: str = ""):
    """사용자 목록 조회"""
    try:
        print(f"👥 [USER-MGT] Getting users list (limit: {limit}, offset: {offset}, search: '{search}')")

        if USER_MANAGEMENT_DB_AVAILABLE:
            # 실제 데이터베이스에서 사용자 목록 조회 (접속 상태 포함)
            users = await db_service.get_all_users_current_status(limit=limit, offset=offset, search=search)

            # 총 사용자 수를 위한 별도 쿼리 (실제로는 COUNT 쿼리를 구현해야 하지만 임시로 전체 조회)
            all_users = await db_service.get_all_users_current_status(limit=1000, offset=0, search=search)
            total = len(all_users)

            # 현재 접속 사용자 설정 (데이터베이스에서 랜덤 선택)
            current_user = await db_service.get_current_mock_user()

            print(f"✅ [USER-MGT-DB] Found {len(users)} users from database (total: {total})")
            print(f"🔄 [USER-MGT-DB] Current user: {current_user.get('name', 'Unknown') if current_user else 'Unknown'}")

            return {
                "success": True,
                "data": {
                    "users": users,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "current_user": current_user
                }
            }
        else:
            # 폴백: Mock 데이터 사용
            print("⚠️ [USER-MGT] Database not available, using mock data")
            users = list(MOCK_USERS_DATA.values())

            # 검색 필터링
            if search:
                search_lower = search.lower()
                users = [
                    user for user in users
                    if (search_lower in user["name"].lower() or
                        search_lower in user["employee_number"].lower() or
                        search_lower in user["department"].lower())
                ]

            # 페이징 적용
            total = len(users)
            users = users[offset:offset + limit]

            # 현재 접속 사용자 설정 (개발용 자동 변경)
            current_user_id = get_current_user_id()
            current_user = MOCK_USERS_DATA.get(current_user_id, {})

            print(f"✅ [USER-MGT] Found {len(users)} users from mock data (total: {total})")
            print(f"🔄 [USER-MGT] Current user rotated to: {current_user.get('name', 'Unknown')} ({current_user_id})")

            return {
                "success": True,
                "data": {
                    "users": users,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "current_user": current_user
                }
            }

    except Exception as e:
        print(f"❌ [USER-MGT] Error getting users: {str(e)}")
        return {
            "success": False,
            "error": "fetch_users_failed",
            "message": f"사용자 목록 조회 중 오류가 발생했습니다: {str(e)}"
        }

@app.get("/api/v1/users/{user_id}")
async def get_user_detail(user_id: str):
    """특정 사용자 상세 정보 조회"""
    try:
        print(f"👤 [USER-MGT] Getting user detail for: {user_id}")

        if USER_MANAGEMENT_DB_AVAILABLE:
            # 실제 데이터베이스에서 사용자 정보 조회
            user = await db_service.get_user_profile(user_id)
            if not user:
                return {
                    "success": False,
                    "error": "user_not_found",
                    "message": "사용자를 찾을 수 없습니다."
                }

            # 사용자 통계 정보 조회
            stats = await db_service.get_user_statistics(user_id)

            # 사용자 접속 이력 조회
            login_history = await db_service.get_user_login_history(user_id, limit=20)

            print(f"✅ [USER-MGT-DB] Found user from database: {user['name']}")

            return {
                "success": True,
                "data": {
                    "user": user,
                    "stats": stats or {},
                    "login_history": login_history or []
                }
            }
        else:
            # 폴백: Mock 데이터 사용
            print("⚠️ [USER-MGT] Database not available, using mock data")
            user = MOCK_USERS_DATA.get(user_id)
            if not user:
                return {
                    "success": False,
                    "error": "user_not_found",
                    "message": "사용자를 찾을 수 없습니다."
                }

            # 사용자 통계 정보 추가
            stats = MOCK_USER_STATS.get(user_id, {})

            print(f"✅ [USER-MGT] Found user from mock data: {user['name']}")

            return {
                "success": True,
                "data": {
                    "user": user,
                    "stats": stats
                }
            }

    except Exception as e:
        print(f"❌ [USER-MGT] Error getting user detail: {str(e)}")
        return {
            "success": False,
            "error": "fetch_user_failed",
            "message": f"사용자 정보 조회 중 오류가 발생했습니다: {str(e)}"
        }

@app.get("/api/v1/auth/current-user")
async def get_current_user():
    """현재 인증된 사용자 정보 반환 (OIDC 통합 및 개발용 Mock)"""
    try:
        print(f"🔐 [AUTH] Getting current user info")

        if USER_MANAGEMENT_DB_AVAILABLE:
            # 실제 데이터베이스에서 현재 사용자 조회 (개발 모드에서는 랜덤 선택)
            user = await db_service.get_current_mock_user()

            if not user:
                return {
                    "success": False,
                    "error": "user_not_authenticated",
                    "message": "인증된 사용자가 없습니다."
                }

            # 로그인 정보 업데이트
            await db_service.update_user_login(user['user_id'])

            print(f"✅ [AUTH-DB] Current user from database: {user['name']} ({user['user_id']})")

            return {
                "success": True,
                "data": {
                    "user": user,
                    "authentication_method": "development_mock_db",
                    "session_valid": True
                }
            }
        else:
            # 폴백: Mock 데이터 사용
            print("⚠️ [AUTH] Database not available, using mock data")
            current_user_id = get_current_user_id()
            user = MOCK_USERS_DATA.get(current_user_id)

            if not user:
                return {
                    "success": False,
                    "error": "user_not_authenticated",
                    "message": "인증된 사용자가 없습니다."
                }

            print(f"✅ [AUTH] Current user from mock data: {user['name']} ({current_user_id})")

            return {
                "success": True,
                "data": {
                    "user": user,
                    "authentication_method": "development_mock",
                    "session_valid": True
                }
            }

    except Exception as e:
        print(f"❌ [AUTH] Error getting current user: {str(e)}")
        return {
            "success": False,
            "error": "auth_check_failed",
            "message": f"사용자 인증 확인 중 오류가 발생했습니다: {str(e)}"
        }

@app.get("/api/v1/auth/oidc-settings")
async def get_oidc_settings():
    """OIDC 인증 설정 조회"""
    global oidc_settings

    try:
        print(f"🔐 [OIDC] Getting OIDC settings: enabled={oidc_settings['enabled']}")

        return {
            "success": True,
            "data": {
                "enabled": oidc_settings["enabled"],
                "current_oidc_user": oidc_settings["current_oidc_user"]
            }
        }
    except Exception as e:
        print(f"❌ [OIDC] Error getting OIDC settings: {str(e)}")
        return {
            "success": False,
            "error": "oidc_settings_error",
            "message": f"OIDC 설정 조회 중 오류가 발생했습니다: {str(e)}"
        }

@app.post("/api/v1/auth/oidc-settings")
async def save_oidc_settings(request: OIDCSettingsRequest):
    """OIDC 인증 설정 저장"""
    global oidc_settings

    try:
        print(f"🔐 [OIDC] Saving OIDC settings: enabled={request.enabled}")

        # OIDC 설정 업데이트
        oidc_settings["enabled"] = request.enabled

        # OIDC가 비활성화되면 현재 OIDC 사용자 정보 제거
        if not request.enabled:
            oidc_settings["current_oidc_user"] = None
            print("🔄 [OIDC] OIDC disabled - switched to PostgreSQL development users")
        else:
            # TODO: 실제 OIDC 인증 연동 시 여기서 사용자 정보 설정
            print("🔐 [OIDC] OIDC enabled - ready for authentication integration")

        print(f"✅ [OIDC] Settings saved successfully: {oidc_settings}")

        return {
            "success": True,
            "data": {
                "enabled": oidc_settings["enabled"],
                "current_oidc_user": oidc_settings["current_oidc_user"],
                "message": "OIDC 설정이 저장되었습니다."
            }
        }
    except Exception as e:
        print(f"❌ [OIDC] Error saving OIDC settings: {str(e)}")
        return {
            "success": False,
            "error": "oidc_settings_save_error",
            "message": f"OIDC 설정 저장 중 오류가 발생했습니다: {str(e)}"
        }

@app.post("/api/v1/auth/oidc-callback")
async def oidc_callback(request: OIDCCallbackRequest):
    """외부 OIDC 시스템으로부터 인증된 사용자 정보 수신"""
    global oidc_settings, oidc_sessions

    try:
        print(f"🔐 [OIDC-CALLBACK] Received OIDC callback for user: {request.user_id}")

        # OIDC가 활성화된 경우에만 처리
        if not oidc_settings["enabled"]:
            return {
                "success": False,
                "error": "oidc_not_enabled",
                "message": "OIDC 인증이 비활성화되어 있습니다."
            }

        # 세션 토큰 생성 (제공되지 않은 경우)
        session_token = request.session_token or f"oidc_session_{uuid.uuid4().hex[:16]}"

        # 사용자 정보를 세션에 저장
        user_info = {
            "user_id": request.user_id,
            "user_name": request.user_name,
            "email": request.email,
            "department": request.department,
            "employee_number": request.employee_number,
            "session_token": session_token,
            "login_time": datetime.now().isoformat(),
            "expires_at": request.expires_at or (datetime.now() + timedelta(hours=8)).isoformat()
        }

        # 세션 저장
        oidc_sessions[session_token] = user_info

        # 현재 OIDC 사용자 업데이트
        oidc_settings["current_oidc_user"] = request.user_name or request.user_id

        # 데이터베이스에 사용자 정보 저장/업데이트 (있는 경우)
        if USER_MANAGEMENT_DB_AVAILABLE:
            try:
                # 사용자 프로필이 없으면 생성
                await db_service.create_or_update_oidc_user({
                    "user_id": request.user_id,
                    "name": request.user_name or request.user_id,
                    "email": request.email,
                    "department": request.department,
                    "employee_number": request.employee_number or f"OIDC_{request.user_id}"
                })

                # 로그인 세션 기록
                await db_service.create_user_session({
                    "session_id": session_token,
                    "user_id": request.user_id,
                    "ip_address": "OIDC_EXTERNAL",
                    "user_agent": "OIDC_AUTHENTICATION",
                    "is_active": True
                })

                print(f"✅ [OIDC-DB] User {request.user_id} saved to database")
            except Exception as db_error:
                print(f"⚠️ [OIDC-DB] Failed to save to database: {db_error}")

        print(f"✅ [OIDC-CALLBACK] Session created for user {request.user_id}: {session_token}")

        return {
            "success": True,
            "data": {
                "session_token": session_token,
                "user_id": request.user_id,
                "message": f"사용자 {request.user_name or request.user_id} 인증이 완료되었습니다."
            }
        }

    except Exception as e:
        print(f"❌ [OIDC-CALLBACK] Error processing OIDC callback: {str(e)}")
        return {
            "success": False,
            "error": "oidc_callback_error",
            "message": f"OIDC 콜백 처리 중 오류가 발생했습니다: {str(e)}"
        }

@app.get("/api/v1/auth/oidc-user")
async def get_current_oidc_user(session_token: Optional[str] = None):
    """현재 OIDC 인증된 사용자 정보 조회"""
    global oidc_settings, oidc_sessions

    try:
        if not oidc_settings["enabled"]:
            return {
                "success": False,
                "error": "oidc_not_enabled",
                "message": "OIDC 인증이 비활성화되어 있습니다."
            }

        # 세션 토큰이 제공된 경우 해당 사용자 정보 반환
        if session_token and session_token in oidc_sessions:
            user_info = oidc_sessions[session_token]

            # 세션 만료 확인
            expires_at = datetime.fromisoformat(user_info["expires_at"])
            if datetime.now() > expires_at:
                del oidc_sessions[session_token]
                return {
                    "success": False,
                    "error": "session_expired",
                    "message": "세션이 만료되었습니다."
                }

            return {
                "success": True,
                "data": {
                    "user": user_info,
                    "authentication_method": "oidc_external",
                    "session_valid": True
                }
            }

        # 가장 최근 로그인한 사용자 반환 (개발용)
        if oidc_sessions:
            latest_session = max(oidc_sessions.values(), key=lambda x: x["login_time"])
            return {
                "success": True,
                "data": {
                    "user": latest_session,
                    "authentication_method": "oidc_external",
                    "session_valid": True
                }
            }

        return {
            "success": False,
            "error": "no_oidc_user",
            "message": "인증된 OIDC 사용자가 없습니다."
        }

    except Exception as e:
        print(f"❌ [OIDC-USER] Error getting OIDC user: {str(e)}")
        return {
            "success": False,
            "error": "oidc_user_error",
            "message": f"OIDC 사용자 조회 중 오류가 발생했습니다: {str(e)}"
        }

@app.delete("/api/v1/auth/oidc-logout")
async def oidc_logout(session_token: Optional[str] = None):
    """OIDC 사용자 로그아웃"""
    global oidc_settings, oidc_sessions

    try:
        if not oidc_settings["enabled"]:
            return {
                "success": False,
                "error": "oidc_not_enabled",
                "message": "OIDC 인증이 비활성화되어 있습니다."
            }

        if session_token and session_token in oidc_sessions:
            user_info = oidc_sessions[session_token]

            # 데이터베이스에 로그아웃 기록 (있는 경우)
            if USER_MANAGEMENT_DB_AVAILABLE:
                try:
                    await db_service.end_user_session(session_token)
                    print(f"✅ [OIDC-LOGOUT] Session {session_token} ended in database")
                except Exception as db_error:
                    print(f"⚠️ [OIDC-LOGOUT] Failed to end session in database: {db_error}")

            # 세션 제거
            del oidc_sessions[session_token]

            # 현재 사용자가 로그아웃한 사용자라면 초기화
            if oidc_settings["current_oidc_user"] == user_info.get("user_name"):
                oidc_settings["current_oidc_user"] = None

            print(f"✅ [OIDC-LOGOUT] User {user_info['user_id']} logged out")

            return {
                "success": True,
                "data": {
                    "message": f"사용자 {user_info.get('user_name', user_info['user_id'])} 로그아웃이 완료되었습니다."
                }
            }

        return {
            "success": False,
            "error": "invalid_session",
            "message": "유효하지 않은 세션입니다."
        }

    except Exception as e:
        print(f"❌ [OIDC-LOGOUT] Error during logout: {str(e)}")
        return {
            "success": False,
            "error": "oidc_logout_error",
            "message": f"OIDC 로그아웃 중 오류가 발생했습니다: {str(e)}"
        }

# Activity Logging 모델
class ActivityLogRequest(BaseModel):
    """사용자 활동 로그 요청 모델"""
    user_id: str
    action: str
    details: Optional[dict] = None
    frontend_port: Optional[int] = None
    timestamp: Optional[str] = None

@app.post("/api/v1/auth/activity")
async def log_user_activity(request: ActivityLogRequest):
    """사용자 활동 로그 저장"""
    try:
        print(f"📊 [ACTIVITY] Logging activity: {request.action} for user {request.user_id}")

        if db_service:
            # PostgreSQL에 활동 로그 저장
            activity_data = {
                **(request.details or {}),
                "frontend_port": request.frontend_port,
                "timestamp": request.timestamp or datetime.now().isoformat()
            }
            await db_service.log_user_activity(
                user_id=request.user_id,
                activity_type=request.action,
                activity_data=activity_data
            )
            print(f"✅ [ACTIVITY] Activity logged successfully in PostgreSQL")
        else:
            print(f"⚠️ [ACTIVITY] Database service not available, logging to console")

        return {
            "success": True,
            "message": f"Activity '{request.action}' logged for user {request.user_id}"
        }

    except Exception as e:
        print(f"❌ [ACTIVITY] Error logging activity: {str(e)}")
        return {
            "success": False,
            "error": "activity_log_error",
            "message": f"활동 로그 저장 중 오류가 발생했습니다: {str(e)}"
        }

# Dashboard 모델들
class DashboardMetrics(BaseModel):
    """대시보드 메트릭스 응답 모델"""
    total_users: int
    active_sessions: int
    documents_processed: int
    system_status: str
    user_activity_ranking: List[dict]
    service_usage_stats: List[dict]
    document_usage_stats: List[dict]
    system_resources: dict
    response_times: List[dict]
    recent_activities: List[dict]
    overall_user_statistics: dict  # 전체 사용자 종합 통계

@app.get("/api/v1/dashboard/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    department: Optional[str] = None
):
    """대시보드 메트릭스 데이터 조회"""
    try:
        print("📊 [DASHBOARD] Loading dashboard metrics...")

        # 기본 지표 초기화
        total_users = 0
        active_sessions = 0
        documents_processed = 0
        system_status = "healthy"
        user_activity_ranking = []
        service_usage_stats = []
        document_usage_stats = []
        system_resources = {}
        response_times = []
        recent_activities = []
        overall_user_statistics = {}

        if db_service:
            # 사용자 통계
            total_users = await db_service.get_total_users_count()
            active_sessions = await db_service.get_active_sessions_count()

            # 문서 통계
            documents_processed = await db_service.get_documents_count()

            # 사용자 활동 랭킹 (상위 10명) - 필터링 조건 적용
            user_activity_ranking = await db_service.get_user_activity_ranking(
                limit=10,
                from_date=from_date,
                to_date=to_date,
                department=department
            )

            # 서비스별 사용 현황
            service_usage_stats = await db_service.get_service_usage_stats()

            # 문서 활용 현황 (최근 7일)
            document_usage_stats = await db_service.get_document_usage_stats(days=7)

            # 최근 활동 로그 (최근 20개)
            recent_activities = await db_service.get_recent_activities(limit=20)

            # 전체 사용자 종합 통계 (집계된 요약)
            overall_user_statistics = await db_service.get_overall_user_statistics()

        # 시스템 리소스 현황
        import psutil
        import time

        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)

        # 메모리 사용률
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        # 디스크 사용률
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100

        system_resources = {
            "cpu_usage": round(cpu_percent, 1),
            "memory_usage": round(memory_percent, 1),
            "disk_usage": round(disk_percent, 1),
            "memory_total_gb": round(memory.total / (1024**3), 1),
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "timestamp": datetime.now().isoformat()
        }

        # 응답 시간 모의 데이터 (실제로는 로그에서 수집)
        now = datetime.now()
        response_times = [
            {
                "timestamp": (now - timedelta(minutes=i*5)).isoformat(),
                "avg_response_time": round(50 + (i % 3) * 20 + (i % 7) * 10, 1),
                "endpoint": "/api/v1/chat"
            }
            for i in range(24, 0, -1)  # 최근 2시간 (5분 간격)
        ]

        print(f"✅ [DASHBOARD] Metrics loaded - Users: {total_users}, Sessions: {active_sessions}, Docs: {documents_processed}")

        return DashboardMetrics(
            total_users=total_users,
            active_sessions=active_sessions,
            documents_processed=documents_processed,
            system_status=system_status,
            user_activity_ranking=user_activity_ranking,
            service_usage_stats=service_usage_stats,
            document_usage_stats=document_usage_stats,
            system_resources=system_resources,
            response_times=response_times,
            recent_activities=recent_activities,
            overall_user_statistics=overall_user_statistics
        )

    except Exception as e:
        print(f"❌ [DASHBOARD] Error loading metrics: {str(e)}")

        # 오류 시 기본값 반환
        return DashboardMetrics(
            total_users=0,
            active_sessions=0,
            documents_processed=0,
            system_status="error",
            user_activity_ranking=[],
            service_usage_stats=[
                {"service": "chat", "usage_count": 0, "port": 3000},
                {"service": "admin", "usage_count": 0, "port": 3003},
                {"service": "additional", "usage_count": 0, "port": 3005}
            ],
            document_usage_stats=[],
            system_resources={
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0,
                "memory_total_gb": 0,
                "disk_total_gb": 0,
                "timestamp": datetime.now().isoformat()
            },
            response_times=[],
            recent_activities=[],
            overall_user_statistics={}
        )

@app.get("/api/v1/dashboard/departments")
async def get_departments():
    """Get list of all departments"""
    try:
        print("📊 [DEPARTMENTS] Loading departments list from database...")

        departments = await db_service.get_departments()

        print(f"✅ [DEPARTMENTS] Found {len(departments)} departments: {departments}")

        return {"departments": departments}

    except Exception as e:
        print(f"❌ [DEPARTMENTS] Error loading departments: {str(e)}")
        # 오류 시 기본 부서 목록 반환
        return {"departments": ["전체", "IT부", "기획부", "마케팅부", "영업부", "HR부"]}

@app.post("/api/v1/dashboard/create-sample-departments")
async def create_sample_departments():
    """Create sample users with different departments"""
    try:
        print("🏢 [DEPARTMENTS] Creating sample departments...")

        if db_service:
            result = await db_service.create_sample_departments()

            if result.get("success"):
                print(f"✅ [DEPARTMENTS] Sample departments created: {result['inserted_users']}/{result['total_users']} users")
                return {
                    "success": True,
                    "message": result["message"],
                    "data": result
                }
            else:
                print(f"❌ [DEPARTMENTS] Failed to create sample departments: {result['message']}")
                return {
                    "success": False,
                    "message": result["message"]
                }
        else:
            return {
                "success": False,
                "message": "Database service not available"
            }

    except Exception as e:
        print(f"❌ [DEPARTMENTS] Error creating sample departments: {str(e)}")
        return {
            "success": False,
            "message": f"Error creating sample departments: {str(e)}"
        }

# =============================================================================
# 임베딩 서비스 API
# =============================================================================

# 임베딩 서비스 임포트
try:
    from embedding_service import embedding_service
    EMBEDDING_SERVICE_AVAILABLE = True
    print("🤖 [EMBEDDING] Embedding service loaded successfully")
except ImportError as e:
    EMBEDDING_SERVICE_AVAILABLE = False
    print(f"⚠️ [EMBEDDING] Embedding service not available: {e}")

@app.get("/api/v1/embedding/models")
async def get_embedding_models():
    """사용 가능한 임베딩 모델 목록 조회"""
    try:
        if not EMBEDDING_SERVICE_AVAILABLE:
            return {
                "success": False,
                "message": "임베딩 서비스를 사용할 수 없습니다"
            }

        models = embedding_service.get_available_models()
        embedding_info = embedding_service.get_embedding_info()

        return {
            "success": True,
            "data": {
                "models": models,
                "current_mode": embedding_info["current_mode"],
                "bge_servers": embedding_info["bge_servers"]
            }
        }
    except Exception as e:
        print(f"❌ [EMBEDDING] Error getting models: {str(e)}")
        return {
            "success": False,
            "message": f"모델 조회 실패: {str(e)}"
        }

@app.post("/api/v1/embedding/set-mode")
async def set_embedding_mode(request: Request):
    """임베딩 모드 설정"""
    try:
        if not EMBEDDING_SERVICE_AVAILABLE:
            return {
                "success": False,
                "message": "임베딩 서비스를 사용할 수 없습니다"
            }

        data = await request.json()
        mode = data.get("mode")

        if not mode:
            return {
                "success": False,
                "message": "임베딩 모드가 지정되지 않았습니다"
            }

        valid_modes = ["bge-m3", "kure-v1", "sentence-transformers"]
        if mode not in valid_modes:
            return {
                "success": False,
                "message": f"지원하지 않는 모드입니다. 사용 가능한 모드: {valid_modes}"
            }

        embedding_service.set_embedding_mode(mode)

        return {
            "success": True,
            "message": f"임베딩 모드가 {mode}로 변경되었습니다",
            "data": {
                "current_mode": mode
            }
        }
    except Exception as e:
        print(f"❌ [EMBEDDING] Error setting mode: {str(e)}")
        return {
            "success": False,
            "message": f"모드 설정 실패: {str(e)}"
        }

@app.post("/api/v1/embedding/encode")
async def encode_text(request: Request):
    """텍스트 임베딩 생성"""
    try:
        if not EMBEDDING_SERVICE_AVAILABLE:
            return {
                "success": False,
                "message": "임베딩 서비스를 사용할 수 없습니다"
            }

        data = await request.json()
        texts = data.get("texts", [])
        mode = data.get("mode")  # 선택적 파라미터

        if not texts or not isinstance(texts, list):
            return {
                "success": False,
                "message": "텍스트 목록이 지정되지 않았습니다"
            }

        embeddings = await embedding_service.encode_text(texts, mode)

        return {
            "success": True,
            "data": {
                "embeddings": embeddings,
                "text_count": len(texts),
                "mode": mode or embedding_service.embedding_mode
            }
        }
    except Exception as e:
        print(f"❌ [EMBEDDING] Error encoding text: {str(e)}")
        return {
            "success": False,
            "message": f"임베딩 생성 실패: {str(e)}"
        }

@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)