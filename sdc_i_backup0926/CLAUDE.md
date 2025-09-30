# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

## 🚪 제2원칙: 포트 점유 및 확보 우선 정책 (Port Acquisition Priority Policy)

**핵심 원칙**: 포트는 수정하지 않으며, 기존 포트와 충돌 시 **기존 포트를 Kill하고 해당 포트를 확보**해야 합니다.

### 포트 관리 규칙
1. **포트 고정 원칙**:
   - 각 서비스는 정해진 고정 포트를 사용
   - 포트 번호 변경 절대 금지
   - 서비스별 표준 포트 준수 필수

2. **포트 충돌 해결 방법**:
   ```bash
   # 올바른 방법: 기존 프로세스 Kill 후 포트 확보
   lsof -ti:3000 | xargs -r kill -9
   npm run dev  # 3000 포트로 실행

   # 금지된 방법: 포트 번호 변경
   npm run dev -- --port 3001  # ❌ 절대 금지
   ```

3. **포트 확보 절차**:
   - 해당 포트 사용 중인 프로세스 확인: `lsof -i :포트번호`
   - 프로세스 강제 종료: `kill -9 PID` 또는 `lsof -ti:포트번호 | xargs -r kill -9`
   - 포트 확보 후 서비스 시작

4. **기존 할당 포트 점유 시 강제 확보**:
   - 기존 할당된 포트를 이미 점유하고 있으면 **반드시 강력하게 kill**
   - 포트 확보 후 기존 프로그램을 해당 포트에서 실행
   - 포트 변경 대신 프로세스 종료를 우선 적용
   ```bash
   # 강제 포트 확보 및 서비스 재시작
   lsof -ti:3000 | xargs -r kill -9  # 강력한 kill
   sleep 1  # 포트 해제 대기
   npm run dev  # 기존 프로그램을 정해진 포트에서 실행
   ```

5. **표준 포트 목록**:
   - Frontend: 3000 (고정)
   - Backend API: 8000 (고정)
   - Admin Panel: 3003 (고정)
   - Database: 5432 (고정)
   - Redis: 6379 (고정)

### 포트 충돌 예방
- 서비스 시작 전 포트 상태 확인 필수
- 자동 포트 확보 스크립트 활용
- 포트 변경 대신 프로세스 종료 우선

이 원칙을 통해 일관된 포트 구성을 유지하고 서비스 간 혼란을 방지합니다.

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

## 🚨 제5원칙: 프로덕션 오류 무시 금지 원칙 (Production Error Prohibition Principle)

**핵심 원칙**: 프로덕션 프로그램에서 발생하는 모든 오류는 **절대 무시하면 안 되며 반드시 즉시 해결**해야 합니다.

### 프로덕션 오류 처리 규칙
1. **오류 발견 시 즉시 대응**:
   - 컴파일 오류, 런타임 오류, 모듈 누락 오류 등 모든 오류 대상
   - "나중에 고치겠다" 또는 "일단 넘어가자"는 절대 금지
   - 오류 발견 즉시 모든 작업을 중단하고 해결에 집중

2. **완전한 해결만 허용**:
   - 임시방편이나 workaround 금지
   - 근본 원인 파악 및 완전한 수정 필수
   - 해결 완료 후에만 다음 작업 진행

3. **오류 무시 금지 사유**:
   - 사용자 경험 저하 방지
   - 시스템 안정성 보장
   - 기술 부채 누적 방지
   - 연쇄 오류 발생 예방

### 오류 해결 프로세스
```bash
# 1단계: 오류 발견 시 즉시 작업 중단
echo "⚠️ 프로덕션 오류 발견 - 모든 작업 중단"

# 2단계: 근본 원인 분석
# - 로그 확인
# - 의존성 점검
# - 설정 파일 검증

# 3단계: 완전한 해결
# - 누락된 의존성 설치
# - 잘못된 경로 수정
# - 설정 오류 교정

# 4단계: 검증 및 테스트
# - 오류 완전 해결 확인
# - 정상 작동 테스트
# - 부작용 없음 확인

# 5단계: 작업 재개
echo "✅ 오류 해결 완료 - 작업 재개"
```

### 위반 시 결과
- **즉각적 영향**: 서비스 장애, 사용자 불만
- **장기적 영향**: 기술 부채 누적, 유지보수 비용 증가
- **팀 영향**: 개발 생산성 저하, 신뢰성 문제

이 원칙을 통해 높은 품질의 안정적인 프로덕션 환경을 유지합니다.

## 📂 제10원칙: 변경 파일 자동 백업 및 추적 시스템 (Change File Auto-Backup & Tracking System)

**핵심 원칙**: 2025년 9월 19일 SDC 개발 서버 상태를 기준으로, 모든 파일 변경사항을 **자동으로 분류하여 백업 폴더에 저장**해야 합니다.

### 기준 상태 정의
- **기준 날짜**: 2025년 9월 19일 (9/19)
- **기준 시점**: SDC 개발 서버의 현재 폴더 상태
- **기준 커밋**: 6e658bc "Update project documentation and enhance chatbot interface"

### 변경 파일 추적 규칙
1. **변경 감지 시점**:
   - 파일 생성, 수정, 삭제가 발생한 즉시
   - 변경 내용과 동시에 백업 처리 진행
   - 실시간 변경사항 추적 및 기록

2. **백업 폴더 구조**:
   ```
   프로젝트루트/
   ├── add-file/           # 신규 생성된 파일들
   ├── modi-fold/          # 수정된 파일들
   └── del-fold/           # 삭제된 파일들
   ```

3. **날짜-시간 기반 분류**:
   ```
   add-file/
   └── 2025-09-19_14-30-25/    # YYYY-MM-DD_HH-MM-SS 형식
       ├── new_component.tsx
       └── new_service.py

   modi-fold/
   └── 2025-09-19_14-30-25/
       ├── modified_file.js
       └── updated_config.yml

   del-fold/
   └── 2025-09-19_14-30-25/
       ├── deleted_component.tsx
       └── removed_script.sh
   ```

### 백업 실행 절차
1. **파일 변경 감지**:
   ```bash
   # 변경된 파일 식별
   git status --porcelain

   # 변경 타입별 분류
   # A = 추가된 파일 (add-file)
   # M = 수정된 파일 (modi-fold)
   # D = 삭제된 파일 (del-fold)
   ```

2. **자동 백업 스크립트**:
   ```bash
   #!/bin/bash
   # 현재 시간으로 폴더명 생성
   TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')

   # 각 변경 타입별 폴더 생성
   mkdir -p add-file/${TIMESTAMP}
   mkdir -p modi-fold/${TIMESTAMP}
   mkdir -p del-fold/${TIMESTAMP}

   # 변경된 파일들을 해당 백업 폴더로 복사
   git diff --name-status | while read status file; do
     case $status in
       A) cp "$file" "add-file/${TIMESTAMP}/" ;;
       M) cp "$file" "modi-fold/${TIMESTAMP}/" ;;
       D) cp "$file" "del-fold/${TIMESTAMP}/" 2>/dev/null || echo "파일 이미 삭제됨" ;;
     esac
   done
   ```

3. **백업 정보 기록**:
   ```bash
   # 각 백업 폴더에 변경 정보 기록
   echo "변경 시간: $(date)" > add-file/${TIMESTAMP}/CHANGE_INFO.txt
   echo "변경 타입: 신규 추가" >> add-file/${TIMESTAMP}/CHANGE_INFO.txt
   echo "파일 목록:" >> add-file/${TIMESTAMP}/CHANGE_INFO.txt
   ls -la add-file/${TIMESTAMP}/ >> add-file/${TIMESTAMP}/CHANGE_INFO.txt
   ```

### 백업 관리 정책
1. **보존 기간**:
   - 최근 30일간의 모든 변경사항 보존
   - 30일 이후 자동 아카이브 또는 삭제
   - 중요 변경사항은 수동으로 영구 보존

2. **백업 검증**:
   - 백업 완료 후 파일 무결성 확인
   - 백업 폴더 용량 모니터링
   - 중복 백업 방지 로직 적용

3. **복원 절차**:
   ```bash
   # 특정 시점으로 파일 복원
   cp modi-fold/2025-09-19_14-30-25/config.yml ./

   # 삭제된 파일 복원
   cp del-fold/2025-09-19_14-30-25/deleted_file.js ./
   ```

### 자동화 스크립트 예시
```bash
#!/bin/bash
# file_change_tracker.sh
# 파일 변경사항 자동 추적 및 백업

# 기능 활성화
ENABLE_AUTO_BACKUP=true

# Git hook을 통한 자동 실행
if [ "$ENABLE_AUTO_BACKUP" = true ]; then
    echo "📂 파일 변경사항 백업 중..."
    ./backup_changed_files.sh
    echo "✅ 백업 완료: $(date)"
fi
```

### 위반 시 위험성
- **변경사항 추적 불가**: 어떤 파일이 언제 변경되었는지 파악 어려움
- **복원 능력 상실**: 문제 발생 시 이전 상태로 되돌리기 불가
- **변경 이력 손실**: 개발 과정 추적 및 디버깅 어려움
- **협업 충돌**: 팀원 간 변경사항 공유 및 병합 문제

### 구현 우선순위
1. **High**: Git hook 기반 자동 백업 시스템 구축
2. **Medium**: 백업 폴더 관리 및 정리 자동화
3. **Low**: 웹 기반 백업 파일 브라우저 개발

이 원칙을 통해 모든 코드 변경사항을 체계적으로 추적하고 관리하여 프로젝트 안정성과 개발 효율성을 극대화합니다.

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

## 📦 제100원칙: 변경사항 자동 추적 및 배포 관리 원칙 (Change Tracking & Deployment Management Principle)

**핵심 원칙**: 복원한 커밋부터 다음 커밋까지의 모든 변경사항을 **자동으로 추적하고 압축하여 배포 가능한 형태로 관리**해야 합니다.

### 변경사항 추적 규칙
1. **기준점 설정**:
   - 복원 커밋: 71b1b06 "SDC 생성형 AI 첫번째 반입버전:2025년09월 23일"
   - 추적 시작일: 2025년 09월 27일
   - 변경사항 문서: change-2025-09-27.md

2. **자동 추적 대상**:
   - 신규 생성 파일 (A)
   - 수정된 파일 (M)
   - 삭제된 파일 (D)
   - 디렉토리 구조 변경
   - 권한 변경

3. **변경사항 기록 형식**:
   ```markdown
   ## 변경사항 - YYYY-MM-DD HH:MM:SS

   ### 신규 파일
   - `파일경로`: 파일 설명

   ### 수정된 파일
   - `파일경로`: 수정 내용 요약

   ### 삭제된 파일
   - `파일경로`: 삭제 사유

   ### 주요 변경 내용
   - 기능 추가/수정 요약
   ```

4. **자동 압축 및 배포**:
   - Git 커밋 요청 시 자동으로 변경사항 압축
   - 압축 파일명: `sdc-changes-YYYY-MM-DD-HHMMSS.tar.gz`
   - 포함 내용: 변경된 파일 + change-date.md
   - 배포 준비 완료 상태로 생성

### 변경사항 관리 워크플로우
1. **실시간 변경 감지**: 파일 생성/수정/삭제 시 즉시 change-date.md 업데이트
2. **중간 체크포인트**: 주요 기능 완성 시 중간 기록
3. **커밋 전 압축**: Git 커밋 요청 시 모든 변경사항 압축
4. **배포 패키지 생성**: 즉시 배포 가능한 형태로 패키징

### 자동화 스크립트
- `track-changes.sh`: 변경사항 자동 추적
- `package-changes.sh`: 변경사항 압축 및 패키징
- `deploy-prepare.sh`: 배포 준비 및 검증

### 위반 시 위험성
- **변경사항 누락**: 배포 시 필수 파일 누락 위험
- **추적 불가**: 문제 발생 시 원인 추적 어려움
- **배포 실패**: 불완전한 패키지로 인한 배포 오류
- **개발 연속성 파괴**: 변경사항 이력 단절

이 원칙을 통해 모든 개발 변경사항을 체계적으로 관리하고 안정적인 배포를 보장합니다.

## 🔗 제21원칙: 전체 시스템 HOST_IP 통합 관리 원칙 (System-wide HOST_IP Unified Management Principle)

**핵심 원칙**: DB 뿐만 아니라 **모든 링크나 연결도 동일하게 IP가 필요한 프로그램이나 환경변수는 모두 동일한 내용**이어야 합니다.

### 전체 시스템 HOST_IP 적용 규칙
1. **완전 통합 원칙**:
   - 데이터베이스 연결
   - API 엔드포인트 URL
   - 웹 서비스 링크
   - 컨테이너 네트워크 설정
   - 프록시 및 로드밸런서 설정
   - 모든 내부/외부 서비스 간 통신

2. **환경변수 통일 규칙**:
   ```bash
   # .env 파일 - 모든 IP 관련 설정 통합
   HOST_IP=192.168.122.177

   # 프론트엔드용 (Next.js)
   NEXT_PUBLIC_HOST_IP=${HOST_IP}
   NEXT_PUBLIC_API_URL=http://${HOST_IP}:8000

   # 프론트엔드용 (SvelteKit)
   PUBLIC_HOST_IP=${HOST_IP}
   PUBLIC_API_URL=http://${HOST_IP}:8000

   # 백엔드 서비스 URL들
   KOREAN_RAG_SERVICE_URL=http://${HOST_IP}:8009
   RAG_ORCHESTRATOR_URL=http://${HOST_IP}:8008
   ADMIN_PANEL_URL=http://${HOST_IP}:3003

   # 데이터베이스 URL
   DATABASE_URL=postgresql+asyncpg://user:pass@${HOST_IP}:5433/db
   REDIS_URL=redis://${HOST_IP}:6379
   ```

3. **적용 대상 확장**:
   - **웹 브라우저 링크**: 모든 a href, window.open 등
   - **AJAX/Fetch 요청**: API 호출, 리소스 로드
   - **WebSocket 연결**: 실시간 통신
   - **이미지/CSS 리소스**: 정적 파일 경로
   - **리다이렉트 URL**: 페이지 전환 및 인증 콜백
   - **Iframe 소스**: 내장 페이지 및 위젯
   - **서비스 디스커버리**: 마이크로서비스 간 연결

4. **코드 구현 예시**:
   ```python
   # Python - 모든 연결에 HOST_IP 사용
   import os
   HOST_IP = os.getenv("HOST_IP", "localhost")

   # API 클라이언트
   api_client = f"http://{HOST_IP}:8000"

   # 데이터베이스 연결
   db_url = f"postgresql://{HOST_IP}:5432/db"

   # 서비스 간 통신
   rag_service_url = f"http://{HOST_IP}:8008"
   ```

   ```javascript
   // JavaScript - 모든 연결에 HOST_IP 사용
   const HOST_IP = process.env.NEXT_PUBLIC_HOST_IP || 'localhost';

   // API 요청
   const apiUrl = `http://${HOST_IP}:8000/api/v1/chat`;

   // 페이지 링크
   const adminUrl = `http://${HOST_IP}:3003/admin`;

   // WebSocket 연결
   const wsUrl = `ws://${HOST_IP}:8000/ws`;
   ```

5. **금지 사항**:
   ```bash
   # ❌ 개별 서비스별 IP 변수 생성 금지
   FRONTEND_IP=192.168.122.177
   BACKEND_IP=192.168.122.177
   DATABASE_IP=192.168.122.177

   # ❌ 하드코딩된 URL 사용 금지
   API_URL=http://192.168.122.177:8000
   ADMIN_URL=http://192.168.122.177:3003
   ```

### 전체 시스템 일관성 확보
- **설정 파일 통합**: 모든 IP 관련 설정을 .env 파일에서 HOST_IP 참조
- **환경별 배포**: 환경에 따라 .env 파일의 HOST_IP만 변경하면 전체 시스템 적용
- **개발/프로덕션 일치**: 동일한 구조로 IP 설정하여 환경 간 일관성 보장

이 원칙을 통해 시스템 전체에서 일관된 네트워크 설정을 유지하고 환경 이식성을 보장합니다.

## 🌐 제22원칙: HOST_IP 환경변수 통합 관리 원칙 (HOST_IP Environment Variable Unified Management Principle)

**핵심 원칙**: DB 조회 시 HOST IP는 프로젝트 전체의 `.env`의 `HOST_IP`를 이용해야 하며, 이 내용은 **모든 프론트엔드와 백엔드에 동일하게 적용**되어야 합니다.

### HOST_IP 관리 규칙
1. **환경변수 우선 원칙**:
   - 모든 HOST IP 참조는 `.env` 파일의 `HOST_IP` 환경변수를 사용
   - 하드코딩된 IP 주소 사용 절대 금지
   - 서비스별 개별 IP 설정 대신 통합 환경변수 사용

2. **적용 범위**:
   - **백엔드**: Python FastAPI, Flask 등 모든 백엔드 서비스
   - **프론트엔드**: Next.js, SvelteKit 등 모든 프론트엔드 애플리케이션
   - **데이터베이스**: PostgreSQL, Redis 등 DB 연결 시
   - **API 호출**: 내부/외부 서비스 간 통신 시

3. **구현 방법**:
   ```bash
   # .env 파일 설정
   HOST_IP=192.168.122.177
   NEXT_PUBLIC_HOST_IP=192.168.122.177
   ```

   ```python
   # Python 백엔드에서 사용
   import os
   HOST_IP = os.getenv("HOST_IP", "localhost")
   api_url = f"http://{HOST_IP}:8000"
   ```

   ```javascript
   // Next.js 프론트엔드에서 사용
   const HOST_IP = process.env.NEXT_PUBLIC_HOST_IP || 'localhost';
   const apiUrl = `http://${HOST_IP}:8000`;
   ```

   ```javascript
   // SvelteKit 프론트엔드에서 사용
   import { env } from '$env/dynamic/public';
   const HOST_IP = env.PUBLIC_HOST_IP || 'localhost';
   const apiUrl = `http://${HOST_IP}:8000`;
   ```

4. **금지된 사용법**:
   ```python
   # ❌ 하드코딩된 IP 사용 금지
   api_url = "http://192.168.122.177:8000"

   # ❌ 개별 IP 변수 생성 금지
   FRONTEND_IP = "192.168.122.177"
   BACKEND_IP = "192.168.122.177"
   ```

5. **DB 조회 시 HOST_IP 활용**:
   ```python
   # ✅ 올바른 방법: 환경변수 사용
   HOST_IP = os.getenv("HOST_IP", "localhost")
   server_url = f"http://{HOST_IP}:{server_port}"

   # ❌ 잘못된 방법: 하드코딩
   server_url = f"http://192.168.122.177:{server_port}"
   ```

### 일관성 보장 절차
1. **프로젝트 시작 시**:
   - .env 파일에서 HOST_IP 확인
   - 모든 서비스 설정에서 HOST_IP 환경변수 사용 확인
   - 하드코딩된 IP 주소 제거

2. **새 서비스 개발 시**:
   - 항상 HOST_IP 환경변수 참조
   - IP 변경 시 .env 파일만 수정하면 전체 적용되도록 설계
   - 서비스별 개별 IP 설정 금지

3. **배포 환경별 관리**:
   ```bash
   # 개발 환경
   HOST_IP=192.168.122.177

   # 프로덕션 환경
   HOST_IP=production.server.ip

   # 로컬 테스트 환경
   HOST_IP=localhost
   ```

### 위반 시 위험성
- **환경별 설정 불일치**: 개발/프로덕션 환경 간 IP 설정 혼란
- **배포 실패**: 하드코딩된 IP로 인한 환경 이식성 문제
- **유지보수 복잡성**: IP 변경 시 여러 파일 수정 필요
- **서비스 연결 실패**: 일관되지 않은 IP 설정으로 인한 통신 오류

### 구현 우선순위
1. **High**: 기존 하드코딩된 IP 주소를 HOST_IP 환경변수로 변경
2. **Medium**: 새로운 서비스 개발 시 HOST_IP 환경변수 사용 템플릿 적용
3. **Low**: HOST_IP 변경 시 자동 전파 시스템 구축

이 원칙을 통해 모든 서비스에서 일관된 호스트 IP 관리를 보장하고 환경별 배포 안정성을 확보합니다.

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.