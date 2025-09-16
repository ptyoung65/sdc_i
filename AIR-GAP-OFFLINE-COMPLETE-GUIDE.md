# 🔒 SDC 완전 오프라인 Air-gap 배포 가이드

**Smart Document Companion - 완전 오프라인 버전**  
**인터넷 연결 없이 완전한 Air-gap 환경에서 운영**

---

## 🎯 개요

이 가이드는 **완전히 인터넷이 차단된 Air-gap 환경**에서 SDC 시스템을 구축하고 운영하는 방법을 설명합니다.

### 🔒 Air-gap 특징
- ✅ **완전 오프라인**: 인터넷 연결 절대 불필요
- ✅ **로컬 리소스만 사용**: 모든 패키지와 이미지 로컬 캐시
- ✅ **보안 강화**: 외부 네트워크 접근 완전 차단
- ✅ **자동화된 설치**: 원클릭 배포 시스템

---

## 📋 시스템 요구사항

### 개발/준비 환경 (인터넷 연결)
- **OS**: Linux (Ubuntu 20.04+, RHEL 8+)
- **CPU**: 4코어 이상
- **RAM**: 8GB 이상
- **디스크**: 50GB 이상 여유공간
- **네트워크**: 인터넷 연결 필요 (캐시 다운로드용)

### Air-gap 대상 환경 (완전 격리)
- **OS**: Linux (동일 배포판 권장)
- **CPU**: 8코어 이상 
- **RAM**: 16GB 이상
- **디스크**: 100GB 이상 여유공간
- **네트워크**: 완전 차단 (인터넷 접근 불가)

---

## 🚀 완전 오프라인 배포 프로세스

### 🌐 단계 1: 인터넷 환경에서 캐시 준비

```bash
# 1. 프로젝트 준비
cd /path/to/sdc_i

# 2. 오프라인 캐시 다운로드 (30-60분 소요)
./prepare-offline-cache.sh

# 다운로드 내용:
#   • 컨테이너 이미지 13개 (~8GB)
#   • Python 패키지 150개 (~2GB)  
#   • Node.js 패키지 80개 (~1GB)
```

### 📦 단계 2: 오프라인 배포 패키지 생성

```bash
# 오프라인 빌드 실행 (인터넷 연결 없이도 가능)
./build-airgap-offline.sh

# 생성물: sdc-airgap-offline-1.0.0-YYYYMMDD_HHMMSS.tar.gz
# 크기: 약 12-15GB (압축됨)
```

### 🚚 단계 3: Air-gap 환경으로 전송

```bash
# USB 저장매체 사용
cp build/sdc-airgap-offline-*.tar.gz /mnt/usb/

# 또는 승인된 네트워크 전송
scp build/sdc-airgap-offline-*.tar.gz user@airgap-server:/tmp/
```

### 🔒 단계 4: Air-gap 환경에서 설치

```bash
# 1. 패키지 압축 해제
tar -xzf sdc-airgap-offline-*.tar.gz
cd sdc-airgap-offline-*

# 2. 완전 오프라인 설치 (15-30분)
sudo ./install_airgap_offline.sh

# 3. Air-gap 보안 강화 (선택사항)
sudo ./configs/secure_airgap.sh
```

### ✅ 단계 5: 서비스 시작 및 접속

```bash
# Air-gap 모드로 서비스 시작
cd /opt/sdc
sudo podman-compose -f docker-compose.yml -f docker-compose.airgap.yml up -d

# 웹 인터페이스 접속
# http://localhost:3000
```

---

## 🛠️ 상세 설치 과정

### A. 캐시 준비 (인터넷 환경)

#### A-1. 사전 준비
```bash
# 필수 도구 설치
sudo apt-get update
sudo apt-get install -y podman podman-compose python3 python3-venv nodejs npm

# 또는 RHEL/CentOS
sudo yum install -y podman podman-compose python3 python3-venv nodejs npm
```

#### A-2. 캐시 다운로드 실행
```bash
./prepare-offline-cache.sh

# 진행 과정:
# [1/6] 인터넷 연결 확인
# [2/6] 캐시 디렉토리 초기화  
# [3/6] 컨테이너 이미지 다운로드 (가장 오래 걸림)
# [4/6] Python 패키지 다운로드
# [5/6] Node.js 패키지 다운로드
# [6/6] 캐시 정보 파일 생성
```

#### A-3. 캐시 검증
```bash
# 캐시 상태 확인
ls -la offline-cache/
cat offline-cache/cache_info.txt

# 예상 구조:
# offline-cache/
# ├── container-images/     # 13개 .tar.gz 파일
# ├── python-packages/      # 150개 .whl 파일
# └── node-packages/        # 3-5개 .tar.gz 파일
```

### B. 오프라인 빌드 (인터넷 없이 가능)

#### B-1. 오프라인 환경 검증
```bash
# 네트워크 차단 테스트
ping -c 1 8.8.8.8
# 실패해야 정상 (오프라인 확인)

# 로컬 리소스 확인
podman images
ls -la offline-cache/
```

#### B-2. 오프라인 빌드 실행
```bash
# 빌드 시작
./build-airgap-offline.sh

# 진행 과정:
# [1/12] 오프라인 환경 검증
# [2/12] 캐시 구조 초기화
# [3/12] 빌드 환경 준비
# [4/12] 소스 코드 복사
# [5/12] 로컬 컨테이너 이미지 처리
# [6/12] Python 패키지 오프라인 처리  
# [7/12] Node.js 패키지 오프라인 처리
# [8/12] Air-gap 설정 템플릿 생성
# [9/12] 오프라인 문서 생성
# [10/12] 오프라인 설치 스크립트 생성
# [11/12] 체크섬 생성
# [12/12] 최종 패키지 생성
```

#### B-3. 빌드 결과 확인
```bash
ls -la build/

# 예상 결과:
# sdc-airgap-offline-1.0.0-20241014_143022.tar.gz  (12-15GB)
# sdc-airgap-offline-1.0.0-20241014_143022.info   (정보 파일)
```

### C. Air-gap 설치 (완전 격리 환경)

#### C-1. 환경 검증
```bash
# 네트워크 격리 확인 (실패해야 정상)
ping -c 1 8.8.8.8
curl -I http://google.com

# 시스템 리소스 확인
free -h    # 16GB+ RAM
df -h      # 100GB+ 디스크
nproc      # 8+ CPU
```

#### C-2. 패키지 설치
```bash
# 압축 해제
tar -xzf sdc-airgap-offline-*.tar.gz
cd sdc-airgap-offline-*

# 구성 요소 확인
ls -la
# containers/         # 컨테이너 이미지들
# python-packages/    # Python wheel 파일들
# node-packages/      # Node.js 패키지들
# configs/            # Air-gap 설정들
# docs/               # 오프라인 문서들
# install_airgap_offline.sh  # 설치 스크립트

# 오프라인 설치 실행
sudo ./install_airgap_offline.sh
```

#### C-3. 설치 과정 모니터링
```bash
# 설치 과정:
# [1/8] 권한 확인
# [2/8] 오프라인 환경 확인  
# [3/8] 설치 디렉토리 생성
# [4/8] 소스 코드 복사
# [5/8] 컨테이너 이미지 로드
# [6/8] Python 패키지 설치
# [7/8] Node.js 패키지 설치  
# [8/8] 설정 파일 적용

# 설치 완료 후 확인
ls -la /opt/sdc/
podman images
```

---

## 🔐 Air-gap 보안 설정

### 네트워크 보안 강화 (선택사항)

```bash
# Air-gap 보안 스크립트 실행
sudo ./configs/secure_airgap.sh

# 적용되는 보안 설정:
# • 모든 외부 네트워크 차단
# • 로컬 트래픽만 허용  
# • DNS를 로컬로 제한
# • 방화벽 규칙 적용
# • hosts 파일 보안 설정
```

### 환경 설정 확인

```bash
# Air-gap 전용 설정 적용
cp configs/.env.airgap /opt/sdc/.env

# 주요 설정 항목:
# AIRGAP_MODE=true
# OFFLINE_MODE=true  
# DISABLE_EXTERNAL_REQUESTS=true
# OLLAMA_BASE_URL=http://localhost:11434  # 로컬 LLM
```

---

## 🚀 서비스 시작 및 관리

### Air-gap 모드 서비스 시작

```bash
cd /opt/sdc

# Air-gap 전용 설정으로 시작
sudo podman-compose -f docker-compose.yml -f docker-compose.airgap.yml up -d

# 서비스 상태 확인
sudo podman ps

# 예상 컨테이너들:
# sdc-postgres      # PostgreSQL 데이터베이스
# sdc-redis         # Redis 캐시
# sdc-milvus        # 벡터 데이터베이스  
# sdc-elasticsearch # 전문 검색
# sdc-backend       # FastAPI 백엔드
# sdc-frontend      # Next.js 프론트엔드
# sdc-searxng       # 로컬 검색엔진
# sdc-prometheus    # 모니터링
# sdc-grafana       # 대시보드
```

### 서비스 접속 정보

| 서비스 | URL | 용도 | 접속 가능 |
|--------|-----|------|-----------|
| **메인 애플리케이션** | http://localhost:3000 | AI 채팅 및 문서 관리 | ✅ |
| **API 문서** | http://localhost:8000/docs | OpenAPI 스웩 | ✅ |
| **백엔드 상태** | http://localhost:8000/health | 헬스체크 | ✅ |
| **Grafana** | http://localhost:3010 | 모니터링 대시보드 | ✅ |
| **Prometheus** | http://localhost:9090 | 메트릭 수집 | ✅ |
| **SearXNG** | http://localhost:8080 | 로컬 검색 | ✅ |

---

## 🎯 Air-gap 환경에서 사용 가능한 기능

### ✅ 완전 지원되는 기능

1. **문서 업로드 및 처리**
   - PDF, DOCX, PPTX, XLSX, TXT, MD
   - 로컬 문서 파서 사용
   - 벡터 임베딩 생성

2. **AI 대화 시스템**
   - 로컬 임베딩 모델 (KURE-v1)
   - 벡터 유사도 검색
   - 하이브리드 검색 (벡터 + 키워드)

3. **데이터 관리**
   - PostgreSQL 데이터베이스
   - Redis 캐싱
   - Milvus 벡터 스토어
   - Elasticsearch 전문검색

4. **모니터링 및 관리**
   - Grafana 대시보드
   - Prometheus 메트릭
   - 시스템 로그 관리

### ❌ 제한되는 기능 (대안 제공)

1. **외부 AI API** → **로컬 Ollama LLM**
   ```bash
   # Ollama 설치 및 모델 다운로드 (선택사항)
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull llama2:7b
   ollama pull codellama:7b
   ```

2. **외부 검색 엔진** → **로컬 SearXNG**
   - 로컬 인덱스 기반 검색
   - 업로드된 문서 내 검색

3. **온라인 문서 가져오기** → **수동 업로드**
   - USB를 통한 문서 전송
   - 로컬 네트워크 공유 폴더

### 🔄 대안 솔루션

#### Ollama 로컬 LLM 설정 (권장)
```bash
# Air-gap 환경에서 Ollama 설치
# 1. 인터넷 환경에서 Ollama 모델 다운로드
# 2. 모델 파일을 Air-gap으로 전송
# 3. 로컬 Ollama 서버 시작

# .env 설정 업데이트
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2:7b
USE_LOCAL_LLM=true
```

---

## 🔧 문제 해결 및 유지보수

### 일반적인 문제들

#### 1. 컨테이너 이미지 로드 실패
```bash
# 이미지 수동 로드
cd /path/to/sdc-airgap-offline/containers
sudo ./load_images.sh

# 이미지 목록 확인
sudo podman images
```

#### 2. Python 패키지 설치 오류
```bash
# 패키지 수동 재설치
cd /path/to/sdc-airgap-offline/python-packages
sudo ./install_packages.sh /opt/sdc
```

#### 3. Node.js 패키지 설치 오류
```bash
# Node.js 패키지 수동 재설치  
cd /path/to/sdc-airgap-offline/node-packages
sudo ./install_packages.sh /opt/sdc
```

#### 4. 서비스 시작 실패
```bash
# 로그 확인
sudo podman logs sdc-backend
sudo podman logs sdc-frontend

# 서비스 재시작
sudo podman-compose restart sdc-backend
```

#### 5. 네트워크 접근 오류
```bash
# Air-gap 네트워크 설정 확인
sudo podman network ls
sudo iptables -L

# 로컬 서비스 상태 확인
curl http://localhost:3000
curl http://localhost:8000/health
```

### 정기 유지보수

#### 데이터베이스 백업
```bash
# PostgreSQL 백업
sudo podman exec sdc-postgres pg_dump -U sdc_user sdc_db > backup_$(date +%Y%m%d).sql

# Redis 백업
sudo podman exec sdc-redis redis-cli SAVE
sudo cp /var/lib/containers/storage/volumes/sdc_redis_data/_data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

#### 로그 관리
```bash
# 로그 크기 확인
sudo du -sh /opt/sdc/logs/

# 오래된 로그 정리 (30일 이전)
sudo find /opt/sdc/logs -name "*.log" -mtime +30 -delete

# 컨테이너 로그 확인
sudo podman logs --tail 100 sdc-backend
```

#### 시스템 성능 모니터링
```bash
# 리소스 사용량 확인
free -h
df -h
sudo podman stats

# Grafana 대시보드 접속
# http://localhost:3010
# admin / [설치시 생성된 비밀번호]
```

---

## 📊 성능 최적화

### Air-gap 환경 최적화 설정

#### 메모리 최적화
```bash
# PostgreSQL 메모리 설정
sudo podman exec sdc-postgres psql -U postgres -c "
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
SELECT pg_reload_conf();
"

# Redis 메모리 제한
sudo podman exec sdc-redis redis-cli CONFIG SET maxmemory 1gb
sudo podman exec sdc-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

#### 디스크 최적화
```bash
# 로그 로테이션 설정
sudo nano /etc/logrotate.d/sdc
# /opt/sdc/logs/*.log {
#     daily
#     missingok
#     rotate 7
#     compress
#     notifempty
#     copytruncate
# }
```

#### 네트워크 최적화
```bash
# 내부 네트워크 최적화
sudo sysctl -w net.core.somaxconn=1024
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=2048
```

---

## 📈 모니터링 및 알림

### Grafana 대시보드 설정

```bash
# Grafana 접속: http://localhost:3010
# 기본 계정: admin / [설치시 비밀번호]

# 주요 대시보드:
# 1. 시스템 리소스 (CPU, 메모리, 디스크)
# 2. 컨테이너 상태 및 성능  
# 3. 데이터베이스 성능
# 4. 애플리케이션 메트릭
# 5. 네트워크 트래픽 (로컬만)
```

### 로그 모니터링

```bash
# 실시간 로그 모니터링
sudo tail -f /opt/sdc/logs/app.log

# 오류 로그 검색
sudo grep -i error /opt/sdc/logs/*.log

# 시스템 로그 확인
sudo journalctl -u podman -f
```

---

## 🆘 응급 상황 대처

### 시스템 복구

#### 전체 서비스 재시작
```bash
cd /opt/sdc
sudo podman-compose down
sudo podman system prune -f
sudo podman-compose -f docker-compose.yml -f docker-compose.airgap.yml up -d
```

#### 데이터베이스 복구
```bash
# PostgreSQL 복구
sudo podman exec -i sdc-postgres psql -U sdc_user sdc_db < backup_YYYYMMDD.sql

# Redis 복구
sudo podman stop sdc-redis
sudo cp redis_backup_YYYYMMDD.rdb /var/lib/containers/storage/volumes/sdc_redis_data/_data/dump.rdb
sudo podman start sdc-redis
```

#### 설정 초기화
```bash
# 설정 파일 백업에서 복구
sudo cp configs/.env.airgap /opt/sdc/.env
sudo chown sdc:sdc /opt/sdc/.env
```

---

## ✅ 설치 검증 체크리스트

Air-gap 설치 완료 후 다음 항목들을 확인하세요:

### 기본 시스템 확인
- [ ] 모든 컨테이너 정상 실행 (`podman ps`)
- [ ] 웹 인터페이스 접속 (http://localhost:3000)
- [ ] API 문서 접속 (http://localhost:8000/docs)
- [ ] 백엔드 상태 확인 (http://localhost:8000/health)

### 기능 테스트
- [ ] 문서 업로드 테스트 (PDF, DOCX 등)
- [ ] AI 채팅 기능 테스트
- [ ] 문서 검색 기능 테스트
- [ ] 관리자 계정 로그인 테스트

### 보안 확인
- [ ] 외부 네트워크 차단 확인 (`ping 8.8.8.8` 실패)
- [ ] 기본 비밀번호 변경 완료
- [ ] 로컬 네트워크만 접근 가능 확인

### 모니터링 설정
- [ ] Grafana 대시보드 접속 (http://localhost:3010)
- [ ] 시스템 메트릭 정상 수집 확인
- [ ] 로그 파일 정상 생성 확인

### 백업 및 복구
- [ ] 데이터베이스 백업 테스트
- [ ] 설정 파일 백업 완료
- [ ] 복구 절차 문서화 완료

---

## 🎉 완료!

축하합니다! SDC Korean RAG 시스템이 완전한 Air-gap 환경에 성공적으로 설치되었습니다.

### 🔒 최종 보안 점검

1. **네트워크 격리 확인**
   ```bash
   ping -c 1 8.8.8.8  # 실패해야 정상
   curl -I http://google.com  # 실패해야 정상
   ```

2. **로컬 서비스만 접근 가능 확인**
   ```bash
   curl http://localhost:3000  # 성공
   curl http://localhost:8000/health  # 성공
   ```

3. **방화벽 설정 확인**
   ```bash
   sudo ufw status  # 외부 접근 차단 확인
   ```

### 🚀 이제 사용 시작!

- **메인 애플리케이션**: http://localhost:3000
- **관리자 대시보드**: http://localhost:3010
- **API 문서**: http://localhost:8000/docs

완전히 격리된 환경에서 안전하고 강력한 AI 문서 처리 시스템을 사용하세요! 

---

**SDC v1.0.0** | Air-gap Complete Offline Edition  
*최종 수정: 2024년 9월 14일*  
*문서 버전: 1.0.0*