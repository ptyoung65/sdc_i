#!/usr/bin/env python3
"""
Korean RAG Gemini Response Service - Gemini API를 활용한 한국어 RAG 응답 생성 서비스

🔄 MIGRATION TO LOCAL LLMs PLANNED 🔄
향후 Local LLM 마이그레이션 예정 - 이 파일은 다음과 같이 변경될 예정입니다:

1. Gemini API 대체 대상 모델들:
   - GPT-OSS (Local GPT variants)
   - DeepSeek-R1 (로컬 추론 모델)
   - Gemma3 (Google의 오픈소스 모델)
   - Qwen3 (Alibaba의 다국어 모델)
   - Ollama (로컬 LLM 실행 플랫폼)

2. 주요 변경 영역:
   - import google.generativeai -> ollama, transformers, vllm 등으로 교체
   - GeminiRAGService -> LocalLLMService로 클래스명 변경
   - API 키 기반 인증 -> 로컬 모델 로딩 방식으로 변경
   - 클라우드 API 호출 -> 로컬 추론 호출로 변경

3. 성능 고려사항:
   - GPU 메모리 관리 및 최적화 필요
   - 배치 처리 및 동시성 제어 구현
   - 모델 로딩 시간 최적화 (캐싱, warm-up)
   - 한국어 성능 벤치마킹 및 파인튜닝 고려

4. 인프라 요구사항:
   - CUDA/ROCm GPU 지원 서버
   - 충분한 VRAM (16GB+ 권장)
   - 모델 파일 저장소 (100GB+ SSD)
   - 컨테이너 오케스트레이션 (Docker/Kubernetes)
"""

import os
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

# FastAPI 및 기본 의존성
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# 🔄 LOCAL LLM MIGRATION POINT 1: 라이브러리 임포트 섹션
# 현재: Gemini API 사용
# 향후: 아래와 같이 로컬 LLM 라이브러리로 교체 예정
# 
# import ollama                    # Ollama 로컬 LLM 플랫폼
# import torch                     # PyTorch for model inference
# from transformers import (       # HuggingFace Transformers
#     AutoTokenizer, 
#     AutoModelForCausalLM,
#     pipeline
# )
# import vllm                      # vLLM for optimized inference
# from openai import OpenAI        # OpenAI-compatible local endpoints
#
# LOCAL_LLM_CONFIG = {
#     "ollama": {"host": "localhost", "port": 11434},
#     "vllm": {"host": "localhost", "port": 8000},
#     "model_path": "/models/",  # 로컬 모델 저장 경로
#     "available_models": [
#         "llama2-13b-korean",
#         "gemma-7b-ko", 
#         "qwen-14b-chat",
#         "deepseek-coder-33b"
#     ]
# }
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ google-generativeai 라이브러리가 설치되지 않았습니다. 'pip install google-generativeai' 실행 필요")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Pydantic 모델
class KoreanAnalysis(BaseModel):
    original_query: str
    processed_query: str
    tokenized: List[str]
    keywords: List[str]

class GenerateRequest(BaseModel):
    query: str
    context: str = ""
    korean_analysis: Optional[Union[KoreanAnalysis, Dict[str, Any]]] = None
    user_id: Optional[str] = "default"

class GenerateResponse(BaseModel):
    response: str
    model_used: str
    processing_time: float
    context_length: int
    korean_optimized: bool

class HealthResponse(BaseModel):
    status: str
    gemini_api_available: bool
    model: Optional[str]
    timestamp: str

# 🔄 LOCAL LLM MIGRATION POINT 2: 서비스 클래스 정의
# 현재: GeminiRAGService - Gemini API 기반 서비스
# 향후: LocalLLMService로 클래스명 변경 및 구조 개편
#
# class LocalLLMService:
#     def __init__(self, model_type="ollama"):
#         self.model_type = model_type  # ollama, vllm, transformers
#         self.model_name = None
#         self.model = None
#         self.tokenizer = None
#         self.client = None  # HTTP client for local API
#         self.gpu_available = torch.cuda.is_available()
#         self.model_config = LOCAL_LLM_CONFIG[model_type]
#
class GeminiRAGService:
    def __init__(self):
        self.model = None
        self.model_name = "gemini-1.5-flash"
        self.api_key = None
        self.initialized = False
        
    def initialize(self):
        """🔄 LOCAL LLM MIGRATION POINT 3: 모델 초기화 메소드
        현재: Gemini API 키 기반 초기화
        향후: 로컬 모델 로딩 방식으로 변경
        
        # 로컬 LLM 초기화 예시:
        # def initialize_local_llm(self, model_name="gemma-7b-ko"):
        #     if self.model_type == "ollama":
        #         self.client = ollama.Client(host=self.model_config["host"])
        #         # 모델이 없으면 자동 다운로드
        #         try:
        #             self.client.pull(model_name)
        #         except Exception as e:
        #             logger.warning(f"모델 다운로드 실패: {e}")
        #             
        #     elif self.model_type == "transformers":
        #         self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        #         self.model = AutoModelForCausalLM.from_pretrained(
        #             model_name,
        #             torch_dtype=torch.float16,
        #             device_map="auto" if self.gpu_available else "cpu"
        #         )
        #         
        #     elif self.model_type == "vllm":
        #         # vLLM 서버가 이미 실행 중이라고 가정
        #         self.client = OpenAI(
        #             base_url=f"http://{self.model_config['host']}:{self.model_config['port']}/v1",
        #             api_key="token"  # vLLM에서는 임의 토큰
        #         )
        """
        if not GEMINI_AVAILABLE:
            logger.error("❌ Gemini API 라이브러리가 설치되지 않았습니다.")
            return False
            
        # API 키 확인 (향후 제거 예정 - 로컬 모델에서는 불필요)
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.error("❌ GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
            logger.info("💡 export GEMINI_API_KEY=your_api_key_here")
            return False
        
        try:
            # Gemini API 설정 (향후 로컬 모델 로딩으로 교체)
            genai.configure(api_key=self.api_key)
            
            # 모델 초기화 (향후 로컬 모델 객체로 교체)
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": 0.3,  # 로컬 모델에서도 동일한 설정 유지
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 2048,  # max_new_tokens로 변경 예정
                }
            )
            
            logger.info(f"✅ Gemini API 초기화 완료: {self.model_name}")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Gemini API 초기화 실패: {e}")
            return False
    
    def create_korean_prompt(self, query: str, context: str, korean_analysis: Optional[KoreanAnalysis] = None) -> str:
        """한국어 최적화 프롬프트 생성"""
        
        # 기본 한국어 RAG 프롬프트
        base_prompt = f"""당신은 한국어 문서 기반 질의응답 전문가입니다. 
제공된 문서 내용을 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공하세요.

**답변 지침:**
1. 제공된 문서 내용을 기반으로만 답변하세요
2. 문서에 없는 내용은 추측하지 마세요
3. 한국어로 자연스럽고 정확하게 답변하세요
4. 구체적인 정보와 예시를 포함하세요
5. 만약 문서 내용이 질문과 관련이 없다면 그렇게 알려주세요

**사용자 질문:** {query}

**관련 문서 내용:**
{context}

**답변:**"""

        # 한국어 분석 정보가 있으면 추가
        if korean_analysis:
            korean_info = f"""
**한국어 분석 정보:**
- 처리된 쿼리: {korean_analysis.processed_query}
- 주요 키워드: {', '.join(korean_analysis.keywords)}
- 토큰: {', '.join(korean_analysis.tokenized)}

"""
            # 프롬프트에 한국어 분석 정보 삽입
            base_prompt = base_prompt.replace("**사용자 질문:**", korean_info + "**사용자 질문:**")
        
        return base_prompt
    
    async def generate_response(self, request: GenerateRequest) -> GenerateResponse:
        """🔄 LOCAL LLM MIGRATION POINT 4: 응답 생성 메소드
        현재: Gemini API 호출 기반 응답 생성
        향후: 로컬 LLM 추론 호출로 변경
        
        # 로컬 LLM 응답 생성 예시:
        # async def generate_local_response(self, request: GenerateRequest):
        #     if self.model_type == "ollama":
        #         response = await asyncio.to_thread(
        #             self.client.chat,
        #             model=self.model_name,
        #             messages=[{"role": "user", "content": prompt}],
        #             options={"temperature": 0.3, "top_p": 0.8}
        #         )
        #         return response['message']['content']
        #         
        #     elif self.model_type == "transformers":
        #         inputs = self.tokenizer(prompt, return_tensors="pt")
        #         with torch.no_grad():
        #             outputs = self.model.generate(
        #                 **inputs,
        #                 max_new_tokens=2048,
        #                 temperature=0.3,
        #                 top_p=0.8,
        #                 do_sample=True,
        #                 pad_token_id=self.tokenizer.eos_token_id
        #             )
        #         return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        #         
        #     elif self.model_type == "vllm":
        #         response = await self.client.chat.completions.create(
        #             model=self.model_name,
        #             messages=[{"role": "user", "content": prompt}],
        #             temperature=0.3,
        #             top_p=0.8,
        #             max_tokens=2048
        #         )
        #         return response.choices[0].message.content
        """
        start_time = datetime.now()
        
        # API 키가 없는 경우 fallback 응답 제공
        if not self.initialized:
            logger.warning("Gemini API가 초기화되지 않았습니다. Fallback 응답을 제공합니다.")
            
            # 컨텍스트 기반 간단한 응답 생성
            fallback_response = f"""제공된 문서 내용을 기반으로 답변드리겠습니다.

**질문:** {request.query}

**관련 문서 내용:**
{request.context[:500]}{'...' if len(request.context) > 500 else ''}

**답변:** 
문서 내용을 검토한 결과, 한국어 자연어 처리 시스템과 관련된 정보를 확인할 수 있습니다. 더 정확한 AI 응답을 위해서는 Gemini API 키 설정이 필요합니다.

⚠️ 현재 Gemini API 키가 설정되지 않아 제한된 응답을 제공하고 있습니다. 완전한 AI 응답을 위해 `export GEMINI_API_KEY=your_api_key` 명령으로 API 키를 설정해 주세요."""

            processing_time = (datetime.now() - start_time).total_seconds()
            
            return GenerateResponse(
                response=fallback_response,
                model_used="fallback-mode",
                processing_time=processing_time,
                context_length=len(request.context),
                korean_optimized=False
            )
        
        try:
            # 한국어 최적화 프롬프트 생성
            prompt = self.create_korean_prompt(
                query=request.query,
                context=request.context,
                korean_analysis=request.korean_analysis
            )
            
            # Gemini API 호출
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            # 응답 텍스트 추출
            if response.candidates and len(response.candidates) > 0:
                generated_text = response.candidates[0].content.parts[0].text.strip()
            else:
                generated_text = "죄송합니다. 응답을 생성할 수 없습니다. 다시 시도해 주세요."
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return GenerateResponse(
                response=generated_text,
                model_used=self.model_name,
                processing_time=processing_time,
                context_length=len(request.context),
                korean_optimized=True
            )
            
        except Exception as e:
            logger.error(f"Gemini API 응답 생성 실패: {e}")
            raise HTTPException(status_code=500, detail=f"응답 생성 중 오류 발생: {str(e)}")

# 전역 Gemini 서비스 인스턴스
gemini_service = GeminiRAGService()

# FastAPI 앱 설정
app = FastAPI(
    title="Korean RAG Gemini Service",
    description="Gemini API를 활용한 한국어 RAG 응답 생성 서비스",
    version="1.0.0-gemini"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """서비스 시작 시 Gemini API 초기화"""
    logger.info("🚀 Korean RAG Gemini Service 시작 중...")
    success = gemini_service.initialize()
    if success:
        logger.info("✅ Gemini API 연결 및 모델 로드 완료")
    else:
        logger.warning("⚠️ Gemini API 초기화 실패 - 모의 모드로 실행")

# API 엔드포인트
@app.get("/", response_model=dict)
async def root():
    return {
        "service": "Korean RAG Gemini Service",
        "version": "1.0.0-gemini",
        "status": "running",
        "description": "Gemini API를 활용한 한국어 RAG 응답 생성 서비스",
        "features": [
            "Gemini 1.5 Flash 모델",
            "한국어 최적화 프롬프트",
            "컨텍스트 기반 응답 생성",
            "한국어 분석 정보 활용"
        ]
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy" if gemini_service.initialized else "degraded",
        gemini_api_available=gemini_service.initialized,
        model=gemini_service.model_name if gemini_service.initialized else None,
        timestamp=datetime.now().isoformat()
    )

@app.post("/generate", response_model=GenerateResponse)
async def generate_response(request: GenerateRequest):
    """
    컨텍스트를 기반으로 Gemini API를 사용하여 한국어 응답 생성
    """
    try:
        # 입력 검증
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="쿼리가 비어있습니다.")
        
        # 컨텍스트는 빈 문자열도 허용 (일반 질의응답 모드)
        
        # Gemini API로 응답 생성
        response = await gemini_service.generate_response(request)
        
        logger.info(f"✅ 응답 생성 완료 - 사용자: {request.user_id}, 처리시간: {response.processing_time:.3f}s")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"응답 생성 API 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """서비스 통계 정보"""
    return {
        "service": "Korean RAG Gemini Service",
        "gemini": {
            "available": gemini_service.initialized,
            "model": gemini_service.model_name,
            "api_key_configured": bool(gemini_service.api_key)
        },
        "features": {
            "korean_optimization": True,
            "context_based_generation": True,
            "multilingual": True
        },
        "version": "1.0.0-gemini"
    }

if __name__ == "__main__":
    print("🚀 Korean RAG Gemini Service 시작 중...")
    print("📍 Gemini API 기반 한국어 응답 생성 서비스")
    print("🔗 Running on http://0.0.0.0:8009")
    print("✅ 컨텍스트 기반 응답 생성, 한국어 최적화")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8009,
        log_level="info"
    )