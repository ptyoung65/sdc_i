# 🔄 Local LLM Migration Guide (Gemini → Local LLMs)

## 개요

현재 SDC (Smart Document Companion) 프로젝트에서 사용 중인 Google Gemini API를 오픈소스 로컬 LLM으로 마이그레이션하기 위한 상세 가이드입니다. 이 문서는 단계별 마이그레이션 방법, 수정해야 할 코드, 그리고 인프라 요구사항을 다룹니다.

## 목표 LLM 플랫폼

### 1. 🦙 Ollama (권장 - 시작하기 좋음)
- **장점**: 설치 및 관리가 간단, GPU/CPU 자동 감지, 다양한 모델 지원
- **적합한 용도**: 프로토타이핑, 개발 환경, 중소규모 운영
- **GPU 요구사항**: 8GB+ VRAM 권장 (CPU 모드도 가능)

### 2. ⚡ vLLM (권장 - 프로덕션용)
- **장점**: 높은 처리량, 배치 처리 최적화, OpenAI 호환 API
- **적합한 용도**: 대규모 운영, 높은 동시성 요구
- **GPU 요구사항**: 16GB+ VRAM 필수

### 3. 🤗 HuggingFace Transformers (고급 사용자용)
- **장점**: 최대 제어권, 커스텀 파인튜닝 가능, 최신 모델 지원
- **적합한 용도**: 연구, 커스텀 모델, 세밀한 제어 필요
- **GPU 요구사항**: 모델에 따라 다름 (8-80GB VRAM)

### 4. 🧠 추천 모델들
- **한국어 특화**: `nlpai-lab/kullm-polyglot-12.8b-v2`, `beomi/KoAlpaca-Polyglot-12.8B`
- **다국어**: `microsoft/Phi-3-medium-4k-instruct`, `google/gemma-2-9b-it`
- **경량 모델**: `microsoft/Phi-3-mini-4k-instruct`, `google/gemma-2-2b-it`
- **대형 모델**: `meta-llama/Llama-3.1-70B-Instruct`, `Qwen/Qwen2.5-72B-Instruct`

---

## 📁 수정해야 할 파일 목록

### 🎯 핵심 서비스 파일 (우선순위 높음)

#### 1. `services/korean-rag-gemini-service.py` 
**역할**: Gemini API 기반 응답 생성 서비스  
**변경점**: 전체 구조 변경 필요
- 클래스명: `GeminiRAGService` → `LocalLLMService`
- 라이브러리 import 변경
- 초기화 방식 완전 변경 (API 키 → 로컬 모델 로딩)
- 응답 생성 로직 변경

#### 2. `services/korean-rag-orchestrator.py`
**역할**: RAG 파이프라인 오케스트레이터  
**변경점**: LLM 서비스 호출부 수정
- 서비스 URL 변경 (Port 8009 유지 또는 변경)
- HTTP 클라이언트 호출 파라미터 조정
- 타임아웃 설정 최적화 (로컬 LLM은 더 빠름)

#### 3. `backend/simple_api.py`
**역할**: 메인 백엔드 API  
**변경점**: Gemini 호출 메소드들 수정
- `generate_gemini_response()` → `generate_local_llm_response()`
- provider 파라미터 확장 ("gemini" → "ollama", "vllm", "transformers")
- 모델 초기화 및 응답 생성 로직 변경

### 🔧 환경 설정 파일

#### 4. `requirements.txt` / `requirements-minimal.txt`
**추가해야 할 의존성**:
```bash
# Ollama
ollama>=0.3.0

# vLLM (선택적)
vllm>=0.6.0
openai>=1.0.0  # vLLM OpenAI 호환 API용

# Transformers (선택적)
torch>=2.0.0
transformers>=4.40.0
accelerate>=0.29.0
bitsandbytes>=0.43.0  # 양자화용
```

#### 5. `.env` 파일
**환경 변수 추가**:
```bash
# LLM 서비스 설정
LLM_SERVICE_TYPE=ollama  # ollama, vllm, transformers
LLM_MODEL_NAME=gemma-2-9b-it
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
VLLM_HOST=localhost
VLLM_PORT=8000

# GPU 설정
CUDA_VISIBLE_DEVICES=0
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

# 모델 경로
LOCAL_MODELS_PATH=/models
HUGGINGFACE_CACHE_DIR=/cache/huggingface
```

#### 6. `docker-compose.yml` (선택적)
**새로운 서비스 추가**:
```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  vllm:
    image: vllm/vllm-openai:latest
    ports:
      - "8000:8000"
    environment:
      - CUDA_VISIBLE_DEVICES=0
    volumes:
      - /models:/models
    command: >
      --model /models/gemma-2-9b-it
      --served-model-name gemma-2-9b-it
      --host 0.0.0.0
      --port 8000
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  ollama_data:
```

---

## 🔄 상세 코드 변경 사항

### 1. 라이브러리 임포트 변경

**기존 (`services/korean-rag-gemini-service.py`)**:
```python
# Gemini API
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
```

**변경 후**:
```python
# Local LLM 라이브러리들
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from openai import OpenAI  # vLLM OpenAI 호환 API
    OPENAI_CLIENT_AVAILABLE = True
except ImportError:
    OPENAI_CLIENT_AVAILABLE = False

# LLM 서비스 설정
LLM_SERVICE_TYPE = os.getenv("LLM_SERVICE_TYPE", "ollama")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemma-2-9b-it")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
VLLM_HOST = os.getenv("VLLM_HOST", "localhost")
VLLM_PORT = os.getenv("VLLM_PORT", "8000")
```

### 2. 서비스 클래스 구조 변경

**기존**:
```python
class GeminiRAGService:
    def __init__(self):
        self.model = None
        self.model_name = "gemini-1.5-flash"
        self.api_key = None
        self.initialized = False
```

**변경 후**:
```python
class LocalLLMService:
    def __init__(self, service_type=None):
        self.service_type = service_type or LLM_SERVICE_TYPE
        self.model_name = LLM_MODEL_NAME
        self.model = None
        self.tokenizer = None
        self.client = None
        self.gpu_available = torch.cuda.is_available() if TRANSFORMERS_AVAILABLE else False
        self.initialized = False
        
        # 서비스별 설정
        if self.service_type == "ollama":
            self.client_config = {"host": f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"}
        elif self.service_type == "vllm":
            self.client_config = {"base_url": f"http://{VLLM_HOST}:{VLLM_PORT}/v1"}
        elif self.service_type == "transformers":
            self.client_config = {"device_map": "auto" if self.gpu_available else "cpu"}
```

### 3. 초기화 메소드 변경

**기존**:
```python
def initialize(self):
    """Gemini API 초기화"""
    if not GEMINI_AVAILABLE:
        return False
    
    self.api_key = os.getenv("GEMINI_API_KEY")
    if not self.api_key:
        return False
    
    genai.configure(api_key=self.api_key)
    self.model = genai.GenerativeModel(self.model_name)
    self.initialized = True
    return True
```

**변경 후**:
```python
def initialize(self):
    """로컬 LLM 초기화"""
    try:
        if self.service_type == "ollama":
            if not OLLAMA_AVAILABLE:
                logger.error("Ollama 라이브러리가 설치되지 않았습니다.")
                return False
            
            self.client = ollama.Client(host=self.client_config["host"])
            
            # 모델이 없으면 자동 다운로드
            try:
                self.client.show(self.model_name)
            except:
                logger.info(f"모델 {self.model_name} 다운로드 시작...")
                self.client.pull(self.model_name)
                
        elif self.service_type == "vllm":
            if not OPENAI_CLIENT_AVAILABLE:
                logger.error("OpenAI 클라이언트 라이브러리가 설치되지 않았습니다.")
                return False
            
            self.client = OpenAI(
                base_url=self.client_config["base_url"],
                api_key="token"  # vLLM에서는 임의 토큰 사용
            )
            
        elif self.service_type == "transformers":
            if not TRANSFORMERS_AVAILABLE:
                logger.error("Transformers 라이브러리가 설치되지 않았습니다.")
                return False
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.gpu_available else torch.float32,
                device_map=self.client_config["device_map"]
            )
            
        self.initialized = True
        logger.info(f"✅ {self.service_type} LLM 초기화 완료: {self.model_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ LLM 초기화 실패: {e}")
        return False
```

### 4. 응답 생성 메소드 변경

**기존**:
```python
async def generate_response(self, request: GenerateRequest) -> GenerateResponse:
    prompt = self.create_korean_prompt(
        query=request.query,
        context=request.context,
        korean_analysis=request.korean_analysis
    )
    
    response = await asyncio.to_thread(
        self.model.generate_content,
        prompt
    )
    
    generated_text = response.candidates[0].content.parts[0].text.strip()
    return GenerateResponse(response=generated_text, ...)
```

**변경 후**:
```python
async def generate_response(self, request: GenerateRequest) -> GenerateResponse:
    prompt = self.create_korean_prompt(
        query=request.query,
        context=request.context,
        korean_analysis=request.korean_analysis
    )
    
    if self.service_type == "ollama":
        response = await asyncio.to_thread(
            self.client.chat,
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": 0.3,
                "top_p": 0.8,
                "num_ctx": 8192  # 컨텍스트 길이
            }
        )
        generated_text = response['message']['content']
        
    elif self.service_type == "vllm":
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            top_p=0.8,
            max_tokens=2048
        )
        generated_text = response.choices[0].message.content
        
    elif self.service_type == "transformers":
        inputs = self.tokenizer(prompt, return_tensors="pt")
        if self.gpu_available:
            inputs = {k: v.cuda() for k, v in inputs.items()}
            
        with torch.no_grad():
            outputs = await asyncio.to_thread(
                self.model.generate,
                **inputs,
                max_new_tokens=2048,
                temperature=0.3,
                top_p=0.8,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        generated_text = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:], 
            skip_special_tokens=True
        )
    
    return GenerateResponse(
        response=generated_text,
        model_used=f"{self.service_type}:{self.model_name}",
        processing_time=processing_time,
        korean_optimized=True
    )
```

### 5. 백엔드 API 메소드 변경

**기존 (`backend/simple_api.py`)**:
```python
async def generate_gemini_response(self, message: str, provider: str = "gemini"):
    if not GEMINI_API_KEY:
        return "Gemini API 키가 설정되지 않았습니다."
    
    model = genai.GenerativeModel(self.gemini_model_name)
    response = await asyncio.to_thread(model.generate_content, message)
    return response.candidates[0].content.parts[0].text.strip()
```

**변경 후**:
```python
async def generate_local_llm_response(self, message: str, provider: str = "ollama"):
    """로컬 LLM을 사용한 응답 생성"""
    
    # provider에 따라 다른 서비스 사용
    if provider == "ollama":
        if not OLLAMA_AVAILABLE:
            return "Ollama가 설치되지 않았습니다."
        
        client = ollama.Client(host=f"http://{OLLAMA_HOST}:{OLLAMA_PORT}")
        response = await asyncio.to_thread(
            client.chat,
            model=LLM_MODEL_NAME,
            messages=[{"role": "user", "content": message}]
        )
        return response['message']['content']
        
    elif provider == "vllm":
        if not OPENAI_CLIENT_AVAILABLE:
            return "OpenAI 클라이언트가 설치되지 않았습니다."
        
        client = OpenAI(base_url=f"http://{VLLM_HOST}:{VLLM_PORT}/v1")
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=LLM_MODEL_NAME,
            messages=[{"role": "user", "content": message}]
        )
        return response.choices[0].message.content
        
    elif provider == "transformers":
        # Transformers 직접 호출 로직
        return await self._generate_with_transformers(message)
    
    else:
        return f"지원하지 않는 provider: {provider}"

# 기존 호출을 모두 변경
# generate_gemini_response → generate_local_llm_response
```

### 6. 서비스 URL 설정 변경

**기존 (`services/korean-rag-orchestrator.py`)**:
```python
KOREAN_RAG_SERVICE_URL = "http://localhost:8009"
```

**변경 후**:
```python
# 환경 변수로 관리
KOREAN_RAG_SERVICE_URL = os.getenv("KOREAN_RAG_SERVICE_URL", "http://localhost:8009")
LLM_SERVICE_TYPE = os.getenv("LLM_SERVICE_TYPE", "ollama")

# 서비스 타입에 따라 다른 URL 사용 (선택적)
if LLM_SERVICE_TYPE == "ollama":
    OLLAMA_SERVICE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
elif LLM_SERVICE_TYPE == "vllm":
    VLLM_SERVICE_URL = f"http://{VLLM_HOST}:{VLLM_PORT}"
```

---

## 🚀 단계별 마이그레이션 프로세스

### Phase 1: 준비 및 설치 (1-2일)
1. **인프라 준비**
   ```bash
   # GPU 확인
   nvidia-smi
   
   # Docker 및 NVIDIA Container Toolkit 설치
   sudo apt update
   sudo apt install docker.io nvidia-docker2
   
   # Ollama 설치 (가장 쉬운 시작)
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **의존성 설치**
   ```bash
   # 가상환경 활성화
   source venv/bin/activate
   
   # 로컬 LLM 라이브러리 설치
   pip install ollama torch transformers accelerate
   pip install openai  # vLLM용
   ```

3. **모델 다운로드**
   ```bash
   # Ollama로 모델 설치
   ollama pull gemma2:9b
   ollama pull llama3.1:8b
   
   # 한국어 모델 (HuggingFace에서)
   huggingface-cli download beomi/KoAlpaca-Polyglot-12.8B
   ```

### Phase 2: 서비스 구현 (3-5일)
1. **새 서비스 파일 생성**
   ```bash
   # 기존 파일 백업
   cp services/korean-rag-gemini-service.py services/korean-rag-gemini-service.py.backup
   
   # 새 서비스 구현
   # → LocalLLMService 클래스로 교체
   ```

2. **설정 파일 업데이트**
   - `.env` 파일에 로컬 LLM 설정 추가
   - `requirements.txt` 업데이트
   - `docker-compose.yml`에 Ollama/vLLM 서비스 추가

3. **백엔드 API 수정**
   - `generate_gemini_response` 메소드 수정
   - Provider 파라미터 확장
   - 오류 처리 로직 업데이트

### Phase 3: 테스트 및 최적화 (2-3일)
1. **기능 테스트**
   ```bash
   # 서비스 시작
   python services/korean-rag-local-llm-service.py
   
   # 백엔드 테스트
   curl -X POST http://localhost:8000/api/v1/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "안녕하세요", "provider": "ollama"}'
   ```

2. **성능 벤치마크**
   - 응답 시간 측정
   - 메모리 사용량 모니터링
   - 동시 요청 처리 능력 테스트

3. **한국어 성능 평가**
   - 기존 Gemini 응답과 품질 비교
   - 한국어 특화 태스크 테스트

### Phase 4: 프로덕션 배포 (1-2일)
1. **환경 설정 최종화**
   - 프로덕션 환경 변수 설정
   - Docker 컨테이너 최적화
   - GPU 자원 할당 설정

2. **모니터링 설정**
   - GPU 사용률 모니터링
   - 모델 로딩 시간 추적
   - 응답 품질 메트릭 수집

3. **롤백 계획**
   - 기존 Gemini 서비스 유지 (fallback)
   - 점진적 트래픽 이전
   - 성능 문제 시 즉시 롤백 가능

---

## 🔧 인프라 요구사항

### 하드웨어 권장 사양

#### 최소 사양 (개발/테스트용)
- **CPU**: 8코어 이상
- **RAM**: 32GB 이상
- **GPU**: NVIDIA RTX 3080 (10GB VRAM) 또는 동급
- **저장공간**: 500GB SSD (모델 저장용)
- **네트워크**: 1Gbps

#### 권장 사양 (프로덕션용)
- **CPU**: 16코어 이상 (AMD EPYC 또는 Intel Xeon)
- **RAM**: 64GB 이상
- **GPU**: NVIDIA A40/A100 (24GB+ VRAM) 또는 RTX 4090
- **저장공간**: 2TB NVMe SSD
- **네트워크**: 10Gbps

#### 대규모 운영 사양
- **CPU**: 32코어 이상
- **RAM**: 128GB 이상
- **GPU**: 2x NVIDIA A100 (80GB) 또는 4x RTX 4090
- **저장공간**: 10TB NVMe SSD (RAID 구성)
- **네트워크**: 25Gbps+

### 소프트웨어 요구사항

```bash
# OS
Ubuntu 22.04 LTS 또는 CentOS Stream 9

# Container Runtime
Docker 24.0+
Docker Compose 2.20+
NVIDIA Container Toolkit 1.13+

# Python Environment  
Python 3.11+
CUDA 12.1+
cuDNN 8.9+

# 모니터링 도구
nvidia-ml-py3      # GPU 모니터링
psutil             # 시스템 리소스 모니터링
prometheus-client  # 메트릭 수집
```

---

## ⚠️ 주요 고려사항 및 위험 요소

### 성능 관련
1. **초기 모델 로딩 시간**: 30초-5분 소요 (모델 크기에 따라)
2. **메모리 사용량**: 모델당 8-80GB VRAM 필요
3. **동시성 제한**: GPU 메모리에 따라 동시 요청 수 제한
4. **응답 시간 변화**: 초기에는 Gemini보다 느릴 수 있음

### 운영 관련
1. **모델 업데이트**: 수동 관리 필요
2. **장애 복구**: 로컬 모델 재시작 시간 고려
3. **스케일링**: 수평 확장 시 GPU 자원 추가 필요
4. **백업**: 모델 파일 백업 전략 필요

### 보안 관련
1. **데이터 프라이버시**: 로컬 처리로 개선
2. **모델 보안**: 악성 모델 다운로드 방지
3. **접근 제어**: 내부 서비스 간 인증 강화

---

## 📊 예상 비용 절감 효과

### API 비용 절감
- **현재 Gemini 비용**: 월 $500-2000 (사용량에 따라)
- **로컬 LLM 비용**: 초기 하드웨어 투자 후 전기비만
- **ROI 시점**: 6-12개월 내 투자 회수 예상

### 운영비 분석
```bash
# Gemini API 비용 (월간 추정)
# 1M 토큰 = $7-15
# 일 10K 요청 * 1000 토큰 = 10M 토큰/월 = $70-150/월

# 로컬 LLM 비용 (월간)
# 전기료: $100-300/월 (GPU 사용량에 따라)
# 인건비: $500-1000/월 (관리 시간)
# 총 운영비: $600-1300/월

# 초기 투자비
# GPU 서버: $5000-15000 (사양에 따라)
# 개발 시간: $5000-10000 (개발자 인건비)
```

---

## 🎯 마이그레이션 체크리스트

### ✅ 사전 준비
- [ ] 하드웨어 사양 확인 (GPU VRAM 16GB+ 권장)
- [ ] Docker 및 NVIDIA Container Toolkit 설치
- [ ] 모델 다운로드 공간 확보 (500GB+)
- [ ] 백업 계획 수립 (기존 Gemini 서비스 보존)

### ✅ 구현 단계
- [ ] 로컬 LLM 라이브러리 설치 (`ollama`, `transformers`)
- [ ] `LocalLLMService` 클래스 구현
- [ ] 백엔드 API 메소드 수정 (`generate_gemini_response` → `generate_local_llm_response`)
- [ ] 환경 설정 파일 업데이트 (`.env`, `requirements.txt`)
- [ ] 서비스 URL 구성 업데이트

### ✅ 테스트 단계
- [ ] 단위 테스트 (개별 서비스)
- [ ] 통합 테스트 (전체 RAG 파이프라인)
- [ ] 성능 벤치마크 (응답 시간, 품질)
- [ ] 부하 테스트 (동시 요청 처리)
- [ ] 한국어 특화 테스트

### ✅ 배포 단계
- [ ] 프로덕션 환경 설정
- [ ] 모니터링 대시보드 설정
- [ ] 롤백 절차 준비
- [ ] 점진적 트래픽 이전 (A/B 테스트)
- [ ] 사용자 피드백 수집 체계 구축

### ✅ 후속 작업
- [ ] 성능 최적화 (양자화, 캐싱)
- [ ] 모델 파인튜닝 (한국어 특화)
- [ ] 비용 효율성 분석
- [ ] 확장성 계획 수립

---

## 📚 추가 리소스

### 공식 문서
- [Ollama 공식 문서](https://ollama.ai/docs)
- [vLLM 문서](https://docs.vllm.ai/)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers)

### 한국어 특화 리소스
- [한국어 LLM 리더보드](https://huggingface.co/spaces/upstage/open-ko-llm-leaderboard)
- [KoAlpaca 모델](https://huggingface.co/beomi/KoAlpaca-Polyglot-12.8B)
- [KULLM 모델](https://huggingface.co/nlpai-lab/kullm-polyglot-12.8b-v2)

### 개발 도구
- [GPU 메모리 계산기](https://huggingface.co/spaces/hf-accelerate/model-memory-usage)
- [모델 성능 벤치마크](https://github.com/EleutherAI/lm-evaluation-harness)

---

**작성일**: 2025-01-13  
**작성자**: Claude Code  
**버전**: 1.0  
**상태**: 마이그레이션 준비 완료

> 💡 **참고**: 이 문서는 실제 마이그레이션 진행 중 발견되는 이슈에 따라 지속적으로 업데이트될 예정입니다.