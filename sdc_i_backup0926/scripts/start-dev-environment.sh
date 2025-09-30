#!/bin/bash

# =============================================================================
# SDC 개발환경 관리 스크립트 (Development Environment Management Script)
# VSCode Web Server, PgAdmin 등 개발 도구 컨테이너 관리
# =============================================================================

set -e

# 설치 디렉토리 설정
INSTALL_DIR="${SDC_INSTALL_DIR:-/home/sdc}"
PROJECT_DIR="${SDC_PROJECT_DIR:-${INSTALL_DIR}}"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 로그 함수들
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# 개발 서비스 정보 (Redis는 기존 프로덕션 스크립트에서 관리)
declare -A DEV_SERVICES=(
    ["postgres-dev"]="postgres:16-alpine sdc-db-postgres-dev 5433:5432"
    ["vscode-dev"]="localhost/sdc-vscode-dev:latest sdc-ide-vscode-dev 8080:8080"
    ["pgadmin-dev"]="docker.io/dpage/pgadmin4:latest sdc-admin-pgadmin-dev 5050:80"
)

# 네트워크 생성
create_dev_network() {
    log_step "개발환경 네트워크 생성 중..."
    if ! podman network exists sdc-dev-network 2>/dev/null; then
        podman network create sdc-dev-network
        log_success "개발환경 네트워크 생성 완료"
    else
        log_info "개발환경 네트워크가 이미 존재합니다"
    fi
}

# PostgreSQL 개발 데이터베이스 시작 (별도 인스턴스)
start_postgres_dev() {
    log_step "PostgreSQL 개발 데이터베이스 시작 중... (포트: 5433)"

    # 기존 컨테이너 정리
    if podman ps -a --format "{{.Names}}" | grep -q "^sdc-db-postgres-dev$"; then
        log_info "기존 개발 PostgreSQL 컨테이너 제거 중..."
        podman stop sdc-db-postgres-dev 2>/dev/null || true
        podman rm -f sdc-db-postgres-dev
    fi

    # 개발용 별도 볼륨 생성 (프로덕션과 완전 분리)
    if ! podman volume exists sdc-postgres-dev-data 2>/dev/null; then
        log_info "개발용 PostgreSQL 데이터 볼륨 생성 중..."
        podman volume create sdc-postgres-dev-data
    fi

    podman run -d \
        --name sdc-db-postgres-dev \
        --network sdc-dev-network \
        -p 5433:5432 \
        -e POSTGRES_DB=sdc_dev \
        -e POSTGRES_USER=sdc_dev_user \
        -e POSTGRES_PASSWORD=sdc_dev_pass_2025 \
        -e POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale=C" \
        -v sdc-postgres-dev-data:/var/lib/postgresql/data \
        --restart unless-stopped \
        postgres:16-alpine

    log_success "PostgreSQL 개발 데이터베이스 시작 완료 (포트: 5433)"
    log_info "개발용 DB는 프로덕션과 완전히 분리된 별도 인스턴스입니다"
}

# Redis는 기존 프로덕션 스크립트(shart.sh)에서 관리

# VSCode 서버 빌드 및 시작
start_vscode_dev() {
    log_step "VSCode 웹 서버 시작 중... (포트: 8080)"

    # VSCode 이미지가 없으면 빌드
    if ! podman images | grep -q "sdc-vscode-dev"; then
        log_info "VSCode 개발 이미지 빌드 중..."
        podman build -t sdc-vscode-dev:latest -f dev-environment/Containerfile.vscode-server dev-environment/
    fi

    # 기존 컨테이너 정리
    if podman ps -a --format "{{.Names}}" | grep -q "^sdc-ide-vscode-dev$"; then
        podman rm -f sdc-ide-vscode-dev
    fi

    podman run -d \
        --name sdc-ide-vscode-dev \
        --network sdc-dev-network \
        -p 8080:8080 \
        -v $(pwd):/home/chatpro/sdc_i \
        -v vscode-extensions:/home/chatpro/.vscode-server/extensions \
        -v vscode-data:/home/chatpro/.vscode-server/data \
        -e NODE_ENV=development \
        -e PYTHONPATH=/home/chatpro/sdc_i/backend \
        -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
        sdc-vscode-dev:latest

    log_success "VSCode 웹 서버 시작 완료 (포트: 8080)"
}

# PgAdmin 시작
start_pgadmin_dev() {
    log_step "PgAdmin 데이터베이스 관리 도구 시작 중... (포트: 5050)"

    # 기존 컨테이너 정리
    if podman ps -a --format "{{.Names}}" | grep -q "^sdc-admin-pgadmin-dev$"; then
        podman rm -f sdc-admin-pgadmin-dev
    fi

    podman run -d \
        --name sdc-admin-pgadmin-dev \
        --network sdc-dev-network \
        -p 5050:80 \
        -e PGADMIN_DEFAULT_EMAIL=admin@sdc.com \
        -e PGADMIN_DEFAULT_PASSWORD=sdc_dev_2025 \
        -v pgadmin-dev-data:/var/lib/pgadmin \
        docker.io/dpage/pgadmin4:latest

    log_success "PgAdmin 시작 완료 (포트: 5050)"
}

# Redis Insight는 제거 (Redis는 프로덕션 스크립트에서 관리)

# 모든 개발 서비스 시작 (Redis는 프로덕션 스크립트에서 별도 관리)
start_all_dev_services() {
    log_step "=== 개발 도구 서비스 시작 ==="

    create_dev_network
    start_postgres_dev
    start_vscode_dev
    start_pgadmin_dev

    log_success "모든 개발 도구 서비스 시작 완료"
    log_info "참고: Redis 캐시는 프로덕션 스크립트(shart.sh)에서 관리됩니다"
}

# 개발 서비스 중지 (Redis는 제외)
stop_all_dev_services() {
    log_step "=== 개발 도구 서비스 중지 ==="

    for container in sdc-db-postgres-dev sdc-ide-vscode-dev sdc-admin-pgadmin-dev; do
        if podman ps --format "{{.Names}}" | grep -q "^${container}$"; then
            log_info "${container} 중지 중..."
            podman stop ${container}
        fi
    done

    log_info "개발용 PostgreSQL 데이터는 별도 볼륨에 보존됩니다"

    log_success "개발 도구 서비스 중지 완료"
    log_info "참고: Redis 캐시는 프로덕션 스크립트(shart.sh)에서 관리됩니다"
}

# 개발 서비스 완전 제거
remove_all_dev_services() {
    log_step "=== 개발 도구 서비스 완전 제거 ==="
    log_warning "⚠️  모든 개발 컨테이너가 제거됩니다! (데이터 볼륨은 보존)"

    for container in sdc-db-postgres-dev sdc-ide-vscode-dev sdc-admin-pgadmin-dev; do
        if podman ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
            log_info "${container} 중지 및 제거 중..."
            podman stop ${container} &>/dev/null || true
            podman rm ${container} &>/dev/null || true
        fi
    done

    log_info "개발용 PostgreSQL 데이터는 별도 볼륨에 보존됩니다"
    log_info "개발용 VSCode 확장프로그램은 볼륨에 보존됩니다"

    log_success "개발 도구 서비스 제거 완료"
    log_info "참고: Redis 캐시는 프로덕션 스크립트(shart.sh)에서 관리됩니다"
}

# 개발 서비스 상태 확인
check_dev_status() {
    log_step "=== 개발 서비스 상태 확인 ==="

    echo "서비스                 컨테이너명 포트   상태          설명                        "
    echo "------------------------- --------------- -------- --------------- ------------------------------"

    # PostgreSQL Dev
    if podman ps --format "{{.Names}}" | grep -q "^sdc-db-postgres-dev$"; then
        echo "postgres-dev              sdc-db-postgres-dev    5433     \033[0;32m실행중\033[0m PostgreSQL 개발 데이터베이스       "
    else
        echo "postgres-dev              sdc-db-postgres-dev    5433     \033[1;33m중지됨\033[0m PostgreSQL 개발 데이터베이스       "
    fi

    # Redis는 프로덕션 스크립트에서 관리

    # VSCode Dev
    if podman ps --format "{{.Names}}" | grep -q "^sdc-ide-vscode-dev$"; then
        echo "vscode-dev                sdc-ide-vscode-dev      8080     \033[0;32m실행중\033[0m VSCode 웹 개발 환경         "
    else
        echo "vscode-dev                sdc-ide-vscode-dev      8080     \033[1;33m중지됨\033[0m VSCode 웹 개발 환경         "
    fi

    # PgAdmin Dev
    if podman ps --format "{{.Names}}" | grep -q "^sdc-admin-pgadmin-dev$"; then
        echo "pgadmin-dev               sdc-admin-pgadmin-dev     5050     \033[0;32m실행중\033[0m PgAdmin 데이터베이스 관리    "
    else
        echo "pgadmin-dev               sdc-admin-pgadmin-dev     5050     \033[1;33m중지됨\033[0m PgAdmin 데이터베이스 관리    "
    fi

    echo ""
    log_info "개발 환경 접속 URL:"
    echo "  • VSCode 웹 IDE:        http://localhost:8080"
    echo "  • PgAdmin:             http://localhost:5050 (dev@sdc.local / sdc_dev_2025)"
    echo "  • PostgreSQL DB:       localhost:5433 (sdc_dev_user / sdc_dev_pass_2025)"
    echo ""
    log_info "프로덕션 서비스 (별도 스크립트 관리):"
    echo "  • Redis Cache:         localhost:6379 (shart.sh에서 관리)"
}

# 개발 서비스 헬스체크
health_check_dev() {
    log_step "=== 개발 서비스 건강 상태 체크 ==="

    services_count=0
    healthy_count=0

    # VSCode Dev Health Check
    services_count=$((services_count + 1))
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 --connect-timeout 5 | grep -q "200\|302"; then
        echo "  VSCode 웹 서버 (포트 8080): ${GREEN}건강함${NC}"
        healthy_count=$((healthy_count + 1))
    else
        echo "  VSCode 웹 서버 (포트 8080): ${RED}응답 없음${NC}"
    fi

    # PgAdmin Health Check
    services_count=$((services_count + 1))
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:5050 --connect-timeout 5 | grep -q "200\|302"; then
        echo "  PgAdmin (포트 5050): ${GREEN}건강함${NC}"
        healthy_count=$((healthy_count + 1))
    else
        echo "  PgAdmin (포트 5050): ${RED}응답 없음${NC}"
    fi

    # Redis Insight는 제거됨 (사용하지 않음)

    echo ""
    log_info "건강한 개발 서비스: ${healthy_count}/${services_count}"

    if [ $healthy_count -eq $services_count ]; then
        log_success "모든 개발 서비스가 정상 작동 중!"
    else
        log_warning "일부 개발 서비스에 문제가 있을 수 있습니다."
    fi
}

# 도움말
show_help() {
    echo "SDC 개발환경 관리 스크립트"
    echo ""
    echo "사용법: $0 [COMMAND]"
    echo ""
    echo "명령어:"
    echo "  start, up           모든 개발 서비스 시작"
    echo "  stop, down          모든 개발 서비스 중지"
    echo "  remove, rm          모든 개발 서비스 완전 제거"
    echo "  status, ps          개발 서비스 상태 확인"
    echo "  health              개발 서비스 헬스체크"
    echo "  vscode              VSCode 웹 서버만 시작"
    echo "  pgadmin             PgAdmin만 시작"
    echo "  help                이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 start           # 모든 개발 서비스 시작"
    echo "  $0 health          # 개발 서비스 헬스체크"
    echo "  $0 vscode          # VSCode만 시작"
}

# 메인 실행 로직
case "${1:-help}" in
    "start"|"up")
        start_all_dev_services
        echo ""
        check_dev_status
        ;;
    "stop"|"down")
        stop_all_dev_services
        ;;
    "remove"|"rm")
        remove_all_dev_services
        ;;
    "status"|"ps")
        check_dev_status
        ;;
    "health")
        health_check_dev
        ;;
    "vscode")
        create_dev_network
        start_vscode_dev
        ;;
    "pgadmin")
        create_dev_network
        start_postgres_dev
        start_pgadmin_dev
        ;;
    "help"|*)
        show_help
        ;;
esac