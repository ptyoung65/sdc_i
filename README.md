# SDC - Smart Document Companion

🤖 **Multi-LLM 기반 한국어 RAG 시스템** | 🔒 **완전 Air-gap 환경 지원**

## 🚀 핵심 기능

- **🤖 Multi-LLM RAG System**: OpenAI, Anthropic, Google, Ollama 등 다양한 LLM 한국어 최적화
- **📄 Multi-Format Documents**: PDF, DOCX, PPTX, XLSX 등 다중 포맷 문서 처리
- **🔍 Hybrid Search**: 벡터 + 키워드 검색 결합으로 정확한 정보 검색
- **💬 Real-time AI Chat**: 실시간 AI 대화 인터페이스
- **🔒 Complete Air-gap**: 완전 오프라인 환경 지원 (인터넷 연결 불필요)
- **🛡️ Enterprise Security**: JWT 인증, RBAC, Rate Limiting, 보안 헤더
- **📊 Monitoring & Dashboard**: Grafana/Prometheus 기반 종합 모니터링

## 🔒 Air-gap 배포 (권장)

> **완전 오프라인 환경**에서 인터넷 연결 없이 설치하고 사용할 수 있습니다.

### ⚡ 초간단 설치 (자동)
```bash
# 자동 설치 (권장)
sudo ./install-airgap-complete.sh

# 웹 접속: http://localhost:3000
# 로그인: admin@sdc.local / admin123 (즉시 변경 권장)
```

### 🛠️ 수동 설치 (단계별)
```bash
# 1. 인터넷 환경에서 캐시 준비 (1회)
./prepare-offline-cache.sh

# 2. Air-gap 환경에서 패키지 빌드
./build-airgap-offline.sh full

# 3. 시스템 설치
sudo ./install-airgap-complete.sh

# 4. 시스템 검증
./validate-airgap-system.sh
```

### 📚 Air-gap 문서
- **빠른 시작**: [`AIR-GAP-QUICK-START.md`](AIR-GAP-QUICK-START.md)
- **상세 가이드**: [`AIR-GAP-OFFLINE-COMPLETE-GUIDE.md`](AIR-GAP-OFFLINE-COMPLETE-GUIDE.md)
- **배포 상태**: [`AIRGAP-DEPLOYMENT-STATUS.md`](AIRGAP-DEPLOYMENT-STATUS.md)

## 📋 Prerequisites

- Docker or Podman
- Node.js 20+
- Python 3.11+
- PostgreSQL 16+
- Redis 7+

## 🛠 Installation

### Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/sdc.git
cd sdc

# Setup environment
make setup

# Start services
make up

# Check health
make health
```

### Manual Setup

1. **Environment Setup**
```bash
cp .env.example .env
# Edit .env with your configuration
```

2. **Install Dependencies**
```bash
# Frontend
cd frontend
npm install

# Backend
cd ../backend
pip install -r requirements.txt
```

3. **Start Services**
```bash
# Using Docker Compose
docker-compose up -d

# Using Podman
podman-compose up -d
```

4. **Run Migrations**
```bash
make db-migrate
```

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Layer 5: CI/CD                    │
│         (GitLab CI, GitHub Actions, Podman)         │
├─────────────────────────────────────────────────────┤
│              Layer 4: Security & Monitoring         │
│     (Rate Limiter, Auth Middleware, Metrics)        │
├─────────────────────────────────────────────────────┤
│            Layer 3: Hybrid Search Database          │
│    (PostgreSQL + Milvus + Elasticsearch)            │
├─────────────────────────────────────────────────────┤
│         Layer 2: AI & RAG Orchestration             │
│    (LangGraph, Multi-LLM, Embedding Service)        │
├─────────────────────────────────────────────────────┤
│              Layer 1: Application Layer             │
│         (Next.js Frontend + FastAPI Backend)        │
└─────────────────────────────────────────────────────┘
```

## 🔧 Development

### Running Tests
```bash
# Run all tests
make test

# Backend tests only
make test-backend

# Frontend tests only
make test-frontend
```

### Code Quality
```bash
# Run linters
make lint

# Format code
make format

# Security scan
make security-scan
```

### Database Management
```bash
# Run migrations
make db-migrate

# Rollback migration
make db-rollback

# Reset database
make db-reset
```

## 📊 Monitoring

### Health Check
```bash
make health
```

### View Metrics
```bash
make metrics
```

### View Logs
```bash
# All services
make logs

# Specific service
make logs-backend
make logs-frontend
```

## 🚢 Deployment

### Staging Deployment
```bash
make deploy-staging
```

### Production Deployment
```bash
make deploy-production
```

## 📁 Project Structure

```
sdc/
├── frontend/               # Next.js frontend application
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── services/      # API services
│   │   └── store/         # Zustand state management
│   └── public/            # Static assets
├── backend/               # FastAPI backend application
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Core functionality
│   │   ├── models/       # Database models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Business logic
│   └── tests/            # Test files
├── scripts/              # Utility scripts
├── nginx/                # Nginx configuration
├── docker-compose.yml    # Docker compose configuration
├── Containerfile         # Podman/Docker build file
└── Makefile             # Build automation
```

## 🔐 Security

- JWT-based authentication
- Rate limiting per user/IP
- CORS protection
- SQL injection prevention
- XSS protection headers
- CSRF protection
- Secure password hashing (bcrypt)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- LangGraph for advanced RAG orchestration
- OpenAI, Anthropic, Google for LLM APIs
- Milvus for vector database
- Elasticsearch for full-text search
- FastAPI and Next.js communities

## 📞 Support

For support, email support@sdc.example.com or open an issue in the repository.

## 🚦 Status

- Backend API: ✅ Operational
- Frontend UI: ✅ Operational
- Vector Database: ✅ Operational
- Search Engine: ✅ Operational
- AI Services: ✅ Operational

---

Made with ❤️ by the SDC Team