#!/bin/bash

##############################################################################
# Open WebUI Remote DB Connection Script
# 원격 PostgreSQL, Milvus 서버에 연결하여 Open WebUI 실행
##############################################################################
# 사용법:
#   ./podman-start-remote.sh --db-host <IP>           - 원격 DB 서버 연결
#   ./podman-start-remote.sh --db-host <IP> --rebuild - 강제 재빌드
#   ./podman-start-remote.sh --help                   - 도움말
##############################################################################
# 원격 DB 서버 요구사항:
#   - PostgreSQL (포트 5433): sdc_dev 데이터베이스
#   - Milvus (포트 19530): 벡터 데이터베이스
#   - 방화벽에서 해당 포트 개방 필요
##############################################################################

set -e

# 스크립트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ============================================
# 옵션 플래그 확인
# ============================================
FORCE_REBUILD=false
USE_PROD_LLM=false
USE_PROD_EMBEDDING=false
USE_SSL_PORT=false
SSL_VERIFY_ENABLED=false
INTERNAL_SSL_VERIFY=false
EXTERNAL_SSL_VERIFY=false
REMOTE_DB_HOST=""

for arg in "$@"; do
    case $arg in
        --db-host=*)
            REMOTE_DB_HOST="${arg#*=}"
            echo "🌐 원격 DB 서버: ${REMOTE_DB_HOST}"
            ;;
        --db-host)
            shift
            REMOTE_DB_HOST="$1"
            echo "🌐 원격 DB 서버: ${REMOTE_DB_HOST}"
            ;;
        --rebuild|-r)
            FORCE_REBUILD=true
            echo "🔨 강제 재빌드 모드 활성화"
            ;;
        --prod-llm)
            USE_PROD_LLM=true
            echo "🔄 개발 환경에서 운영 LLM 사용"
            ;;
        --prod-embedding)
            USE_PROD_EMBEDDING=true
            echo "🔄 개발 환경에서 운영 임베딩 사용"
            ;;
        --prod-all)
            USE_PROD_LLM=true
            USE_PROD_EMBEDDING=true
            echo "🔄 개발 환경에서 운영 LLM + 임베딩 모두 사용"
            ;;
        --ssl)
            USE_SSL_PORT=true
            echo "🔐 SSL 포트 모드 활성화"
            ;;
        --ssl-verify)
            USE_SSL_PORT=true
            SSL_VERIFY_ENABLED=true
            INTERNAL_SSL_VERIFY=true
            EXTERNAL_SSL_VERIFY=true
            echo "🔐 SSL 포트 모드 활성화 (모든 SSL 검증 활성화)"
            ;;
        --internal-ssl-verify)
            INTERNAL_SSL_VERIFY=true
            echo "🔐 컨테이너 내부 SSL 검증 활성화"
            ;;
        --external-ssl-verify)
            EXTERNAL_SSL_VERIFY=true
            echo "🔐 외부 서버 연결 SSL 검증 활성화"
            ;;
        --ssl-verify-all)
            INTERNAL_SSL_VERIFY=true
            EXTERNAL_SSL_VERIFY=true
            echo "🔐 모든 SSL 검증 활성화 (내부 + 외부)"
            ;;
        --help|-h)
            echo ""
            echo "사용법:"
            echo "  ./podman-start-remote.sh <IP>                     - 원격 DB 서버 연결"
            echo "  ./podman-start-remote.sh --db-host <IP>           - 원격 DB 서버 연결"
            echo "  ./podman-start-remote.sh <IP> --rebuild           - 강제 재빌드"
            echo ""
            echo "옵션:"
            echo "  <IP>                  - 원격 DB 서버 IP 주소 (필수, 첫 번째 인자)"
            echo "  --db-host <IP>        - 원격 DB 서버 IP 주소 (필수, 명시적 옵션)"
            echo "  --rebuild             - 프론트엔드 강제 재빌드"
            echo "  --prod-llm            - 운영 LLM 사용"
            echo "  --prod-embedding      - 운영 임베딩 사용"
            echo "  --prod-all            - 운영 LLM + 임베딩 모두 사용"
            echo "  --ssl                 - SSL 포트 사용 (검증 비활성화)"
            echo "  --ssl-verify          - SSL 포트 사용 (검증 활성화)"
            echo ""
            echo "원격 DB 서버 요구사항:"
            echo "  - PostgreSQL: <IP>:5433"
            echo "  - Milvus: <IP>:19530"
            echo ""
            exit 0
            ;;
        *)
            # IP 주소 형식인지 확인 (xxx.xxx.xxx.xxx 또는 hostname)
            if [[ $arg =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]] || [[ $arg =~ ^[a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9]$ ]]; then
                if [ -z "$REMOTE_DB_HOST" ]; then
                    REMOTE_DB_HOST="$arg"
                    echo "🌐 원격 DB 서버: ${REMOTE_DB_HOST}"
                fi
            else
                echo "❌ 알 수 없는 옵션: $arg"
                echo "도움말: ./podman-start-remote.sh --help"
                exit 1
            fi
            ;;
    esac
done

# --db-host 필수 체크
if [ -z "$REMOTE_DB_HOST" ]; then
    echo ""
    echo "❌ 오류: --db-host 옵션이 필요합니다."
    echo ""
    echo "사용법:"
    echo "  ./podman-start-remote.sh --db-host <원격_DB_IP>"
    echo ""
    echo "예시:"
    echo "  ./podman-start-remote.sh --db-host 192.168.1.100"
    echo ""
    exit 1
fi

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 컨테이너 이름
OPENWEBUI_CONTAINER="sdc-open-webui"

# 볼륨 이름
OPENWEBUI_VOLUME="openwebui-data"

# HOST_IP 자동 감지 함수
# 192.168.122.178을 우선으로 사용 (메인 서버 IP)
# 11.93.33.10은 테스트 서버용 보조 IP
detect_host_ip() {
    # 192.168.122.178 우선 확인
    local main_ip=$(ip addr show 2>/dev/null | grep -oP 'inet \K192\.168\.122\.178' | head -n1)
    if [ -n "$main_ip" ]; then
        echo "$main_ip"
        return
    fi

    # 192.168.122.x 대역 확인
    local detected_ip=$(ip addr show 2>/dev/null | grep -oP 'inet \K192\.168\.122\.[0-9]+' | head -n1)
    if [ -n "$detected_ip" ]; then
        echo "$detected_ip"
        return
    fi

    # 그 외 IP 확인
    detected_ip=$(ip addr show 2>/dev/null | grep -oP 'inet \K[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | grep -v '127.0.0.1' | head -n1)
    echo "$detected_ip"
}

# 보조 IP 감지 함수
detect_secondary_ip() {
    local secondary_ip=$(ip addr show 2>/dev/null | grep "dynamic" | grep -oP 'inet \K[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -n1)
    echo "$secondary_ip"
}

# .env 파일 로드
if [ -f .env ]; then
    echo -e "${BLUE}📄 .env 파일 로드 중...${NC}"
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${RED}❌ .env 파일이 없습니다. .env.example을 복사하세요.${NC}"
    exit 1
fi

# HOST_IP 자동 감지
DETECTED_IP=$(detect_host_ip)
DETECTED_SECONDARY_IP=$(detect_secondary_ip)

if [ -n "$DETECTED_IP" ]; then
    echo -e "${BLUE}🔍 Local HOST_IP 감지: ${DETECTED_IP}${NC}"
    if [ -n "$DETECTED_SECONDARY_IP" ]; then
        echo -e "${BLUE}🔍 Secondary IP 감지: ${DETECTED_SECONDARY_IP}${NC}"
    fi
    export HOST_IP=$DETECTED_IP
    export HOST_IP_SECONDARY=$DETECTED_SECONDARY_IP
else
    echo -e "${YELLOW}⚠️  HOST_IP 자동 감지 실패, .env의 기존 값 사용${NC}"
fi

##############################################################################
# 원격 DB 연결 테스트
##############################################################################
echo ""
echo -e "${BLUE}🔍 원격 DB 서버 연결 테스트 중...${NC}"
echo ""

# PostgreSQL 연결 테스트
printf "  PostgreSQL (${REMOTE_DB_HOST}:5433): "
if nc -z -w5 ${REMOTE_DB_HOST} 5433 2>/dev/null; then
    echo -e "${GREEN}✅ 연결 가능${NC}"
else
    echo -e "${RED}❌ 연결 실패${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  원격 DB 서버에 연결할 수 없습니다.${NC}"
    echo "다음을 확인하세요:"
    echo "  1. 원격 DB 서버가 실행 중인지 확인"
    echo "  2. 방화벽에서 포트 5432이 개방되어 있는지 확인"
    echo "  3. 네트워크 연결 상태 확인"
    echo ""
    read -p "계속 진행하시겠습니까? (y/N): " continue_anyway
    if [[ ! "$continue_anyway" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Milvus 연결 테스트
printf "  Milvus (${REMOTE_DB_HOST}:19530): "
if nc -z -w5 ${REMOTE_DB_HOST} 19530 2>/dev/null; then
    echo -e "${GREEN}✅ 연결 가능${NC}"
else
    echo -e "${RED}❌ 연결 실패${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  원격 Milvus 서버에 연결할 수 없습니다.${NC}"
    echo "다음을 확인하세요:"
    echo "  1. 원격 Milvus 서버가 실행 중인지 확인"
    echo "  2. 방화벽에서 포트 19530이 개방되어 있는지 확인"
    echo "  3. 네트워크 연결 상태 확인"
    echo ""
    read -p "계속 진행하시겠습니까? (y/N): " continue_anyway
    if [[ ! "$continue_anyway" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

##############################################################################
# 환경별 설정 자동 적용
##############################################################################
echo ""
echo -e "${BLUE}🔧 환경 설정 확인 중...${NC}"
echo -e "${BLUE}   현재 환경: ${ENVIRONMENT}${NC}"

if [ "$ENVIRONMENT" = "development" ]; then
    echo -e "${YELLOW}🛠️  개발 환경 설정 적용 (한국어 최적화 서비스)${NC}"

    if [ "$USE_PROD_LLM" = true ]; then
        echo -e "${BLUE}   ⚙️  옵션: 운영 LLM 사용${NC}"
        sed -i "s|^OPENAI_API_BASE_URL=.*|OPENAI_API_BASE_URL=${OPENAI_API_BASE_URL_PRODUCTION}|" .env
        sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${OPENAI_API_KEY_PRODUCTION}|" .env
        sed -i "s|^DEFAULT_MODELS=.*|DEFAULT_MODELS=${DEFAULT_MODELS_PRODUCTION}|" .env
    else
        sed -i "s|^OPENAI_API_BASE_URL=.*|OPENAI_API_BASE_URL=${OPENAI_API_BASE_URL_DEVELOPMENT}|" .env
        sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${OPENAI_API_KEY_DEVELOPMENT}|" .env
        sed -i "s|^DEFAULT_MODELS=.*|DEFAULT_MODELS=${DEFAULT_MODELS_DEVELOPMENT}|" .env
    fi

    if [ "$USE_PROD_EMBEDDING" = true ]; then
        echo -e "${BLUE}   ⚙️  옵션: 운영 임베딩 사용${NC}"
        sed -i "s|^RAG_EMBEDDING_ENGINE=.*|RAG_EMBEDDING_ENGINE=${RAG_EMBEDDING_ENGINE_PRODUCTION}|" .env
        sed -i "s|^RAG_EMBEDDING_MODEL=.*|RAG_EMBEDDING_MODEL=${RAG_EMBEDDING_MODEL_PRODUCTION}|" .env
        sed -i "s|^RAG_OPENAI_API_BASE_URL=.*|RAG_OPENAI_API_BASE_URL=${RAG_OPENAI_API_BASE_URL_PRODUCTION}|" .env
        sed -i "s|^RAG_OPENAI_API_KEY=.*|RAG_OPENAI_API_KEY=${RAG_OPENAI_API_KEY_PRODUCTION}|" .env
    else
        sed -i "s|^RAG_EMBEDDING_ENGINE=.*|RAG_EMBEDDING_ENGINE=${RAG_EMBEDDING_ENGINE_DEVELOPMENT}|" .env
        sed -i "s|^RAG_EMBEDDING_MODEL=.*|RAG_EMBEDDING_MODEL=${RAG_EMBEDDING_MODEL_DEVELOPMENT}|" .env
        sed -i "s|^RAG_OPENAI_API_BASE_URL=.*|RAG_OPENAI_API_BASE_URL=${RAG_OPENAI_API_BASE_URL_DEVELOPMENT}|" .env
        sed -i "s|^RAG_OPENAI_API_KEY=.*|RAG_OPENAI_API_KEY=${RAG_OPENAI_API_KEY_DEVELOPMENT}|" .env
    fi

    sed -i "s|^CHUNK_SIZE=.*|CHUNK_SIZE=${CHUNK_SIZE_DEVELOPMENT}|" .env
    sed -i "s|^CHUNK_OVERLAP=.*|CHUNK_OVERLAP=${CHUNK_OVERLAP_DEVELOPMENT}|" .env

    export $(grep -v '^#' .env | xargs)

    echo -e "${GREEN}✅ 개발 환경 설정 완료${NC}"
else
    echo -e "${GREEN}✅ 운영/테스트 환경 설정${NC}"

    sed -i "s|^OPENAI_API_BASE_URL=.*|OPENAI_API_BASE_URL=${OPENAI_API_BASE_URL_PRODUCTION}|" .env
    sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${OPENAI_API_KEY_PRODUCTION}|" .env
    sed -i "s|^DEFAULT_MODELS=.*|DEFAULT_MODELS=${DEFAULT_MODELS_PRODUCTION}|" .env
    sed -i "s|^RAG_EMBEDDING_ENGINE=.*|RAG_EMBEDDING_ENGINE=${RAG_EMBEDDING_ENGINE_PRODUCTION}|" .env
    sed -i "s|^RAG_EMBEDDING_MODEL=.*|RAG_EMBEDDING_MODEL=${RAG_EMBEDDING_MODEL_PRODUCTION}|" .env
    sed -i "s|^RAG_OPENAI_API_BASE_URL=.*|RAG_OPENAI_API_BASE_URL=${RAG_OPENAI_API_BASE_URL_PRODUCTION}|" .env
    sed -i "s|^RAG_OPENAI_API_KEY=.*|RAG_OPENAI_API_KEY=${RAG_OPENAI_API_KEY_PRODUCTION}|" .env
    sed -i "s|^CHUNK_SIZE=.*|CHUNK_SIZE=${CHUNK_SIZE_PRODUCTION}|" .env
    sed -i "s|^CHUNK_OVERLAP=.*|CHUNK_OVERLAP=${CHUNK_OVERLAP_PRODUCTION}|" .env

    export $(grep -v '^#' .env | xargs)

    echo -e "${GREEN}✅ 운영/테스트 환경 설정 완료${NC}"
fi
echo ""

echo -e "${BLUE}📡 Podman 기본 네트워크(podman) 사용${NC}"
echo -e "${GREEN}🚀 Open WebUI (원격 DB 모드) 시작 중...${NC}"
echo ""

##############################################################################
# 포트 정리
##############################################################################
echo -e "${YELLOW}🔧 포트 정리: 기존 포트 사용 프로세스 종료 중...${NC}"
echo ""

# Open WebUI 관련 포트 목록 (PostgreSQL, Milvus 제외 - 원격 사용)
PORTS_TO_CLEAN="6380 5000 3000"

killed_count=0

for port in $PORTS_TO_CLEAN; do
    printf "  포트 %s: " "$port"

    if command -v fuser >/dev/null 2>&1; then
        if fuser "$port/tcp" >/dev/null 2>&1; then
            printf "🔄 사용 중 → "
            if fuser -k "$port/tcp" >/dev/null 2>&1; then
                printf "✅ 정리 완료\n"
                killed_count=$((killed_count + 1))
            else
                printf "❌ 정리 실패\n"
            fi
        else
            printf "✅ 사용 가능\n"
        fi
    else
        if lsof -i :"$port" >/dev/null 2>&1; then
            printf "🔄 사용 중 → "
            if lsof -ti :"$port" | xargs -r kill -9 2>/dev/null; then
                printf "✅ 정리 완료\n"
                killed_count=$((killed_count + 1))
            else
                printf "❌ 정리 실패\n"
            fi
        else
            printf "✅ 사용 가능\n"
        fi
    fi
done

echo ""
if [ $killed_count -gt 0 ]; then
    echo -e "${YELLOW}⚠️  총 $killed_count개 포트에서 프로세스를 종료했습니다.${NC}"
    sleep 2
else
    echo -e "${GREEN}✅ 모든 포트가 사용 가능한 상태입니다.${NC}"
fi
echo ""

##############################################################################
# 기존 컨테이너 정리
##############################################################################
echo -e "${YELLOW}🗑️  기존 컨테이너 정리 중...${NC}"

# PostgreSQL, Milvus는 제외 (원격 사용)
CONTAINERS_TO_CLEAN="sdc-open-webui sdc-redis-dev sdc-pipelines sdc-guardrails sdc-monitoring"

for container in $CONTAINERS_TO_CLEAN; do
    if podman ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
        printf "  컨테이너 %s: " "$container"
        if podman rm -f "$container" 2>/dev/null; then
            printf "✅ 제거 완료\n"
        else
            printf "❌ 제거 실패\n"
        fi
    fi
done

echo -e "${GREEN}✅ 컨테이너 정리 완료${NC}"
echo ""

##############################################################################
# 1. Redis 캐시 서비스 시작 (로컬)
##############################################################################
echo -e "${YELLOW}🔄 Redis 캐시 서비스 시작 중 (로컬)...${NC}"

if ! podman volume exists sdc-redis-data 2>/dev/null; then
    echo -e "${BLUE}📦 Redis 볼륨 생성 중...${NC}"
    podman volume create sdc-redis-data >/dev/null 2>&1
fi

# [2026-01-23] 네트워크 단순화: podman 네트워크만 사용
# dify-network는 별도로 생성하지 않음 (dify-manager.sh에서 처리)

podman run -d \
    --name sdc-redis-dev \
    --replace \
    --security-opt label=disable \
    --network podman \
    -v sdc-redis-data:/data \
    -p 0.0.0.0:6380:6379 \
    --health-cmd "redis-cli ping || exit 1" \
    --health-interval 10s \
    --health-timeout 3s \
    --health-retries 3 \
    --restart unless-stopped \
    docker.io/redis:7-alpine \
    redis-server --appendonly yes

echo -e "${GREEN}✅ Redis 컨테이너 시작됨 (포트: 6380)${NC}"
echo "   컨테이너명: sdc-redis-dev"
echo "   네트워크: podman"
echo ""

##############################################################################
# 2. Pipelines 컨테이너 시작 (podman 네트워크)
##############################################################################
echo -e "${YELLOW}🔄 Pipelines 컨테이너 시작 중...${NC}"

podman run -d \
    --name sdc-pipelines \
    --replace \
    --security-opt label=disable \
    --network podman \
    -p 0.0.0.0:9099:9099 \
    -v ${SCRIPT_DIR}/pipelines:/app/pipelines:z \
    -e PIPELINES_DIR=/app/pipelines \
    -e PIPELINES_API_KEY="0p3n-w3bu!" \
    --restart unless-stopped \
    ghcr.io/open-webui/pipelines:main

echo -e "${GREEN}✅ Pipelines 컨테이너 시작됨 (포트: 9099)${NC}"
echo "   컨테이너명: sdc-pipelines"
echo "   파이프라인 디렉토리: ${SCRIPT_DIR}/pipelines"
echo "   네트워크: podman"
echo ""

##############################################################################
# 3. Guardrails 컨테이너 시작 (podman 네트워크)
##############################################################################
# ----- 1227 guardrails 볼륨 마운트 추가 시작 -----
# 📌 볼륨 마운트 설명:
#   - 로컬: ${SCRIPT_DIR}/services/arthur-guardrails
#   - 컨테이너: /app
#   - 효과: 로컬 소스 코드 수정 시 재빌드 없이 컨테이너 재시작만으로 반영
#   - 수정 파일: arthur_guardrails_service.py, database.py 등
#   - 재시작 명령: podman restart sdc-guardrails
# ----- 1227 guardrails 볼륨 마운트 추가 종료 -----
echo -e "${YELLOW}🛡️  Guardrails 컨테이너 시작 중...${NC}"

# 호스트 포트: 13010, 내부 포트: 8001
podman run -d \
    --name sdc-guardrails \
    --replace \
    --security-opt label=disable \
    --network podman \
    -p 0.0.0.0:13010:8001 \
    -v ${SCRIPT_DIR}/services/arthur-guardrails:/app:Z \
    -w /app \
    -e HOST_IP="${REMOTE_DB_HOST}" \
    -e DB_HOST="${REMOTE_DB_HOST}" \
    -e DB_PORT="5433" \
    -e DB_NAME="guardrails_db" \
    -e DB_USER="sdc_dev_user" \
    -e DB_PASSWORD="sdc_dev_pass_2025" \
    -e DATABASE_URL="postgresql+asyncpg://sdc_dev_user:sdc_dev_pass_2025@${REMOTE_DB_HOST}:5433/guardrails_db" \
    --restart unless-stopped \
    localhost/sdc-arthur-guardrails:latest \
    python arthur_guardrails_service.py --port 8001 --host 0.0.0.0

echo -e "${GREEN}✅ Guardrails 컨테이너 시작됨 (포트: 13010 -> 8001)${NC}"
echo "   컨테이너명: sdc-guardrails"
echo "   볼륨 마운트: ${SCRIPT_DIR}/services/arthur-guardrails -> /app (재빌드 불필요)"
echo "   네트워크: podman"
echo ""

##############################################################################
# 4. Guardrails 데이터베이스 초기화 (테이블이 없을 경우에만)
##############################################################################
echo -e "${YELLOW}🛡️  Guardrails 데이터베이스 초기화 확인 중...${NC}"

GUARDRAIL_INIT_SCRIPT="${SCRIPT_DIR}/scripts/sdc-guardrail-init.sh"

if [ -f "${GUARDRAIL_INIT_SCRIPT}" ]; then
    chmod +x "${GUARDRAIL_INIT_SCRIPT}"
    # 테이블이 없을 경우에만 생성 (--force-init 옵션 없이 실행)
    "${GUARDRAIL_INIT_SCRIPT}" --db-host "${REMOTE_DB_HOST}" --db-port 5433 || {
        echo -e "${RED}❌ Guardrails 초기화 스크립트 실행 실패${NC}"
        echo -e "${YELLOW}⚠️  계속 진행합니다...${NC}"
    }
else
    echo -e "${YELLOW}⚠️  Guardrails 초기화 스크립트가 없습니다: ${GUARDRAIL_INIT_SCRIPT}${NC}"
fi
echo ""

##############################################################################
# 5. Monitoring 컨테이너 시작
# -----1222 대시보드 수정 시작 ------
# -----1222 대시보드 수정 종료 ------
##############################################################################
# ----- 1225 monitoring-backend 볼륨 마운트 주석 추가 시작 -----
# 📌 볼륨 마운트 설명:
#   - 로컬: ${SCRIPT_DIR}/services/monitoring-backend
#   - 컨테이너: /app
#   - 효과: 로컬 소스 코드 수정 시 재빌드 없이 컨테이너 재시작만으로 반영
#   - 수정 파일: main.py, queries.py 등
#   - 재시작 명령: podman restart sdc-monitoring
# ----- 1225 monitoring-backend 볼륨 마운트 주석 추가 종료 -----
echo -e "${YELLOW}📊 Monitoring 컨테이너 시작 중...${NC}"

podman run -d \
    --name sdc-monitoring \
    --replace \
    --security-opt label=disable \
    --network host \
    -v ${SCRIPT_DIR}/services/monitoring-backend:/app:Z \
    -w /app \
    -e CORS_ORIGINS="http://${HOST_IP}:3000,http://localhost:3000,http://${HOST_IP_SECONDARY}:3000" \
    -e DB_HOST="${REMOTE_DB_HOST}" \
    -e DB_PORT="5433" \
    -e DB_USER="sdc_dev_user" \
    -e DB_PASSWORD="sdc_dev_pass_2025" \
    -e DB_NAME="sdc_dev" \
    --restart unless-stopped \
    localhost/monitoring-backend:1.0 \
    python main.py

echo -e "${GREEN}✅ Monitoring 컨테이너 시작됨 (포트: 3001)${NC}"
echo "   컨테이너명: sdc-monitoring"
echo "   볼륨 마운트: ${SCRIPT_DIR}/services/monitoring-backend -> /app (재빌드 불필요)"
echo ""

##############################################################################
# 6. Open WebUI 컨테이너 준비
##############################################################################
echo -e "${YELLOW}🌐 Open WebUI 준비 중 (원격 DB 연결)...${NC}"

FIXED_IMAGE="localhost/open-webui:fixed-db"
OFFICIAL_IMAGE="ghcr.io/open-webui/open-webui:main"
OPENWEBUI_IMAGE=""

# 수정된 이미지 우선 사용 (원격 DB 연결 버그 수정)
if podman image exists ${FIXED_IMAGE} 2>/dev/null; then
    echo -e "${GREEN}✅ 수정된 이미지 사용: ${FIXED_IMAGE}${NC}"
    echo -e "${BLUE}   (원격 DB 연결 버그 수정 버전)${NC}"
    OPENWEBUI_IMAGE=${FIXED_IMAGE}
elif podman image exists ${OFFICIAL_IMAGE} 2>/dev/null; then
    echo -e "${GREEN}✅ 공식 이미지 존재: ${OFFICIAL_IMAGE}${NC}"
    OPENWEBUI_IMAGE=${OFFICIAL_IMAGE}
elif podman image exists localhost/open-webui:latest 2>/dev/null; then
    echo -e "${GREEN}✅ 로컬 이미지 존재: localhost/open-webui:latest${NC}"
    OPENWEBUI_IMAGE="localhost/open-webui:latest"
else
    echo -e "${RED}❌ Open WebUI 이미지가 없습니다.${NC}"
    exit 1
fi

# 프론트엔드 빌드 확인
if [ ! -d "$(pwd)/build" ] || [ "$FORCE_REBUILD" = true ]; then
    if [ "$FORCE_REBUILD" = true ]; then
        echo -e "${YELLOW}🔨 프론트엔드 강제 재빌드 중...${NC}"
    else
        echo -e "${YELLOW}📦 프론트엔드 빌드 폴더가 없습니다. 빌드 중...${NC}"
    fi

    if [ ! -d "node_modules" ]; then
        echo -e "${BLUE}📥 npm 패키지 설치 중...${NC}"
        npm install
    fi

    npm run build
    echo -e "${GREEN}✅ 프론트엔드 빌드 완료${NC}"
else
    echo -e "${GREEN}✅ 프론트엔드 빌드 존재 (build/)${NC}"
fi

echo ""
echo -e "${BLUE}📋 실행 방식: 공식 이미지 + 로컬 빌드 마운트 + 원격 DB 연결${NC}"
echo -e "${BLUE}   이미지: ${OPENWEBUI_IMAGE}${NC}"
echo -e "${BLUE}   원격 PostgreSQL: ${REMOTE_DB_HOST}:5433${NC}"
echo -e "${BLUE}   원격 Milvus: ${REMOTE_DB_HOST}:19530${NC}"
echo ""

# 포트 매핑 결정
OPENWEBUI_PORT=${OPENWEBUI_PORT:-3000}

if [ "$USE_SSL_PORT" = true ]; then
    PORT_MAPPING="${OPENWEBUI_PORT}:8080"
    echo -e "${BLUE}🔐 SSL 포트 매핑: ${OPENWEBUI_PORT}:8080 (HTTPS)${NC}"
else
    PORT_MAPPING="${OPENWEBUI_PORT}:8080"
    echo -e "${BLUE}🌐 표준 포트 매핑: ${OPENWEBUI_PORT}:8080 (HTTP)${NC}"
fi

# SSL 검증 설정
echo ""
echo -e "${BLUE}🔐 SSL 검증 설정:${NC}"

if [ "$INTERNAL_SSL_VERIFY" = true ]; then
    echo -e "${GREEN}   ✅ 컨테이너 내부 SSL 검증: 활성화${NC}"
    INTERNAL_SSL_ENV=""
else
    echo -e "${YELLOW}   ⚠️  컨테이너 내부 SSL 검증: 비활성화${NC}"
    INTERNAL_SSL_ENV="-e NODE_TLS_REJECT_UNAUTHORIZED=0"
fi

if [ "$EXTERNAL_SSL_VERIFY" = true ]; then
    echo -e "${GREEN}   ✅ 외부 서버 연결 SSL 검증: 활성화${NC}"
    EXTERNAL_SSL_ENV=""
else
    echo -e "${YELLOW}   ⚠️  외부 서버 연결 SSL 검증: 비활성화${NC}"
    EXTERNAL_SSL_ENV="-e PYTHONHTTPSVERIFY=0 -e CURL_CA_BUNDLE= -e REQUESTS_CA_BUNDLE= -e SSL_CERT_FILE= -e PYTHONWARNINGS=ignore:Unverified"
fi

SSL_ENV_VARS="${INTERNAL_SSL_ENV} ${EXTERNAL_SSL_ENV}"

if [ "$INTERNAL_SSL_VERIFY" = true ] || [ "$EXTERNAL_SSL_VERIFY" = true ]; then
    if [ -d "./certs" ]; then
        CERT_MOUNT="-v $(pwd)/certs:/app/certs:Z"
        echo -e "${BLUE}   📁 인증서 디렉토리 마운트: ./certs${NC}"
    else
        CERT_MOUNT=""
        echo -e "${YELLOW}   ⚠️  ./certs 디렉토리가 없습니다.${NC}"
    fi
else
    CERT_MOUNT=""
fi
echo ""

# Open WebUI 컨테이너 실행 (원격 DB 연결)
# [2026.01.19] --network=host로 변경하여 실제 클라이언트 IP 획득 가능
# [2026.01.19] PORT=${OPENWEBUI_PORT} 추가하여 기존 포트 유지 (기본값 3000)
# [2026.01.19] PIPELINES_URLS: host.docker.internal → localhost 변경
# ----- [2026-02-02] 보안 수정: X-Forwarded-For 변조 방지 -----
# 문제: 원본 이미지의 /app/backend/start.sh에 --forwarded-allow-ips '*' 하드코딩
# 해결: 보안 강화된 start_secure.sh를 /app/backend/start.sh에 마운트하여 덮어쓰기
# 효과: FORWARDED_ALLOW_IPS 환경변수 값에 따라 조건부로 프록시 헤더 처리
# ----- [2026-02-02] 보안 수정 시작 -----
podman run -d \
    --name ${OPENWEBUI_CONTAINER} \
    --network=host \
    -e PORT=${OPENWEBUI_PORT} \
    -e HOST_IP=${HOST_IP:-localhost} \
    -e DATABASE_URL=postgresql://sdc_dev_user:sdc_dev_pass_2025@${REMOTE_DB_HOST}:5433/sdc_dev \
    -e OPENAI_API_BASE_URL=${OPENAI_API_BASE_URL} \
    -e OPENAI_API_BASE_URLS="${OPENAI_API_BASE_URL};http://${HOST_IP}:9099" \
    -e OPENAI_API_KEY=${OPENAI_API_KEY} \
    -e OPENAI_API_KEYS="${OPENAI_API_KEY};0p3n-w3bu!" \
    -e DEFAULT_MODELS=${DEFAULT_MODELS} \
    -e RAG_EMBEDDING_ENGINE=${RAG_EMBEDDING_ENGINE} \
    -e RAG_EMBEDDING_MODEL=${RAG_EMBEDDING_MODEL} \
    -e RAG_OPENAI_API_BASE_URL=${RAG_OPENAI_API_BASE_URL} \
    -e RAG_OPENAI_API_KEY=${RAG_OPENAI_API_KEY} \
    -e SENTENCE_TRANSFORMERS_HOME=${SENTENCE_TRANSFORMERS_HOME} \
    -e HF_HOME=${HF_HOME} \
    -e VECTOR_DB=${VECTOR_DB} \
    -e MILVUS_URI=http://${REMOTE_DB_HOST}:19530 \
    -e OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-''} \
    -e CORS_ALLOW_ORIGIN=${CORS_ALLOW_ORIGIN} \
    -e FORWARDED_ALLOW_IPS=${FORWARDED_ALLOW_IPS} \
    -e SCARF_NO_ANALYTICS=${SCARF_NO_ANALYTICS} \
    -e DO_NOT_TRACK=${DO_NOT_TRACK} \
    -e ANONYMIZED_TELEMETRY=${ANONYMIZED_TELEMETRY} \
    -e WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY} \
    -e ENABLE_RAG_WEB_SEARCH=${ENABLE_RAG_WEB_SEARCH} \
    -e ENABLE_RAG_LOCAL_WEB_FETCH=${ENABLE_RAG_LOCAL_WEB_FETCH} \
    -e ENABLE_IMAGE_GENERATION=${ENABLE_IMAGE_GENERATION} \
    -e ENABLE_COMMUNITY_SHARING=${ENABLE_COMMUNITY_SHARING} \
    -e CHROMA_TELEMETRY=${CHROMA_TELEMETRY} \
    -e CHROMA_CLIENT_DISABLED=${CHROMA_CLIENT_DISABLED} \
    -e PIPELINES_URLS="http://localhost:9099" \
    -e PIPELINES_API_KEY="0p3n-w3bu!" \
    ${SSL_ENV_VARS} \
    -v ${OPENWEBUI_VOLUME}:/app/backend/data \
    ${CERT_MOUNT} \
    -v $(pwd)/build:/app/build:Z \
    -v $(pwd)/embeddings:/app/embeddings:Z \
    -v $(pwd)/src:/app/src:Z \
    -v $(pwd)/static:/app/static:Z \
    -v $(pwd)/package.json:/app/package.json:Z \
    -v $(pwd)/svelte.config.js:/app/svelte.config.js:Z \
    -v $(pwd)/vite.config.ts:/app/vite.config.ts:Z \
    -v $(pwd)/tsconfig.json:/app/tsconfig.json:Z \
    -v $(pwd)/tailwind.config.js:/app/tailwind.config.js:Z \
    -v $(pwd)/postcss.config.js:/app/postcss.config.js:Z \
    -v $(pwd)/backend/open_webui/routers/configs.py:/app/backend/open_webui/routers/configs.py:Z \
    -v $(pwd)/backend/open_webui/routers/auths.py:/app/backend/open_webui/routers/auths.py:Z \
    -v $(pwd)/backend/open_webui/routers/podman.py:/app/backend/open_webui/routers/podman.py:Z \
    -v $(pwd)/backend/open_webui/main.py:/app/backend/open_webui/main.py:Z \
    -v $(pwd)/backend/open_webui/models/users.py:/app/backend/open_webui/models/users.py:Z \
    -v $(pwd)/backend/open_webui/models/user_sessions.py:/app/backend/open_webui/models/user_sessions.py:Z \
    -v $(pwd)/backend/open_webui/models/announcements.py:/app/backend/open_webui/models/announcements.py:Z \
    -v $(pwd)/backend/open_webui/utils/auth.py:/app/backend/open_webui/utils/auth.py:Z \
    -v $(pwd)/backend/start_secure.sh:/app/backend/start.sh:Z \
    -v /run/user/1000/podman/podman.sock:/run/podman/podman.sock \
    --security-opt label=disable \
    -e PODMAN_SOCKET=/run/podman/podman.sock \
    -v /home/chatpro/open-webui-main:/scripts:ro \
    --restart unless-stopped \
    ${OPENWEBUI_IMAGE} \
    bash start.sh
# ----- [2026-02-02] 보안 수정 완료 -----

echo -e "${GREEN}✅ Open WebUI 컨테이너 시작됨 (포트: 3000)${NC}"
echo "   컨테이너명: ${OPENWEBUI_CONTAINER}"
echo ""

##############################################################################
# 상태 확인
##############################################################################
echo ""
echo -e "${GREEN}✨ 모든 컨테이너 시작 완료! (원격 DB 모드)${NC}"
echo ""
echo "=================================="
echo "🌐 Open WebUI 접속 주소:"
echo "   - http://localhost:3000"
echo "   - http://127.0.0.1:3000"
echo "   - http://${HOST_IP}:3000 (Primary)"
if [ -n "$HOST_IP_SECONDARY" ]; then
    echo "   - http://${HOST_IP_SECONDARY}:3000 (Secondary)"
fi
echo ""
echo "원격 서비스 연결:"
echo "   🗄️  PostgreSQL: ${REMOTE_DB_HOST}:5433"
echo "   🧠 Milvus: ${REMOTE_DB_HOST}:19530"
echo ""
echo "로컬 서비스 포트:"
echo "   🔄 Redis: localhost:6380"
echo "   🔄 Pipelines: http://localhost:9099"
echo "   🛡️  Guardrails: http://localhost:13010"
echo "   📊 Monitoring: http://localhost:3001"
echo "=================================="
echo ""
echo "환경 정보:"
echo "  📍 Local IP: ${HOST_IP}"
echo "  🌐 Remote DB Host: ${REMOTE_DB_HOST}"
echo "  🔧 환경 유형: ${ENVIRONMENT}"
echo ""
echo "컨테이너 상태 확인:"
podman ps --filter "name=sdc"
echo ""

##############################################################################
# 컨테이너 상태 점검 및 자동 재시작
# ----- [2026-02-07] exited 상태 컨테이너 자동 재시작 추가 -----
##############################################################################
echo ""
echo -e "${YELLOW}🔍 컨테이너 상태 점검 중... (10초 대기)${NC}"
sleep 10

RESTART_TARGETS="sdc-open-webui sdc-redis-dev sdc-pipelines sdc-guardrails sdc-monitoring"
MAX_RETRY=3        # 최대 재시도 횟수
RETRY_WAIT=5       # 재시도 간 대기 시간(초)

for retry in $(seq 1 $MAX_RETRY); do
    exited_containers=""

    for container in $RESTART_TARGETS; do
        state=$(podman inspect --format '{{.State.Status}}' "$container" 2>/dev/null)
        if [ "$state" = "exited" ] || [ "$state" = "dead" ]; then
            exited_containers="$exited_containers $container"
        fi
    done

    # 중지된 컨테이너가 없으면 점검 완료
    if [ -z "$exited_containers" ]; then
        echo -e "${GREEN}✅ 모든 컨테이너 정상 실행 중${NC}"
        break
    fi

    # 중지된 컨테이너 재시작
    echo -e "${YELLOW}⚠️  [${retry}/${MAX_RETRY}] 중지된 컨테이너 감지 → 자동 재시작${NC}"
    for container in $exited_containers; do
        printf "  🔄 %-20s → " "$container"
        if podman start "$container" >/dev/null 2>&1; then
            printf "${GREEN}재시작 완료${NC}\n"
        else
            printf "${RED}재시작 실패${NC}\n"
        fi
    done

    # 마지막 시도가 아니면 대기 후 재확인
    if [ $retry -lt $MAX_RETRY ]; then
        echo -e "${BLUE}   ${RETRY_WAIT}초 후 재확인...${NC}"
        sleep $RETRY_WAIT
    fi
done

# 최종 상태 출력
echo ""
echo -e "${BLUE}📋 최종 컨테이너 상태:${NC}"
for container in $RESTART_TARGETS; do
    state=$(podman inspect --format '{{.State.Status}}' "$container" 2>/dev/null || echo "not found")
    if [ "$state" = "running" ]; then
        printf "  ✅ %-20s %s\n" "$container" "$state"
    else
        printf "  ❌ %-20s %s\n" "$container" "$state"
    fi
done
echo ""
# ----- [2026-02-07] exited 상태 컨테이너 자동 재시작 종료 -----

##############################################################################
# Dify 컨테이너 시작 옵션
# [2026-01-23] 추가: SDC 컨테이너 시작 후 Dify 컨테이너도 함께 시작할지 선택
##############################################################################
echo ""
echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}  Dify 컨테이너 시작 옵션${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""
echo "Dify (AI Workflow Builder) 컨테이너를 함께 시작하시겠습니까?"
echo "  - dify-sandbox"
echo "  - dify-plugin-daemon"
echo "  - dify-api"
echo "  - dify-worker"
echo "  - dify-web (포트: 9008)"
echo ""
read -p "Dify 컨테이너 시작? (y/N): " START_DIFY

if [[ "$START_DIFY" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}🚀 Dify 컨테이너 시작 중...${NC}"
    echo ""

    # dify-manager.sh 실행
    DIFY_MANAGER_PATH="${SCRIPT_DIR}/dify_add_con/dify-manager.sh"

    if [ -f "${DIFY_MANAGER_PATH}" ]; then
        cd "${SCRIPT_DIR}/dify_add_con" && ./dify-manager.sh start

        echo ""
        echo -e "${GREEN}✅ Dify 컨테이너 시작 완료!${NC}"
        echo ""
        echo "=================================="
        echo "🌐 전체 서비스 접속 정보:"
        echo "   - Open WebUI: http://${HOST_IP}:3000"
        echo "   - Dify:       http://${HOST_IP}:9008"
        echo "   - Pipelines:  http://${HOST_IP}:9099"
        echo "   - Guardrails: http://${HOST_IP}:13010"
        echo "   - Monitoring: http://${HOST_IP}:3001"
        echo "=================================="
    else
        echo -e "${RED}❌ dify-manager.sh를 찾을 수 없습니다: ${DIFY_MANAGER_PATH}${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}ℹ️  Dify 컨테이너 시작을 건너뜁니다.${NC}"
    echo "   나중에 시작하려면: cd dify_add_con && ./dify-manager.sh start"
    echo ""
    echo "로그 확인: podman logs -f ${OPENWEBUI_CONTAINER}"
fi
echo ""
