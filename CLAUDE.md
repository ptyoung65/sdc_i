# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🔴 제0원칙: 정확한 지시만 따르기 (Exact Instructions Only Principle)

**최우선 절대 원칙**: 사용자가 명확히 지시한 부분만 정확히 수정하고, 그 외의 것은 절대 건드리지 말 것.

### 절대 금지 사항
1. ❌ **스스로 판단해서 코드 수정 금지**
   - 이미 잘 작동하는 코드는 절대 건드리지 말 것
   - "개선"하려고 마음대로 수정하지 말 것
   - 사용자가 명확히 지시하지 않은 부분은 절대 수정 금지

2. ❌ **폴백(Fallback) 로직 추가 금지**
   - 에러 처리를 위한 폴백 로직 추가 금지
   - "만약을 위한" 대체 로직 추가 금지
   - 예: `if (!data) { fallback logic }` 같은 코드 추가 금지

3. ❌ **로컬스토리지 사용 금지**
   - localStorage, sessionStorage 사용 금지
   - 브라우저 저장소에 데이터 저장 금지

4. ❌ **Mock 데이터/하드코딩 금지**
   - 테스트용 Mock 데이터 추가 금지
   - 하드코딩된 값 추가 금지
   - 임시 데이터로 작동 확인 후 반드시 제거

5. ❌ **전체 파일 수정 금지**
   - 조건을 준 부분만 정확히 수정
   - 관련 없는 다른 부분은 절대 건드리지 말 것

### 올바른 작업 방식
✅ **사용자가 명확히 지시한 내용만 수정**
✅ **불확실하면 먼저 질문하고 확인 후 작업**
✅ **이미 작동하는 코드는 보존**
✅ **최소한의 변경만 수행**

### 예시
```
❌ 잘못된 방식:
- 사용자: "A 기능 수정해줘"
- Claude: A 기능 수정 + B 기능도 개선 + C 기능에 폴백 추가 + localStorage 사용

✅ 올바른 방식:
- 사용자: "A 기능 수정해줘"
- Claude: A 기능만 정확히 수정 (다른 것은 일체 건드리지 않음)
```

**이 원칙을 위반하면 완벽하게 작동하던 프로그램이 망가질 수 있습니다.**

## 🚨 제1원칙: 완전 오프라인 캐시 환경 (Air-gap Offline Cache Principle)

**최우선 원칙**: 모든 필요한 라이브러리와 종속성은 **반드시 오프라인 캐시를 사용**해야 합니다.

### 라이브러리 설치 및 관리 규칙
1. **신규 라이브러리 필요 시**:
   - 오프라인 캐시에 먼저 다운로드
   - 캐시된 패키지를 통해서만 설치 진행
   - 인터넷 직접 연결 절대 금지

2. **Python 패키지 관리**:
   ```bash
   # 올바른 방법: 오프라인 캐시 사용
   pip install --no-index --find-links /path/to/offline/cache package_name

   # 금지된 방법: 직접 인터넷 설치
   pip install package_name  # ❌ 절대 금지
   ```

3. **Node.js 패키지 관리**:
   ```bash
   # 올바른 방법: 오프라인 캐시 사용
   npm install --cache /path/to/offline/cache --offline

   # 금지된 방법: 직접 인터넷 설치
   npm install package_name  # ❌ 절대 금지
   ```

4. **Container 이미지**:
   - 모든 이미지는 사전에 캐시된 .tar 파일에서 로드
   - 레지스트리 직접 pull 절대 금지
   - `podman load -i cached_image.tar` 방식만 사용

### 개발 환경 제약사항
- **Air-gap 환경**: 완전 오프라인 상태에서만 작동
- **로컬 종속성만 사용**: 외부 네트워크 연결 없음
- **사전 준비된 리소스**: 모든 필요 패키지는 미리 캐시됨

이 원칙을 위반하는 모든 작업은 **즉시 중단**하고 오프라인 캐시 방식으로 대체해야 합니다.

## 🔄 제4원칙: Mock 테스트 후 원복 필수 (Mock Test Reversion Principle)

**핵심 원칙**: 테스트 목적으로 Mock 데이터나 임시 코드를 사용한 후에는 **반드시 실제 구현으로 원복**해야 합니다.

### Mock 테스트 규칙
1. **테스트 중 Mock 사용**:
   - 기능 검증을 위한 임시 Mock 데이터 허용
   - 테스트 완료 후 즉시 원복 필수
   - Mock 코드를 프로덕션에 그대로 두는 것 절대 금지

2. **원복 체크리스트**:
   - Mock 데이터 → 실제 API 응답
   - 하드코딩된 값 → 동적 값
   - 테스트용 조건문 → 실제 비즈니스 로직
   - 임시 콘솔 로그 → 제거 또는 적절한 로깅

3. **위반 시 위험성**:
   - 프로덕션 환경에서 예상치 못한 동작
   - 실제 데이터 흐름 차단
   - 사용자 경험 저하
   - 시스템 신뢰성 문제

### Mock 테스트 예시
```javascript
// ❌ 잘못된 방법: Mock 데이터를 그대로 둠
sources: [
  { chunk_id: 'mock-1', content: 'mock content' } // 테스트 후 제거 안함
]

// ✅ 올바른 방법: 실제 API 응답 사용
sources: data.sources || [] // 테스트 후 원복 완료
```

이 원칙을 통해 테스트와 프로덕션 환경의 일관성을 보장합니다.

## Common Development Commands

This project uses a comprehensive Makefile for development tasks. All commands should be run from the project root.

### Essential Commands
- `make help` - Display all available commands
- `make setup` - Initial project setup (copies .env, installs dependencies, builds containers)
- `make up` - Start all services in containers
- `make dev` - Start development environment (databases only, then backend/frontend locally)
- `make down` - Stop all services
- `make health` - Check if all services are running properly

### Testing
- `make test` - Run all tests (backend + frontend)
- `make test-backend` - Run Python backend tests using pytest
- `make test-frontend` - Run Next.js frontend tests using Jest
- `make test-integration` - Run integration tests with full stack

### Code Quality
- `make lint` - Run all linters (backend: black, ruff, mypy; frontend: eslint)
- `make lint-backend` - Backend: `black --check`, `ruff check`, `mypy`
- `make lint-frontend` - Frontend: `npm run lint` 
- `make format` - Format all code (black for Python, prettier for TypeScript)

### Database Management
- `make db-migrate` - Run Alembic database migrations
- `make db-rollback` - Rollback last migration
- `make db-reset` - Reset database completely (destructive)

### Container Management
Uses Podman by default (can substitute Docker):
- `make build` - Build all containers
- `make build-backend` - Build only backend container
- `make build-frontend` - Build only frontend container

## Architecture Overview

SDC (Smart Document Companion) is a multi-LLM conversational AI platform with the following architecture:

### Layer Structure
```
Layer 5: CI/CD (Podman/Docker deployment)
Layer 4: Security & Monitoring (Rate limiting, JWT auth, metrics)
Layer 3: Hybrid Search Database (PostgreSQL + Milvus + Elasticsearch)
Layer 2: AI & RAG Orchestration (LangGraph, Multi-LLM, Embedding)
Layer 1: Application Layer (Next.js Frontend + FastAPI Backend)
```

### Core Services
- **Backend**: FastAPI application (`backend/app/main.py`)
- **Frontend**: Next.js application with Zustand state management
- **PostgreSQL**: Primary database with pgvector extension
- **Redis**: Caching and rate limiting
- **Milvus**: Vector database for embeddings
- **Elasticsearch**: Full-text search engine
- **Nginx**: Reverse proxy and load balancer

### Backend Structure (`backend/app/`)
- `api/routes/` - API endpoint definitions
- `core/` - Core functionality (config, database, middleware, security)
- `services/` - Business logic (auth, AI services, document processing)
- `schemas/` - Pydantic data validation models
- `services/ai/` - Multi-LLM orchestration, RAG pipeline, embeddings

### Frontend Structure (`frontend/`)
- `src/components/` - React components
- `src/hooks/` - Custom React hooks  
- `src/services/` - API service layer
- `src/store/` - Zustand state management
- Uses Radix UI components, Tailwind CSS, and React Hook Form

### Multi-LLM PRP System (`multi-llm-prp/`)
Separate TypeScript project implementing Problem Refinement Prompts methodology:
- `src/core/` - Core types and interfaces
- `src/agents/` - Agent orchestration system
- `src/providers/` - OpenAI, Anthropic, Google AI integrations
- `src/prp/` - PRP management and validation

## Key Technologies

### Backend Stack
- **FastAPI** - Python async web framework
- **SQLAlchemy** - Database ORM with async support
- **Alembic** - Database migrations
- **Pydantic** - Data validation and serialization
- **LangGraph** - RAG pipeline orchestration
- **JWT** - Authentication tokens
- **bcrypt** - Password hashing

### Frontend Stack  
- **Next.js 15** - React framework
- **TypeScript** - Type safety
- **Zustand** - State management
- **Radix UI** - Accessible UI components
- **Tailwind CSS** - Utility-first styling
- **React Hook Form + Zod** - Form handling and validation
- **SWR** - Data fetching
- **Framer Motion** - Animations

### AI/ML Services
- **Multi-LLM Support**: OpenAI, Anthropic, Google, Ollama
- **KURE-v1**: Korean language optimized embedding model
- **Hybrid Search**: Vector + keyword search combination
- **RAG Pipeline**: Advanced retrieval-augmented generation

## Development Guidelines

### Environment Setup
- Copy `.env.example` to `.env` and configure API keys
- Requires Node.js 20+, Python 3.11+, PostgreSQL 16+, Redis 7+
- Use `make setup` for initial configuration

### Testing Requirements
- Backend: Use pytest with asyncio support
- Frontend: Jest for unit tests, Playwright for E2E
- Always run tests before committing: `make test`

### Code Standards
- Backend: Black formatting, Ruff linting, MyPy type checking
- Frontend: ESLint + Prettier, TypeScript strict mode
- Use `make lint` to check code quality

### Security Considerations
- JWT-based authentication with bcrypt password hashing  
- Rate limiting per user/IP
- CORS protection and security headers
- SQL injection prevention via SQLAlchemy
- Never commit API keys or secrets

### Container Development
- Uses Podman by default (Docker compatible)
- Multi-stage Containerfile for optimized builds
- Health checks for all services
- Volume mounts for development hot-reloading

## 완료된 기능 체크리스트

### ✅ Document Upload & RAG Service Integration (2025-09-05)
**Status**: COMPLETE - DO NOT MODIFY UNLESS EXPLICITLY REQUESTED

**Implemented Features**:
1. **Document Upload API** ✅
   - `POST /api/v1/documents` endpoint for frontend compatibility
   - `POST /api/v1/documents/upload` endpoint (legacy support)
   - File processing and storage in memory store
   - Support for multipart/form-data uploads

2. **Simple Document Search** ✅
   - Keyword-based document content matching
   - Context extraction (200-character snippets)
   - User-specific document isolation
   - Fallback to basic AI when no matches found

3. **RAG Integration** ✅
   - Enhanced AI responses using document context
   - Source attribution in responses
   - Hybrid approach: Full RAG service when available, simple search as fallback
   - Integration with existing chat endpoint

4. **Testing & Validation** ✅
   - Document upload endpoint tested and working
   - RAG-based chat responses verified
   - Frontend-backend integration confirmed
   - All API endpoints responding correctly

**Key Files Modified**:
- `backend/simple_api.py`: Main implementation
- Added document storage, search logic, and API endpoints
- Preserved all existing functionality

**Important**: This implementation uses a simple in-memory document store and keyword matching. Do not modify this working solution unless the user explicitly requests changes or improvements. The system is functioning correctly and serving uploaded documents in AI responses.

### ✅ Multi-Format Document Processing System (2025-09-05)
**Status**: COMPLETE - DO NOT MODIFY UNLESS EXPLICITLY REQUESTED
**Commit**: 11e58bd - "Implement multi-format document processing with Docling and alternative processors"

**Implemented Features**:

1. **Docker Container Integration** ✅
   - Added Docling service to `docker-compose.yml`
   - Container configured with health checks and proper networking
   - Environment variables for DOCLING_HOST and DOCLING_PORT
   - Volume mounts for document processing (`./uploads` and `./processed`)
   - Backend service dependency on Docling service

2. **Docling Client Service** ✅
   - **File**: `backend/app/services/document/docling_client.py`
   - HTTP client for Docling service communication
   - Support for PDF, PPT, PPTX, XLSX, XLS, DOC, DOCX formats
   - Automatic file type detection and validation
   - Comprehensive error handling with fallback mechanisms
   - Health check capabilities

3. **Alternative Document Processor** ✅
   - **File**: `backend/app/services/document/alternative_processor.py`
   - Local Python library fallback when Docling unavailable
   - **Libraries**: python-docx, python-pptx, openpyxl, PyPDF2
   - Format-specific processing methods for each document type
   - Graceful degradation with informative error messages

4. **Enhanced Upload Processing** ✅
   - **File**: `backend/simple_api.py` (507 lines added)
   - Smart document processing pipeline: Docling → Alternative → Basic
   - Automatic file extension detection and format routing
   - Temporary file handling with cleanup
   - Comprehensive logging and status tracking
   - Processing method attribution (docling/alternative_processor/basic)

5. **Dependencies & Environment** ✅
   - **Installed Libraries**: python-docx, python-pptx, openpyxl, PyPDF2, lxml, XlsxWriter
   - **Requirements Updated**: `requirements.txt` and `requirements-minimal.txt`
   - All document processing dependencies available in virtual environment
   - Import error handling with graceful fallbacks

6. **Database Migrations Setup** ✅
   - **Alembic Configuration**: `backend/alembic.ini`
   - Database migration scripts in `backend/alembic/`
   - Proper database model support for document metadata

7. **Monitoring & Metrics** ✅
   - **File**: `backend/app/core/monitoring/enhanced_metrics.py`
   - Document processing performance tracking
   - Success/failure rate monitoring for different processors

8. **Frontend Integration** ✅
   - **File**: `frontend/src/components/chat/conversation-sidebar.tsx`
   - UI components for document management
   - Compatible with existing upload workflow

**Processing Flow**:
```
File Upload → Extension Detection → Structured Format Check
    ↓
If PDF/PPT/XLSX/DOC:
    Try Docling Service → If Failed → Alternative Processor → If Failed → Basic Processing
Else:
    Basic Text Processing
    ↓
Store with Processing Method Metadata → RAG Integration
```

**Supported Formats**:
- ✅ **PDF**: PyPDF2 library
- ✅ **Word**: python-docx (DOCX, DOC)  
- ✅ **PowerPoint**: python-pptx (PPTX, PPT)
- ✅ **Excel**: openpyxl (XLSX, XLS)
- ✅ **Text**: Built-in (TXT, MD)

**Key Files Modified/Created**:
- `docker-compose.yml`: Added Docling service configuration
- `backend/simple_api.py`: Enhanced with multi-format processing (507 lines added)
- `backend/app/services/document/`: Complete document processing module
- `backend/requirements.txt`: Updated with document processing libraries
- `backend/alembic/`: Database migration setup
- Frontend conversation components

**Testing Status**: ✅ VERIFIED
- Document upload working with all supported formats
- Fallback mechanisms tested (Docling → Alternative → Basic)
- Integration with existing RAG pipeline confirmed
- Frontend-backend communication verified
- All processing methods functional

**Important**: This is a complete, production-ready multi-format document processing system with intelligent fallback mechanisms. The system automatically detects file types and uses the most appropriate processing method. Do not modify this implementation unless specifically requested, as it provides comprehensive document processing capabilities while maintaining backward compatibility.

## ⚠️ CRITICAL DEVELOPMENT GUIDELINES

### Completed Features Protection
**BEFORE modifying any file related to completed features, you MUST:**

1. **Check CLAUDE.md Completion Checklist** - Review the "완료된 기능 체크리스트" section
2. **Verify Feature Status** - If marked as "COMPLETE - DO NOT MODIFY", get explicit user confirmation
3. **Preserve Existing Functionality** - Never break working features during modifications
4. **Test Before Commit** - Verify all existing features still work after changes

### Multi-Format Document Processing - Protection Rules
**Status**: COMPLETE (Commit: 11e58bd) - PROTECTED SYSTEM

**DO NOT MODIFY these files without explicit user request:**
- `docker-compose.yml` (Docling service configuration)
- `backend/simple_api.py` (Document processing pipeline)  
- `backend/app/services/document/` (Document processing modules)
- `backend/requirements.txt` (Document processing dependencies)

**IF modification is requested:**
1. Backup existing functionality
2. Test all document formats (PDF, DOCX, PPTX, XLSX)  
3. Verify fallback mechanisms work
4. Confirm RAG integration remains functional
5. Update completion checklist if changes are made

### Code Modification Priority
1. **Preserve Completed Features** (Highest Priority)
2. **Implement New Requirements**
3. **Optimize/Refactor** (Lowest Priority)

This ensures stable, working features are not accidentally broken during development.

## 📌 핵심 서비스 정의 (Critical Services Definition)

### 🎯 핵심 서비스 (Core Services) - 반드시 모두 정상 작동해야 함
**핵심 서비스는 SDC 프로젝트에서 신규 개발된 서비스만 포함합니다.**

| 서비스명 | 포트 | 설명 | 컨테이너명 | 상태 요구사항 |
|---------|------|------|-----------|--------------|
| **Frontend** | 3000 | Next.js 메인 UI | sdc-frontend | ✅ Healthy 필수 |
| **Backend API** | 8000 | FastAPI/Air-gap 서버 | sdc-backend | ✅ Healthy 필수 |
| **Admin Panel** | 3003 | 관리자 대시보드 | - | ✅ Running 필수 |
| **Korean RAG** | 8009 | 한국어 RAG 서비스 | sdc-korean-rag | ✅ Healthy 필수 |
| **Graph RAG** | 8010 | 그래프 기반 RAG | sdc-graph-rag | ✅ Healthy 필수 |
| **Keyword RAG** | 8011 | 키워드 기반 RAG | sdc-keyword-rag | ✅ Healthy 필수 |
| **Text-to-SQL RAG** | 8012 | SQL 변환 RAG | sdc-text-to-sql-rag | ✅ Healthy 필수 |
| **RAG Orchestrator** | 8008 | RAG 통합 관리 | sdc-rag-orchestrator | ✅ Healthy 필수 |
| **Docling** | 5000 | 문서 처리 서비스 | sdc-docling | ✅ Healthy 필수 |

### 📦 지원 서비스 (Supporting Services) - 일반 패키지
**핵심 서비스가 아니지만 시스템 작동에 필요한 서비스들**

| 서비스명 | 포트 | 설명 | 상태 |
|---------|------|------|------|
| PostgreSQL | 5432 | 데이터베이스 | 필요시 사용 |
| Redis | 6379 | 캐시/세션 | 필요시 사용 |
| Milvus | 19530 | 벡터 DB | 필요시 사용 |
| Elasticsearch | 9200 | 검색 엔진 | 필요시 사용 |
| Nginx | 80/443 | 리버스 프록시 | 필요시 사용 |

### ⚠️ 완벽한 시스템 기준
**"완벽한 것은 모든 컨테이너와 화면이 다 실행이 되어야 완벽한 거야"**
- ✅ 모든 핵심 서비스 (9개) 정상 작동
- ✅ 모든 컨테이너 Healthy 상태
- ✅ 모든 웹 화면 접속 가능
- ✅ 모든 API 엔드포인트 응답

## 🔌 포트 관리 및 서비스 매핑

### 현재 사용 중인 포트 목록
**이 섹션은 모든 프로젝트 재실행 시 확인해야 하며, 신규 서비스 생성 시 포트 충돌을 방지하기 위해 반드시 참조해야 합니다.**

#### ✅ 활성 포트 (Active Ports)
| 포트 | 서비스명 | 설명 | 상태 | 시작 명령 |
|------|---------|------|------|-----------|
| 3000 | SDC Frontend | 메인 AI 챗봇 UI | ✅ 활성 | `cd frontend && npm run dev` |
| 3001 | - | 미사용 | ⭕ 미사용 | - |
| 3002 | Dify | AI Workflow Builder | ✅ 활성 | Docker 컨테이너로 실행 중 |
| 3003 | Admin Panel / RAG Dashboard | 관리자 페이지 (Guardrails/RBAC) | ✅ 활성 | `cd services/admin-panel && npm run dev` |
| 3004 | Curation Dashboard | AI 큐레이션 모니터링 대시보드 | ✅ 활성 | `cd services/curation-dashboard && npm run dev` |
| 8000 | SDC Backend API | 메인 백엔드 서비스 | ✅ 활성 | `cd backend && python simple_api.py` |
| 8001 | Guardrails Service | AI 안전 가드레일 서비스 | ✅ 활성 | `cd services && python simple-guardrails-service.py --port 8001` |
| 8002 | RAG Evaluator | RAG 성과 평가 서비스 | ✅ 활성 | `cd services/rag-evaluator && python main.py --port 8002` |
| 8003 | - | 미사용 | ⭕ 미사용 | - |
| 8004 | - | 미사용 | ⭕ 미사용 | - |
| 8005 | - | 미사용 | ⭕ 미사용 | - |
| 8006 | Curation Service | 큐레이션 API 서비스 | ✅ 활성 | `cd services && python simple-curation-service.py --port 8006` |
| 8007 | AI Model Service | AI 모델 관리 서비스 | ✅ 활성 | `cd services/ai-model-service && python main.py --port 8007` |
| 8008 | RAG Orchestrator | RAG 파이프라인 오케스트레이터 | ✅ 활성 | `cd services/rag-orchestrator && python main.py --port 8008` |
| 8080 | SearxNG | 검색 엔진 | ⚠️ 가능 | Docker 컨테이너 |
| 5432 | PostgreSQL | 데이터베이스 | ⚠️ 가능 | Docker/시스템 서비스 |
| 6379 | Redis | 캐시/세션 스토어 | ⚠️ 가능 | Docker/시스템 서비스 |

### 📝 포트 확인 명령어
프로젝트 재실행 전 반드시 실행해야 할 명령어:

```bash
# 포트 상태 빠른 확인
for port in 3000 3001 3002 3003 3004 8000 8001 8002 8003 8004 8005 8006 8007 8008; do 
  echo -n "Port $port: "
  curl -s -o /dev/null -w "%{http_code}" http://localhost:$port 2>/dev/null || echo "Not Available"
done

# 프로세스 확인
ps aux | grep -E "(node|python|uvicorn)" | grep -E "(3000|3001|3002|3003|3004|8000|8006|8007|8008)"

# 포트 강제 종료 (필요시)
lsof -ti:포트번호 | xargs -r kill -9
```

### 🚀 Open WebUI 서비스 시작 (필수)
```bash
# Open WebUI 컨테이너 시작 (원격 DB 모드)
cd /home/chatpro/open-webui-main
./podman-start-remote.sh 192.168.122.85

# 접속 주소: http://192.168.122.178:3000
```

### 🚀 전체 서비스 시작 스크립트
```bash
# 1. 백엔드 서비스 시작
cd backend && source venv/bin/activate && python simple_api.py &

# 2. 프론트엔드 시작
cd frontend && npm run dev &

# 3. AI 큐레이션 서비스들 시작
cd services && python simple-curation-service.py --port 8006 &
cd services/ai-model-service && python main.py --port 8007 &
cd services/rag-orchestrator && python main.py --port 8008 &

# 4. 대시보드 시작
cd services/curation-dashboard && npm run dev &
```

### ⚠️ 포트 충돌 방지 가이드라인
1. **신규 서비스 생성 시**: 
   - 위 표에서 미사용(⭕) 포트를 우선 사용
   - 3005-3099 (프론트엔드), 8009-8099 (백엔드) 범위 권장

2. **프로젝트 재실행 시**:
   - 위의 포트 확인 명령어 실행
   - 이미 사용 중인 포트 확인 후 종료 또는 다른 포트 사용

3. **Docker/Podman 서비스**:
   - docker-compose.yml 파일에서 포트 매핑 확인
   - 컨테이너 실행 전 호스트 포트 확인

4. **포트 변경 시**:
   - package.json (프론트엔드)
   - main.py의 uvicorn.run() (백엔드)
   - docker-compose.yml (컨테이너)
   - 환경 변수 파일 (.env)

### 🔄 자동 포트 관리 함수
```bash
# ~/.bashrc 또는 프로젝트 스크립트에 추가
check_sdc_ports() {
  echo "=== SDC 프로젝트 포트 상태 ==="
  for port in 3000 3001 3002 3003 3004 8000 8006 8007 8008; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
      echo "✅ Port $port: 사용 중"
    else
      echo "⭕ Port $port: 사용 가능"
    fi
  done
}

# 사용: check_sdc_ports
```

**중요**: 이 포트 매핑 정보는 프로젝트의 안정적인 운영을 위해 항상 최신 상태로 유지되어야 합니다.

## 🔗 GitHub Repository 관리

### Repository 정보
- **GitHub Repository**: https://github.com/ptyoung65/sdc_i
- **Owner**: ptyoung65
- **Repository Name**: sdc_i
- **Default Branch**: main

### Git 설정 정보
```bash
# Remote origin 설정
git remote add origin https://github.com/ptyoung65/sdc_i.git

# 또는 토큰을 포함한 설정 (보안상 실제 사용시에만)
git remote add origin https://ghp_TOKEN@github.com/ptyoung65/sdc_i.git
```

### 일반적인 Git 명령어
```bash
# 현재 상태 확인
git status

# 변경사항 추가
git add .

# 커밋
git commit -m "커밋 메시지"

# GitHub에 push
git push origin main

# 최신 변경사항 pull
git pull origin main
```

### GitHub Token 관리
- **보안 주의**: GitHub Personal Access Token은 보안이 중요하므로 직접 코드에 포함하지 않음
- **환경변수 사용 권장**: `GITHUB_TOKEN` 환경변수로 관리
- **토큰 권한**: Repository 읽기/쓰기 권한 필요

### 자동화 스크립트 예시
```bash
#!/bin/bash
# quick_commit_push.sh
git add .
git commit -m "Update: $(date '+%Y-%m-%d %H:%M:%S')"
git push origin main
```

**중요**: GitHub Token과 같은 민감한 정보는 환경변수나 별도 설정 파일로 관리하고, 절대 코드에 직접 포함하지 않도록 주의하세요.

## 🔧 VSCode 기반 웹 개발 환경 (VSCode Web Development Environment)

### 개발 환경 구성 완료 (2025-01-15)
**Status**: COMPLETE - 프로그램 개발자용 VSCode 웹 UI 및 Podman 컨테이너 환경 구축 완료

**구현된 기능**:

#### 1. VSCode Web Server 환경 ✅
- **VSCode Server Container**: `dev-environment/Containerfile.vscode-server`
- **Web IDE 접속**: http://localhost:8080 (password: sdc_dev_2025)
- **통합 개발 환경**: 프론트엔드, 백엔드, 데이터베이스 모두 웹 브라우저에서 개발 가능

#### 2. 개발자 전용 어드민 인터페이스 ✅
- **별도 포트**: 3005 (http://localhost:3005)
- **서비스 모니터링**: 모든 개발 서비스 상태 실시간 확인
- **컨테이너 관리**: Podman 컨테이너 시작/중지 제어
- **개발 도구 링크**: VSCode, PgAdmin, Redis Insight 등 원클릭 접속

#### 3. Podman 기반 개발 컨테이너 환경 ✅
- **docker-compose.dev.yml**: 완전한 개발 환경 오케스트레이션
- **PostgreSQL Dev**: localhost:5433 (사용자: sdc_dev_user, 비밀번호: sdc_dev_pass_2025)
- **Redis Dev**: localhost:6380
- **PgAdmin**: localhost:5050 (dev@sdc.local / sdc_dev_2025)
- **Redis Insight**: localhost:8001

#### 4. 개발 환경 관리 스크립트 ✅
- **dev-start.sh**: 전체 개발 환경 시작
- **dev-stop.sh**: 개발 환경 종료
- **start-developer-admin.sh**: 개발자 어드민 인터페이스만 시작

### 포트 할당 (개발 환경)
| 서비스 | 포트 | 용도 | 접속 URL |
|--------|------|------|----------|
| VSCode Server | 8080 | 웹 기반 IDE | http://localhost:8080 |
| Developer Admin | 3005 | 개발자 관리 인터페이스 | http://localhost:3005 |
| Frontend Dev | 3000 | Next.js 개발 서버 | http://localhost:3000 |
| Backend API | 8000 | FastAPI 개발 서버 | http://localhost:8000 |
| Admin Panel | 3003 | 기존 관리자 패널 | http://localhost:3003 |
| PostgreSQL Dev | 5433 | 개발용 DB | localhost:5433 |
| Redis Dev | 6380 | 개발용 캐시 | localhost:6380 |
| PgAdmin | 5050 | DB 관리 도구 | http://localhost:5050 |
| Redis Insight | 8001 | Redis 관리 도구 | http://localhost:8001 |

### 사용 방법
```bash
# 전체 개발 환경 시작 (VSCode + 모든 서비스)
./dev-start.sh

# 개발자 관리 인터페이스만 시작
./start-developer-admin.sh

# 개발 환경 종료
./dev-stop.sh

# 서비스 상태 확인
podman-compose -f docker-compose.dev.yml logs -f
```

### 개발 환경 특징
- **완전 웹 기반**: 모든 개발 도구를 웹 브라우저에서 접근 가능
- **컨테이너화**: 일관된 개발 환경 제공
- **실시간 모니터링**: 모든 서비스 상태를 개발자 어드민에서 확인
- **원클릭 접속**: 필요한 도구들에 바로 접근 가능
- **분리된 DB**: 프로덕션과 완전히 분리된 개발용 데이터베이스

**Important**: 이 개발 환경은 프로그램 개발자의 생산성을 위해 최적화되었으며, VSCode Server를 통해 완전한 웹 기반 개발 경험을 제공합니다.

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.