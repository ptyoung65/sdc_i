# 🚀 SDC Air-gap 빠른 시작 가이드

**Smart Document Companion - Korean RAG System**  
**Air-gap 환경 완전 오프라인 설치 및 실행**

---

## 📋 개요

이 가이드는 인터넷이 완전히 차단된 Air-gap 환경에서 SDC 시스템을 설치하고 실행하는 방법을 설명합니다.

### ✨ 주요 기능
- 🤖 Multi-LLM 한국어 RAG 시스템
- 📄 다중 포맷 문서 처리 (PDF, DOCX, PPTX, XLSX)
- 💬 실시간 AI 채팅 인터페이스
- 🔍 하이브리드 검색 (벡터 + 키워드)
- 📊 모니터링 및 관리 대시보드
- 🔒 완전 오프라인 운영

---

## ⚡ 초간단 설치 (자동)

### 1단계: 설치 스크립트 실행
```bash
# 완전 자동 설치 (권장)
sudo ./install-airgap-complete.sh
```

### 2단계: 웹 접속 및 설정
1. 브라우저에서 http://localhost:3000 접속
2. `admin@sdc.local` / `admin123` 로그인
3. **즉시 비밀번호 변경**
4. AI API 키 설정 (선택사항)

### 3단계: 사용 시작! 🎉
- 문서 업로드 및 AI 대화 시작

---

## 🛠️ 수동 설치 (단계별)

### 사전 준비
```bash
# 필수 패키지 설치 (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y podman podman-compose python3 python3-venv curl wget

# 또는 RHEL/CentOS
sudo yum install -y podman podman-compose python3 python3-venv curl wget
```

### 1. 배포 패키지 생성 (인터넷 환경)
```bash
# 패키지 빌드 (최초 1회)
./build-airgap-package.sh full

# 생성된 패키지를 Air-gap 시스템으로 전송
# USB: cp build/sdc-airgap-*.tar.gz /mnt/usb/
# SCP: scp build/sdc-airgap-*.tar.gz user@target:/tmp/
```

### 2. Air-gap 시스템에서 설치
```bash
# 패키지 압축 해제
tar -xzf sdc-airgap-*.tar.gz
cd sdc-airgap-*

# 자동 설치
sudo ./install-airgap-complete.sh

# 또는 기존 설치 스크립트 사용
sudo ./scripts/install_airgap.sh
```

### 3. 서비스 시작
```bash
cd /opt/sdc  # 또는 설치된 디렉토리
sudo ./scripts/start_services.sh
```

---

## 🌐 서비스 접속 정보

### 주요 서비스
| 서비스 | URL | 설명 |
|--------|-----|------|
| **메인 애플리케이션** | http://localhost:3000 | AI 채팅 및 문서 관리 |
| **API 문서** | http://localhost:8000/docs | OpenAPI 문서 |
| **백엔드 상태** | http://localhost:8000/health | 헬스체크 |

### 모니터링 & 관리
| 서비스 | URL | 계정 |
|--------|-----|------|
| **Grafana 대시보드** | http://localhost:3010 | admin / [생성된 비밀번호] |
| **Prometheus** | http://localhost:9090 | - |

### 데이터베이스 (내부용)
| 서비스 | 접속 | 정보 |
|--------|-----|------|
| **PostgreSQL** | localhost:5432 | sdc_db / sdc_user |
| **Redis** | localhost:6379 | 캐시 및 세션 |
| **Milvus** | localhost:19530 | 벡터 데이터베이스 |
| **Elasticsearch** | localhost:9200 | 전문 검색 |

---

## 🔐 보안 설정 (필수)

### ⚠️ 설치 후 즉시 수행해야 할 보안 작업

#### 1. 관리자 비밀번호 변경
```bash
# 웹 접속 후 변경
# URL: http://localhost:3000
# 기본 계정: admin@sdc.local / admin123
```

#### 2. AI API 키 설정 (선택사항)
```bash
sudo nano /opt/sdc/.env

# 다음 항목 설정
OPENAI_API_KEY=your_api_key_here
ANTHROPIC_API_KEY=your_api_key_here
GOOGLE_API_KEY=your_api_key_here

# 서비스 재시작
cd /opt/sdc
sudo podman-compose restart backend
```

#### 3. 보안 크리덴셜 백업
```bash
# 설치 시 생성된 보안 파일 백업
sudo cp /tmp/sdc-secure-*/credentials.enc ~/sdc-credentials-backup.enc
sudo chmod 600 ~/sdc-credentials-backup.enc
```

---

## 🎯 기본 사용법

### 1. 문서 업로드
1. 웹 인터페이스 접속 (http://localhost:3000)
2. 로그인 후 문서 업로드 버튼 클릭
3. 지원 파일: PDF, DOCX, PPTX, XLSX, TXT, MD

### 2. AI 대화
1. 채팅 인터페이스에서 질문 입력
2. 업로드된 문서 기반으로 AI가 답변
3. 다양한 AI 모델 선택 가능

### 3. 문서 검색
- 키워드 검색
- 유사도 검색  
- 하이브리드 검색

---

## 📊 시스템 관리

### 서비스 관리
```bash
cd /opt/sdc

# 모든 서비스 시작
sudo podman-compose up -d

# 모든 서비스 중지
sudo podman-compose down

# 특정 서비스 재시작
sudo podman-compose restart backend
sudo podman-compose restart frontend

# 서비스 상태 확인
sudo podman ps
```

### 로그 확인
```bash
# 전체 로그
sudo podman-compose logs -f

# 특정 서비스 로그
sudo podman-compose logs -f backend
sudo podman-compose logs -f frontend

# 시스템 로그
tail -f /var/log/sdc/app.log
```

### 데이터베이스 관리
```bash
# 데이터베이스 백업
sudo podman exec sdc-postgres pg_dump -U sdc_user sdc_db > backup_$(date +%Y%m%d).sql

# 백업 복원
sudo podman exec -i sdc-postgres psql -U sdc_user sdc_db < backup_YYYYMMDD.sql
```

---

## 🚨 문제 해결

### 자주 발생하는 문제들

#### 서비스가 시작되지 않음
```bash
# 포트 충돌 확인
sudo lsof -i :3000
sudo lsof -i :8000

# 충돌하는 프로세스 종료
sudo lsof -ti:3000 | xargs -r kill -9

# 컨테이너 상태 확인
sudo podman ps -a
```

#### 데이터베이스 연결 오류
```bash
# PostgreSQL 상태 확인
sudo podman exec sdc-postgres pg_isready -U sdc_user

# 데이터베이스 재시작
sudo podman-compose restart postgres

# 연결 테스트
sudo podman exec sdc-postgres psql -U sdc_user -d sdc_db -c "SELECT 1;"
```

#### 메모리 부족
```bash
# 메모리 사용량 확인
free -h
sudo podman stats

# 불필요한 서비스 중지 (임시)
sudo podman-compose stop grafana prometheus
```

#### 웹 인터페이스 접속 안됨
```bash
# 프론트엔드 상태 확인
curl http://localhost:3000

# 백엔드 API 확인  
curl http://localhost:8000/health

# Nginx 로그 확인 (사용 시)
sudo podman logs sdc-nginx
```

---

## 🔄 업데이트 및 유지보수

### 시스템 업데이트
1. 새 버전의 air-gap 패키지 생성
2. 기존 데이터 백업
3. 새 패키지로 재설치
4. 데이터 복원

### 정기 유지보수
```bash
# 로그 정리 (월 1회)
sudo find /opt/sdc/logs -name "*.log" -mtime +30 -delete

# 데이터베이스 최적화 (월 1회)
sudo podman exec sdc-postgres vacuumdb -U sdc_user -d sdc_db --analyze

# 디스크 사용량 확인
df -h
du -sh /opt/sdc
```

---

## 📈 성능 최적화

### 권장 시스템 사양
- **최소**: 8GB RAM, 4 CPU 코어, 50GB 디스크
- **권장**: 16GB RAM, 8 CPU 코어, 100GB 디스크
- **고성능**: 32GB RAM, 16 CPU 코어, 200GB SSD

### 튜닝 옵션
```bash
# PostgreSQL 메모리 조정
sudo podman exec sdc-postgres psql -U postgres -c "ALTER SYSTEM SET shared_buffers = '512MB';"

# Redis 메모리 제한
sudo podman exec sdc-redis redis-cli CONFIG SET maxmemory 1gb

# 컨테이너 리소스 제한 조정 (docker-compose.yml)
```

---

## 🆘 지원 및 도움

### 문서 위치
- **상세 설치 가이드**: `AIR-GAP-DEPLOYMENT-GUIDE.md`
- **개발 문서**: `dev-environment/docs/DEVELOPMENT_GUIDE.md`
- **API 문서**: http://localhost:8000/docs
- **설치 보고서**: `/opt/sdc/installation_report.md`

### 로그 파일 위치
- **애플리케이션 로그**: `/opt/sdc/logs/`
- **설치 로그**: 설치 디렉토리의 `install_*.log`
- **컨테이너 로그**: `sudo podman logs <container_name>`

### 진단 명령어
```bash
# 종합 상태 체크
curl -s http://localhost:8000/health | jq '.'

# 시스템 리소스 체크
htop
df -h
sudo podman stats

# 네트워크 연결 체크
sudo ss -tuln | grep -E ":(3000|8000|5432|6379)"
```

---

## ✅ 설치 완료 체크리스트

설치 완료 후 다음 사항들을 확인하세요:

- [ ] 웹 인터페이스 접속 확인 (http://localhost:3000)
- [ ] API 문서 접속 확인 (http://localhost:8000/docs)
- [ ] 관리자 비밀번호 변경 완료
- [ ] 테스트 문서 업로드 및 AI 대화 테스트
- [ ] 보안 크리덴셜 파일 백업
- [ ] 모니터링 대시보드 접속 확인 (http://localhost:3010)
- [ ] 데이터베이스 백업 절차 확인
- [ ] AI API 키 설정 (필요 시)

---

## 🎉 완료!

축하합니다! SDC Korean RAG 시스템이 Air-gap 환경에 성공적으로 설치되었습니다.

이제 완전히 오프라인 환경에서 한국어 문서 기반 AI 대화 시스템을 사용할 수 있습니다.

**💡 팁**: 시스템 사용 중 문제가 발생하면 먼저 로그를 확인하고, 필요시 서비스를 재시작해보세요.

---

**SDC v1.0.0** | Air-gap Deployment | Korean RAG System  
*Generated with Claude Code* 🤖