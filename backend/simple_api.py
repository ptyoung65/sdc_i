"""
Simplified API with RAG integration for document-based chat
"""
from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import os
from datetime import datetime, timedelta
import uuid
import google.generativeai as genai
import asyncio
from dotenv import load_dotenv

# RAG service imports
try:
    from app.services.ai.rag_service import RAGService, RAGStrategy
    from app.services.document import DocumentService
    from app.core.database import get_db, create_tables
    from sqlalchemy.ext.asyncio import AsyncSession
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

# .env 파일 로드
load_dotenv()

# Gemini AI 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
app = FastAPI(title="SDC Backend - Simple", version="0.1.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://192.168.122.177:3000",
        "http://192.168.0.14:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple models
class ChatRequest(BaseModel):
    message: str
    provider: Optional[str] = "gemini"
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
    rating: int
    feedback: Optional[str] = None

# Mock data storage
conversations_db = {}
messages_db = {}
ratings_db = {}
user_documents = {}  # 사용자별 업로드된 문서 저장소

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
            error_msg = f"AI 서비스 오류가 발생했습니다: {str(e)}"
            print(f"❌ [GEMINI] Exception occurred: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"📊 [GEMINI] Full traceback:\n{traceback.format_exc()}")
            return error_msg
    
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
        enabled_rag_types: Dict[str, bool] = None
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
                            response = await self.generate_gemini_response(enhanced_message, provider, conversation_history)
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
            response = await self.generate_gemini_response(enhanced_message, provider, conversation_history)
            
            # 생성 단계 추적 완료
            if rag_tracker:
                rag_tracker.end_generation(response, provider or "gemini")
            
            return {"response": response, "sources": all_sources}
        
        # 기본 AI 응답
        print(f"🤖 [AI] Using basic AI response")
        
        # 생성 단계 추적 시작 (기본 응답의 경우)
        if rag_tracker:
            rag_tracker.start_generation()
        
        if provider == "gemini":
            response = await self.generate_gemini_response(message, provider, conversation_history)
        elif provider == "claude":
            response = "Claude API는 아직 구현되지 않았습니다. Gemini를 사용해주세요."
        elif provider == "openai":
            response = "OpenAI API는 아직 구현되지 않았습니다. Gemini를 사용해주세요."
        else:
            response = await self.generate_gemini_response(message, "gemini", conversation_history)
        
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
                    response = await self.generate_gemini_response(
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
                    
                    response = await self.generate_gemini_response(context_prompt, provider, conversation_history)
                    
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
                combined_response = await self.generate_gemini_response(
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
            basic_response = await self.generate_gemini_response(message, provider, conversation_history)
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
                response = await self.generate_gemini_response(message, provider, conversation_history)
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
                
                response = await self.generate_gemini_response(enhanced_message, provider, conversation_history)
                
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
                response = await self.generate_gemini_response(message, provider, conversation_history)
                return {"response": response, "sources": []}
                
        except Exception as e:
            print(f"❌ [SIMPLE-RAG] Error in simple document search: {str(e)}")
            import traceback
            print(f"📊 [SIMPLE-RAG] Full traceback: {traceback.format_exc()}")
            
            # 실패시 기본 AI로 fallback
            print(f"🔄 [SIMPLE-RAG] Falling back to basic AI response")
            response = await self.generate_gemini_response(message, provider, conversation_history)
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
            response = await self.generate_gemini_response(enhanced_message, provider, conversation_history)
            return {"response": response, "sources": all_sources}
        
        # 기본 AI 응답
        response = await self.generate_gemini_response(message, provider, conversation_history)
        return {"response": response, "sources": []}

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
                "available": bool(os.getenv("GEMINI_API_KEY")),
                "models": ["gemini-pro"]
            },
            {
                "name": "claude",
                "display_name": "Anthropic Claude",
                "available": bool(os.getenv("ANTHROPIC_API_KEY")),
                "models": ["claude-3-sonnet"]
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

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """채팅 엔드포인트 - 실제 AI를 사용한 대화 생성"""
    print(f"\n🎯 [CHAT] New chat request received")
    print(f"📝 [CHAT] Message: {request.message[:50]}...")
    print(f"🤖 [CHAT] Provider: {request.provider}")
    print(f"👤 [CHAT] User: {request.user_id}")
    print(f"💬 [CHAT] Conversation ID: {request.conversation_id}")
    print(f"📚 [CHAT] History length: {len(request.conversation_history) if request.conversation_history else 0}")
    
    try:
        # 대화 ID 생성 또는 기존 대화 사용
        conv_id = request.conversation_id or f"conv-{str(uuid.uuid4())[:8]}"
        msg_id = f"msg-{str(uuid.uuid4())[:8]}"
        
        print(f"🆔 [CHAT] Final conversation ID: {conv_id}")
        print(f"🆔 [CHAT] Message ID: {msg_id}")
        
        # 사용자 입력 안전성 검증 (Guardrails)
        if GUARDRAILS_AVAILABLE:
            print(f"🛡️ [GUARDRAILS] Validating user input...")
            is_safe, filtered_or_reason = await validate_user_input(
                request.message, 
                request.user_id or "default_user"
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
            print(f"⚠️ [GUARDRAILS] Validation skipped - service unavailable")
        
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

        # 실제 AI 응답 생성 (RAG 및 웹 검색 지원)
        print(f"🚀 [CHAT] Calling AI service with RAG and web search support...")
        ai_result = await ai_service.generate_response(
            message=validated_message,
            provider=request.provider or "gemini",
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
                request.user_id or "default_user"
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
    """메시지 평점 저장"""
    rating_key = f"{request.message_id}_{request.user_id}"
    ratings_db[rating_key] = {
        "message_id": request.message_id,
        "user_id": request.user_id,
        "rating": request.rating,
        "feedback": request.feedback,
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
        return {"rating": None, "feedback": None}

# Document upload endpoints
@app.post("/api/v1/documents")
async def upload_document_default(
    file: UploadFile = File(...),
    user_id: str = Form(default="default_user")
):
    """문서 업로드 엔드포인트 - 프론트엔드 기본 경로 (Multi-format support with Docling)"""
    print(f"📄 [UPLOAD] Document upload request: filename={file.filename}, user_id={user_id}")
    
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
    
    # Check if this is a structured document that needs Docling processing
    structured_formats = {'pdf', 'ppt', 'pptx', 'xlsx', 'xls', 'doc', 'docx'}
    
    if DOCLING_AVAILABLE and file_extension in structured_formats:
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
        "upload_time": datetime.now().isoformat()
    }
    
    # 전역 documents 저장소에 추가 (실제 구현에서는 데이터베이스에 저장)
    if user_id not in user_documents:
        user_documents[user_id] = []
    user_documents[user_id].append(temp_document)
    
    print(f"📄 [UPLOAD] Document {doc_id} stored for user {user_id}")
    
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
            return 1  # 문서를 찾을 수 없으면 기본값 1
        
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

@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok"}

# ==================== 평가 데이터 API ====================
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi.responses import StreamingResponse
import io
import csv

def get_pg_connection():
    """PostgreSQL 연결"""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB", "sdc_dev"),
        user=os.getenv("POSTGRES_USER", "sdc_dev_user"),
        password=os.getenv("POSTGRES_PASSWORD", "sdc_dev_pass_2025")
    )

@app.get("/api/evaluations")
async def get_evaluations(
    limit: int = 100,
    offset: int = 0,
    rating: Optional[str] = None  # "good", "bad", or None for all
):
    """
    평가 데이터 조회 API
    - limit: 조회할 데이터 수 (기본 100)
    - offset: 시작 위치 (기본 0)
    - rating: 평가 필터 ("good", "bad", None)
    """
    try:
        conn = get_pg_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 기본 쿼리
        query = """
            SELECT
                f.id,
                f.user_id,
                u.name as user_name,
                f.data->>'model_id' as model_id,
                f.snapshot->'chat'->'chat'->'messages' as messages,
                f.data->>'rating' as rating,
                f.data->>'reason' as reason,
                f.data->>'comment' as comment,
                f.created_at
            FROM feedback f
            LEFT JOIN "user" u ON f.user_id = u.id
            WHERE f.type = 'rating'
        """

        # 평가 필터 추가
        if rating == "good":
            query += " AND (f.data->>'rating')::int = 1"
        elif rating == "bad":
            query += " AND (f.data->>'rating')::int = -1"

        query += " ORDER BY f.created_at DESC LIMIT %s OFFSET %s"

        cursor.execute(query, (limit, offset))
        results = cursor.fetchall()

        # 데이터 가공
        evaluations = []
        for row in results:
            # 메시지 추출
            messages = row.get('messages', [])
            user_message = ""
            assistant_message = ""

            if isinstance(messages, list) and len(messages) > 0:
                # 사용자 메시지 찾기
                for msg in messages:
                    if isinstance(msg, dict):
                        if msg.get('role') == 'user':
                            user_message = msg.get('content', '')
                        elif msg.get('role') == 'assistant':
                            assistant_message = msg.get('content', '')

            # 평가 타입 변환
            rating_value = row.get('rating')
            evaluation_type = "bad" if rating_value == '-1' or rating_value == -1 else "good" if rating_value == '1' or rating_value == 1 else "unknown"

            # 평가 일시 변환 (Unix timestamp to datetime)
            created_timestamp = row.get('created_at', 0)
            created_at = datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d %H:%M:%S') if created_timestamp else ''

            evaluations.append({
                "id": row.get('id'),
                "model": row.get('model_id', 'N/A'),
                "user_name": row.get('user_name', 'Unknown'),
                "user_id": row.get('user_id', 'N/A'),
                "user_message": user_message,
                "assistant_message": assistant_message,
                "evaluation": evaluation_type,
                "reason": row.get('reason', ''),
                "comment": row.get('comment', ''),
                "created_at": created_at
            })

        cursor.close()
        conn.close()

        return {
            "success": True,
            "total": len(evaluations),
            "data": evaluations
        }

    except Exception as e:
        print(f"❌ [EVALUATIONS] Error fetching evaluations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/evaluations/csv")
async def download_evaluations_csv():
    """
    평가 데이터를 CSV로 다운로드
    """
    try:
        conn = get_pg_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 전체 데이터 조회
        query = """
            SELECT
                f.id,
                f.user_id,
                u.name as user_name,
                f.data->>'model_id' as model_id,
                f.snapshot->'chat'->'chat'->'messages' as messages,
                f.data->>'rating' as rating,
                f.data->>'reason' as reason,
                f.data->>'comment' as comment,
                f.created_at
            FROM feedback f
            LEFT JOIN "user" u ON f.user_id = u.id
            WHERE f.type = 'rating'
            ORDER BY f.created_at DESC
        """

        cursor.execute(query)
        results = cursor.fetchall()

        # CSV 생성
        output = io.StringIO()
        csv_writer = csv.writer(output)

        # 헤더
        csv_writer.writerow([
            '모델 구분',
            '사용자명',
            '사용자 ID',
            '메시지 입력 내용',
            '응답 내용',
            'Good/Bad',
            '평가 입력 종류',
            '평가 입력 상세내용',
            '평가 일시'
        ])

        # 데이터
        for row in results:
            # 메시지 추출
            messages = row.get('messages', [])
            user_message = ""
            assistant_message = ""

            if isinstance(messages, list) and len(messages) > 0:
                for msg in messages:
                    if isinstance(msg, dict):
                        if msg.get('role') == 'user':
                            user_message = msg.get('content', '')
                        elif msg.get('role') == 'assistant':
                            assistant_message = msg.get('content', '')

            # 평가 타입 변환
            rating_value = row.get('rating')
            evaluation_type = "Bad" if rating_value == '-1' or rating_value == -1 else "Good" if rating_value == '1' or rating_value == 1 else "Unknown"

            # 평가 일시 변환
            created_timestamp = row.get('created_at', 0)
            created_at = datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d %H:%M:%S') if created_timestamp else ''

            csv_writer.writerow([
                row.get('model_id', 'N/A'),
                row.get('user_name', 'Unknown'),
                row.get('user_id', 'N/A'),
                user_message,
                assistant_message,
                evaluation_type,
                row.get('reason', ''),
                row.get('comment', ''),
                created_at
            ])

        cursor.close()
        conn.close()

        # CSV 다운로드 응답
        output.seek(0)

        # UTF-8 BOM 추가 (Excel에서 한글 깨짐 방지)
        csv_content = '\ufeff' + output.getvalue()

        return StreamingResponse(
            iter([csv_content.encode('utf-8')]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=evaluations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )

    except Exception as e:
        print(f"❌ [EVALUATIONS-CSV] Error generating CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# Evaluations2 API (신규)
# ========================================

@app.get("/api/v1/evaluations2/feedbacks/all/detailed")
async def get_all_detailed_feedbacks():
    """
    평가 데이터 상세 조회 API (Evaluations2 페이지용)
    - 모든 평가 데이터를 상세하게 반환
    """
    try:
        conn = get_pg_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 전체 데이터 조회
        query = """
            SELECT
                f.id,
                f.user_id,
                u.name as user_name,
                f.data->>'model_id' as model_id,
                f.snapshot->'chat'->'chat'->'messages' as messages,
                f.data->>'rating' as rating,
                f.data->>'reason' as reason,
                f.data->>'comment' as comment,
                f.created_at
            FROM feedback f
            LEFT JOIN "user" u ON f.user_id = u.id
            WHERE f.type = 'rating'
            ORDER BY f.created_at DESC
        """

        cursor.execute(query)
        results = cursor.fetchall()

        # 데이터 가공
        evaluations = []
        for row in results:
            # 메시지 추출
            messages = row.get('messages', [])
            user_message = ""
            assistant_message = ""

            if isinstance(messages, list) and len(messages) > 0:
                for msg in messages:
                    if isinstance(msg, dict):
                        if msg.get('role') == 'user':
                            user_message = msg.get('content', '')
                        elif msg.get('role') == 'assistant':
                            assistant_message = msg.get('content', '')

            # 평가 타입 변환
            rating_value = row.get('rating')
            evaluation_type = "bad" if rating_value == '-1' or rating_value == -1 else "good" if rating_value == '1' or rating_value == 1 else "unknown"

            # 평가 일시 변환
            created_timestamp = row.get('created_at', 0)
            created_at = datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d %H:%M:%S') if created_timestamp else ''

            evaluations.append({
                "id": row.get('id'),
                "model": row.get('model_id', 'N/A'),
                "user_name": row.get('user_name', 'Unknown'),
                "user_id": row.get('user_id', 'N/A'),
                "user_message": user_message,
                "assistant_message": assistant_message,
                "evaluation": evaluation_type,
                "reason": row.get('reason', ''),
                "comment": row.get('comment', ''),
                "created_at": created_at
            })

        cursor.close()
        conn.close()

        return evaluations

    except Exception as e:
        print(f"❌ [EVALUATIONS2] Error fetching detailed feedbacks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/evaluations2/feedbacks/all/csv")
async def export_all_feedbacks_csv():
    """
    평가 데이터를 CSV로 다운로드 (Evaluations2 페이지용)
    """
    try:
        conn = get_pg_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 전체 데이터 조회
        query = """
            SELECT
                f.id,
                f.user_id,
                u.name as user_name,
                f.data->>'model_id' as model_id,
                f.snapshot->'chat'->'chat'->'messages' as messages,
                f.data->>'rating' as rating,
                f.data->>'reason' as reason,
                f.data->>'comment' as comment,
                f.created_at
            FROM feedback f
            LEFT JOIN "user" u ON f.user_id = u.id
            WHERE f.type = 'rating'
            ORDER BY f.created_at DESC
        """

        cursor.execute(query)
        results = cursor.fetchall()

        # CSV 생성
        output = io.StringIO()
        csv_writer = csv.writer(output)

        # 헤더
        csv_writer.writerow([
            'ID',
            'Model',
            'User Name',
            'User ID',
            'User Message',
            'Assistant Message',
            'Evaluation',
            'Reason',
            'Comment',
            'Created At'
        ])

        # 데이터
        for row in results:
            # 메시지 추출
            messages = row.get('messages', [])
            user_message = ""
            assistant_message = ""

            if isinstance(messages, list) and len(messages) > 0:
                for msg in messages:
                    if isinstance(msg, dict):
                        if msg.get('role') == 'user':
                            user_message = msg.get('content', '')
                        elif msg.get('role') == 'assistant':
                            assistant_message = msg.get('content', '')

            # 평가 타입 변환
            rating_value = row.get('rating')
            evaluation_type = "Bad" if rating_value == '-1' or rating_value == -1 else "Good" if rating_value == '1' or rating_value == 1 else "Unknown"

            # 평가 일시 변환
            created_timestamp = row.get('created_at', 0)
            created_at = datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d %H:%M:%S') if created_timestamp else ''

            csv_writer.writerow([
                row.get('id'),
                row.get('model_id', 'N/A'),
                row.get('user_name', 'Unknown'),
                row.get('user_id', 'N/A'),
                user_message,
                assistant_message,
                evaluation_type,
                row.get('reason', ''),
                row.get('comment', ''),
                created_at
            ])

        cursor.close()
        conn.close()

        # CSV 다운로드 응답
        output.seek(0)

        # UTF-8 BOM 추가 (Excel에서 한글 깨짐 방지)
        csv_content = '\ufeff' + output.getvalue()

        return StreamingResponse(
            iter([csv_content.encode('utf-8')]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=evaluations2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )

    except Exception as e:
        print(f"❌ [EVALUATIONS2-CSV] Error generating CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)