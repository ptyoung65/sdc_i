#!/bin/bash

################################################################################
# Dify 전체 관리 스크립트 (개선 버전)
#
# 기능:
# - 원격 DB(PostgreSQL, Milvus) 연결 확인
# - 로컬/원격 서버 IP 지정 가능
# - 기존 컨테이너 자동 정리 및 포트 초기화
# - PostgreSQL 초기 테이블 생성
# - 초기 사용자 생성
# - 컨테이너 순차적 실행
#
# 사용법:
#   ./dify-manager.sh <COMMAND> [OPTIONS]
#
# 명령어:
#   install   - 전체 설치 (이미지 로드 + DB 초기화 + 컨테이너 시작)
#   start     - Dify 시작
#   stop      - Dify 중지
#   restart   - Dify 재시작
#   status    - 상태 확인
#   logs      - 로그 확인
#   clean     - 전체 삭제
#   init-db   - DB 초기화만 수행
################################################################################

set -e

# ============================================
# 색상 코드
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ============================================
# 로그 함수
# ============================================
log_header() {
    echo ""
    echo -e "${BOLD}${BLUE}========================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}========================================${NC}"
    echo ""
}

log_section() {
    echo ""
    echo -e "${CYAN}----------------------------------------${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}----------------------------------------${NC}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${MAGENTA}[STEP $1/$2]${NC} $3"
}

# ============================================
# 설정 파일 경로
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/.dify-config"

# ============================================
# 설정 로드 함수
# ============================================
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
        return 0
    fi
    return 1
}

# ============================================
# 설정 저장 함수
# ============================================
save_config() {
    cat > "$CONFIG_FILE" << EOF
# ============================================================
# Dify Manager 설정 파일
# ============================================================
# 이 파일의 설정값들을 수정하여 Dify 환경을 구성할 수 있습니다.
# 수정 후 ./dify-manager.sh 명령으로 적용하세요.
# 자동 생성됨: $(date)

# ------------------------------------------------------------
# 네트워크 설정
# ------------------------------------------------------------

# 원격 DB 서버 IP
# PostgreSQL과 Milvus가 실행 중인 서버의 IP 주소
REMOTE_DB_IP="$REMOTE_DB_IP"

# 웹 접근 IP (사용자가 브라우저에서 접속할 때 사용하는 IP)
# 예: http://$WEB_ACCESS_IP:$WEB_PORT 로 접속하는 경우
# 이 IP는 CORS 설정과 API URL 설정에 사용됩니다
WEB_ACCESS_IP="$WEB_ACCESS_IP"

# 웹 포트 (사용자가 브라우저에서 접속할 때 사용하는 포트)
WEB_PORT="$WEB_PORT"

# 로컬 서버 IP (레거시 설정, 현재는 사용되지 않음)
# 서버에 여러 IP가 있는 경우 내부 통신용으로 사용할 수 있습니다
# 대부분의 경우 WEB_ACCESS_IP와 동일한 값을 사용하면 됩니다
LOCAL_HOST_IP="$LOCAL_HOST_IP"

# ------------------------------------------------------------
# 데이터베이스 설정 (PostgreSQL)
# ------------------------------------------------------------

# PostgreSQL 포트 (원격 DB 서버의 PostgreSQL 포트)
DB_PORT="$DB_PORT"

# PostgreSQL 사용자명
DB_USERNAME="$DB_USERNAME"

# PostgreSQL 비밀번호
DB_PASSWORD="$DB_PASSWORD"

# PostgreSQL 데이터베이스 이름
DB_DATABASE="$DB_DATABASE"

# ------------------------------------------------------------
# 벡터 데이터베이스 설정 (Milvus)
# ------------------------------------------------------------

# Milvus 포트 (원격 DB 서버의 Milvus 포트)
MILVUS_PORT="$MILVUS_PORT"

# ------------------------------------------------------------
# Redis 설정 (로컬 서버)
# ------------------------------------------------------------

# Redis 포트
REDIS_PORT="$REDIS_PORT"

# Redis 비밀번호 (비밀번호가 없으면 빈 문자열)
REDIS_PASSWORD="$REDIS_PASSWORD"

# Redis 컨테이너 이름 (기존에 실행 중인 Redis 컨테이너 이름)
REDIS_CONTAINER_NAME="$REDIS_CONTAINER_NAME"

# ------------------------------------------------------------
# 컨테이너 및 네트워크 설정
# ------------------------------------------------------------

# Podman 네트워크 이름
NETWORK_NAME="$NETWORK_NAME"

# Dify 컨테이너 이름 접두사
# 예: dify-api, dify-worker, dify-web 등
CONTAINER_PREFIX="$CONTAINER_PREFIX"

# ------------------------------------------------------------
# 추가 옵션
# ------------------------------------------------------------

# Nginx 사용 여부 (yes 또는 no)
# no: 각 서비스를 개별 포트로 직접 접근
# yes: Nginx를 통해 리버스 프록시 구성
USE_NGINX="$USE_NGINX"
EOF
    chmod 600 "$CONFIG_FILE"
}

# ============================================
# 대화형 설정 함수
# ============================================
interactive_config() {
    log_header "Dify 설정"

    echo -e "${BOLD}필수 정보를 입력해주세요:${NC}"
    echo ""

    # 원격 DB 서버 IP 선택
    echo -e "${BOLD}원격 DB 서버 IP 선택 (PostgreSQL, Milvus, Redis):${NC}"
    echo "  1) 11.93.33.13"
    echo "  2) 11.93.32.31"
    echo "  3) 11.93.32.32"
    echo "  4) 직접 입력"
    echo ""
    read -p "선택 (1-4): " DB_CHOICE

    case $DB_CHOICE in
        1)
            REMOTE_DB_IP="11.93.33.13"
            ;;
        2)
            REMOTE_DB_IP="11.93.32.31"
            ;;
        3)
            REMOTE_DB_IP="11.93.32.32"
            ;;
        4)
            read -p "원격 DB 서버 IP 입력: " REMOTE_DB_IP
            while [ -z "$REMOTE_DB_IP" ]; do
                log_error "원격 DB 서버 IP는 필수입니다."
                read -p "원격 DB 서버 IP 입력: " REMOTE_DB_IP
            done
            ;;
        *)
            log_error "잘못된 선택입니다. 기본값 11.93.33.13을 사용합니다."
            REMOTE_DB_IP="11.93.33.13"
            ;;
    esac

    log_success "선택된 원격 DB 서버: $REMOTE_DB_IP"
    echo ""

    # 웹 접근 IP 설정 (자동 감지)
    echo -e "${BOLD}웹 접근 설정:${NC}"

    # 서버의 모든 IP 주소 감지
    local DETECTED_IP=$(hostname -I | awk '{print $1}')
    local ALL_IPS=$(hostname -I)

    echo "  이 서버의 사용 가능한 IP 주소: $ALL_IPS"
    echo ""

    # 자동 감지된 IP를 기본값으로 제시
    read -p "웹 접근 IP [기본값: $DETECTED_IP]: " WEB_ACCESS_IP
    WEB_ACCESS_IP=${WEB_ACCESS_IP:-$DETECTED_IP}
    log_success "웹 접근 IP: $WEB_ACCESS_IP"
    echo ""

    read -p "웹 포트 [기본값: 9008]: " WEB_PORT
    WEB_PORT=${WEB_PORT:-9008}
    log_success "웹 포트: $WEB_PORT"
    echo ""

    # 로컬 서버 IP (레거시 설정)
    LOCAL_HOST_IP="$WEB_ACCESS_IP"
    log_info "로컬 서버 IP: $LOCAL_HOST_IP (웹 접근 IP와 동일)"
    echo ""

    # PostgreSQL 설정
    echo ""
    echo -e "${BOLD}PostgreSQL 설정:${NC}"
    read -p "PostgreSQL 포트 [기본값: 5433]: " DB_PORT
    DB_PORT=${DB_PORT:-5433}

    read -p "PostgreSQL 사용자명 [기본값: sdc_dev_user]: " DB_USERNAME
    DB_USERNAME=${DB_USERNAME:-sdc_dev_user}

    read -sp "PostgreSQL 비밀번호 [기본값: sdc_dev_pass_2025]: " DB_PASSWORD
    echo ""
    DB_PASSWORD=${DB_PASSWORD:-sdc_dev_pass_2025}

    read -p "PostgreSQL 데이터베이스 [기본값: dify]: " DB_DATABASE
    DB_DATABASE=${DB_DATABASE:-dify}

    # Milvus 설정
    echo ""
    echo -e "${BOLD}Milvus 설정:${NC}"
    read -p "Milvus 포트 [기본값: 19530]: " MILVUS_PORT
    MILVUS_PORT=${MILVUS_PORT:-19530}

    # Redis 설정 (로컬 서버의 기존 컨테이너 사용)
    echo ""
    echo -e "${BOLD}Redis 설정:${NC}"
    echo "  ※ 로컬 서버의 기존 sdc-redis-dev 컨테이너를 사용합니다"
    read -p "Redis 포트 [기본값: 6379]: " REDIS_PORT
    REDIS_PORT=${REDIS_PORT:-6379}

    read -p "Redis 비밀번호 (없으면 Enter): " REDIS_PASSWORD
    REDIS_PASSWORD=${REDIS_PASSWORD:-""}

    # Redis 컨테이너 이름
    REDIS_CONTAINER_NAME="sdc-redis-dev"

    # 네트워크 설정
    # [2026-01-23] 네트워크 단순화: podman 네트워크만 사용
    echo ""
    echo -e "${BOLD}네트워크 설정:${NC}"
    echo "  ※ podman 네트워크를 사용합니다 (단순화된 네트워크 구성)"
    NETWORK_NAME="podman"

    read -p "컨테이너 이름 prefix [기본값: dify]: " CONTAINER_PREFIX
    CONTAINER_PREFIX=${CONTAINER_PREFIX:-dify}

    # Nginx 사용 여부
    echo ""
    echo -e "${BOLD}Nginx 리버스 프록시:${NC}"
    echo "  - yes: Nginx 사용 (포트 80으로 통합 접속)"
    echo "  - no:  Web(9008), API(5001) 직접 접속"
    read -p "Nginx를 사용하시겠습니까? (yes/no) [기본값: no]: " USE_NGINX
    USE_NGINX=${USE_NGINX:-no}

    # 설정 확인
    echo ""
    log_section "설정 확인"
    echo ""
    echo "  ${BOLD}[웹 접근]${NC}          http://$WEB_ACCESS_IP:$WEB_PORT"
    echo "  ${BOLD}[원격 DB 서버]${NC}    $REMOTE_DB_IP"
    echo ""
    echo "  PostgreSQL:       $DB_USERNAME@$REMOTE_DB_IP:$DB_PORT/$DB_DATABASE (원격)"
    echo "  Milvus:           $REMOTE_DB_IP:$MILVUS_PORT (원격)"
    echo "  Redis:            $REDIS_CONTAINER_NAME:$REDIS_PORT (로컬 컨테이너)"
    echo ""
    echo "  네트워크:         $NETWORK_NAME"
    echo "  컨테이너 prefix:  $CONTAINER_PREFIX"
    echo "  Nginx 사용:       $USE_NGINX"
    echo ""

    read -p "이 설정으로 진행하시겠습니까? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "설정 취소됨"
        exit 0
    fi

    # 설정 저장
    save_config
    log_success "설정이 저장되었습니다: $CONFIG_FILE"
}

# ============================================
# 초기 설정 확인
# ============================================
check_config() {
    if ! load_config; then
        log_warning "설정 파일이 없습니다. 설정을 시작합니다."
        interactive_config
    fi
}

# ============================================
# 환경 변수 설정
# ============================================
setup_environment() {
    # 디렉토리 설정
    CONFIG_DIR="${SCRIPT_DIR}/config"
    VOLUMES_DIR="${SCRIPT_DIR}/volumes"
    IMAGES_DIR="${SCRIPT_DIR}/images"

    # 로컬 서버 IP - 설정 파일에서 이미 로드됨
    # LOCAL_HOST_IP는 .dify-config에서 로드된 값 사용
    # WEB_ACCESS_IP와 WEB_PORT도 .dify-config에서 로드됨

    # Milvus 호스트
    MILVUS_HOST="${REMOTE_DB_IP}"
    DB_HOST="${REMOTE_DB_IP}"

    # Redis 설정 (로컬 서버의 기존 컨테이너 사용)
    # [2026-01-23] 호스트 IP와 외부 포트(6380)를 사용하여 DNS 해석 문제 해결
    # REDIS_CONTAINER_NAME은 컨테이너 확인용으로만 사용
    REDIS_HOST="${LOCAL_HOST_IP}"
    REDIS_PORT="6380"
    # REDIS_PASSWORD는 설정 파일에서 로드됨

    # Secret Keys
    SECRET_KEY="sk-9f73s3ljTXVcMT3Blbkdfsx_adsfaflafasd"
    SANDBOX_API_KEY="dify-sandbox-$(openssl rand -hex 16)"
    PLUGIN_DAEMON_KEY="sk-plugin-daemon-$(openssl rand -hex 16)"
    INNER_API_KEY="sk-inner-api-key-$(openssl rand -hex 16)"

    # 컨테이너 리스트 (Redis는 원격 서버 사용, Nginx 선택적)
    CONTAINERS_ORDER=(
        "${CONTAINER_PREFIX}-sandbox"
        "${CONTAINER_PREFIX}-plugin-daemon"
        "${CONTAINER_PREFIX}-api"
        "${CONTAINER_PREFIX}-worker"
        "${CONTAINER_PREFIX}-web"
    )

    CONTAINERS_STOP_ORDER=(
        "${CONTAINER_PREFIX}-web"
        "${CONTAINER_PREFIX}-worker"
        "${CONTAINER_PREFIX}-api"
        "${CONTAINER_PREFIX}-plugin-daemon"
        "${CONTAINER_PREFIX}-sandbox"
    )

    # Nginx 사용 시 목록에 추가
    if [[ "$USE_NGINX" =~ ^[Yy][Ee][Ss]$ ]]; then
        CONTAINERS_ORDER+=("${CONTAINER_PREFIX}-nginx")
        CONTAINERS_STOP_ORDER=("${CONTAINER_PREFIX}-nginx" "${CONTAINERS_STOP_ORDER[@]}")
    fi
}

# ============================================
# 사용법 출력
# ============================================
show_usage() {
    cat << EOF
${BOLD}Dify 전체 관리 스크립트${NC}

${BOLD}사용법:${NC}
  $0 <COMMAND> [OPTIONS]

${BOLD}명령어:${NC}
  ${GREEN}install${NC}    - 전체 설치 (이미지 로드 + DB 초기화 + 컨테이너 시작)
  ${GREEN}start${NC}      - Dify 시작
  ${GREEN}stop${NC}       - Dify 중지
  ${GREEN}restart${NC}    - Dify 재시작
  ${GREEN}status${NC}     - 상태 확인
  ${GREEN}logs${NC}       - 로그 확인 [컨테이너명]
  ${GREEN}clean${NC}      - 전체 삭제 (컨테이너 + 네트워크)
  ${GREEN}check${NC}      - 환경 체크 (DB 연결 + 이미지 확인)
  ${GREEN}init-db${NC}    - DB 초기화 (테이블 생성 + 사용자 생성)
  ${GREEN}config${NC}     - 설정 변경

${BOLD}예제:${NC}
  # 최초 설치
  $0 install

  # Dify 시작
  $0 start

  # 상태 확인
  $0 status

  # API 로그 확인
  $0 logs dify-api

  # DB 초기화
  $0 init-db

  # 설정 변경
  $0 config

EOF
}

# ============================================
# 함수: 포트 사용 확인 및 해제
# ============================================
check_and_free_ports() {
    log_section "포트 사용 확인 및 정리"

    local PORTS=(80 ${WEB_PORT} 5001 5003 8194)

    for port in "${PORTS[@]}"; do
        local PID=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$PID" ]; then
            log_warning "포트 $port 사용 중 (PID: $PID)"

            # Podman 컨테이너인지 확인
            local CONTAINER=$(podman ps -a --filter "publish=$port" --format "{{.Names}}" 2>/dev/null || true)
            if [ -n "$CONTAINER" ]; then
                log_info "컨테이너 중지 및 삭제: $CONTAINER"
                podman rm -f "$CONTAINER" 2>/dev/null || true
                log_success "✓ 포트 $port 해제됨"
            else
                log_warning "포트 $port는 Podman 외부 프로세스가 사용 중입니다."
                log_info "수동으로 확인하세요: lsof -i :$port"
            fi
        fi
    done
}

# ============================================
# 함수: 기존 컨테이너 정리
# ============================================
cleanup_existing_containers() {
    log_section "기존 Dify 컨테이너 정리"

    local FOUND_ANY=false

    for container in "${CONTAINERS_STOP_ORDER[@]}"; do
        if podman ps -a --filter "name=${container}" --format "{{.Names}}" | grep -q "${container}"; then
            FOUND_ANY=true
            log_info "삭제 중: ${container}"
            podman rm -f "${container}" 2>/dev/null || true
            log_success "✓ ${container} 삭제됨"
        fi
    done

    if [ "$FOUND_ANY" = false ]; then
        log_info "기존 컨테이너가 없습니다."
    else
        log_success "기존 컨테이너 정리 완료"
    fi
}

# ============================================
# 함수: 원격 DB 연결 테스트
# ============================================
test_remote_connection() {
    log_section "DB 서버 연결 테스트"

    # PostgreSQL 연결 테스트 (원격)
    log_info "PostgreSQL 연결 테스트 (원격): ${DB_HOST}:${DB_PORT}"
    if timeout 5 bash -c "cat < /dev/null > /dev/tcp/${DB_HOST}/${DB_PORT}" 2>/dev/null; then
        log_success "PostgreSQL 연결 성공 ✓"
    else
        log_error "PostgreSQL 연결 실패: ${DB_HOST}:${DB_PORT}"
        log_warning "원격 서버의 PostgreSQL이 실행 중인지 확인하세요."
        return 1
    fi

    # Milvus 연결 테스트 (원격)
    log_info "Milvus 연결 테스트 (원격): ${MILVUS_HOST}:${MILVUS_PORT}"
    if timeout 5 bash -c "cat < /dev/null > /dev/tcp/${MILVUS_HOST}/${MILVUS_PORT}" 2>/dev/null; then
        log_success "Milvus 연결 성공 ✓"
    else
        log_error "Milvus 연결 실패: ${MILVUS_HOST}:${MILVUS_PORT}"
        log_warning "원격 서버의 Milvus가 실행 중인지 확인하세요."
        return 1
    fi

    # Redis 컨테이너 존재 확인 (로컬)
    # [2026-01-23] REDIS_CONTAINER_NAME을 사용하여 컨테이너 확인
    log_info "Redis 컨테이너 확인 (로컬): ${REDIS_CONTAINER_NAME}"
    if podman ps --filter "name=${REDIS_CONTAINER_NAME}" --format "{{.Names}}" | grep -q "${REDIS_CONTAINER_NAME}"; then
        log_success "Redis 컨테이너 실행 중 ✓ (${REDIS_CONTAINER_NAME})"
        log_info "Redis 연결 정보: ${REDIS_HOST}:${REDIS_PORT}"
    else
        log_error "Redis 컨테이너를 찾을 수 없습니다: ${REDIS_CONTAINER_NAME}"
        log_warning "로컬 서버의 ${REDIS_CONTAINER_NAME} 컨테이너가 실행 중인지 확인하세요."
        log_info "컨테이너 확인: podman ps -a --filter 'name=${REDIS_CONTAINER_NAME}'"
        return 1
    fi

    echo ""
    log_success "모든 DB 연결 테스트 통과!"
    return 0
}

# ============================================
# 함수: DB 초기화 (테이블 생성)
# ============================================
init_database() {
    log_section "PostgreSQL 데이터베이스 초기화"

    # PostgreSQL 클라이언트 확인
    if ! command -v psql &> /dev/null; then
        log_warning "psql 명령이 없습니다. PostgreSQL 클라이언트를 설치하거나 API 컨테이너가 자동으로 초기화합니다."
        return 0
    fi

    # DB 연결 테스트
    log_info "데이터베이스 연결 테스트..."
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d "$DB_DATABASE" -c "SELECT 1;" &>/dev/null; then
        log_success "데이터베이스 연결 성공"
    else
        log_warning "데이터베이스 '${DB_DATABASE}'가 존재하지 않습니다."
        log_info "데이터베이스 생성 중..."

        # postgres 데이터베이스에 연결하여 dify 데이터베이스 생성
        if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d postgres -c "CREATE DATABASE ${DB_DATABASE};" &>/dev/null; then
            log_success "데이터베이스 '${DB_DATABASE}' 생성 완료 ✓"
        else
            # 이미 존재하는 경우의 에러 무시
            if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d "$DB_DATABASE" -c "SELECT 1;" &>/dev/null; then
                log_success "데이터베이스 연결 성공"
            else
                log_error "데이터베이스 생성 실패"
                log_info "API 컨테이너가 시작할 때 자동으로 마이그레이션을 수행합니다."
                return 0
            fi
        fi
    fi

    # 테이블 존재 확인
    log_info "기존 테이블 확인 중..."
    local TABLE_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d "$DB_DATABASE" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')

    if [ "$TABLE_COUNT" -gt 0 ]; then
        log_success "데이터베이스에 이미 ${TABLE_COUNT}개의 테이블이 존재합니다. (스킵)"
        log_info "기존 데이터베이스를 사용합니다."
    else
        log_info "테이블이 없습니다. API 컨테이너가 시작할 때 자동으로 마이그레이션을 수행합니다."
        log_info "MIGRATION_ENABLED=true 환경 변수가 설정되어 있습니다."
    fi
}

# ============================================
# 함수: 초기 사용자 생성
# ============================================
create_initial_user() {
    log_section "초기 관리자 사용자 확인"

    # PostgreSQL 클라이언트 확인
    if ! command -v psql &> /dev/null; then
        log_info "psql 명령이 없습니다. 웹 인터페이스에서 관리자 계정을 생성하세요."
        log_info "접속 URL: http://${WEB_ACCESS_IP}:${WEB_PORT}"
        return 0
    fi

    # DB 연결 확인
    if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d "$DB_DATABASE" -c "SELECT 1;" &>/dev/null; then
        log_warning "데이터베이스 연결 실패. 웹 인터페이스에서 관리자 계정을 생성하세요."
        return 0
    fi

    # accounts 테이블 존재 확인
    local TABLE_EXISTS=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d "$DB_DATABASE" -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'accounts');" 2>/dev/null | tr -d ' ')

    if [ "$TABLE_EXISTS" = "t" ]; then
        # 기존 사용자 확인
        local USER_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d "$DB_DATABASE" -t -c "SELECT COUNT(*) FROM accounts;" 2>/dev/null | tr -d ' ')

        if [ -z "$USER_COUNT" ] || [ "$USER_COUNT" = "0" ]; then
            log_info "등록된 사용자가 없습니다."
            log_info "웹 인터페이스에서 최초 관리자 계정을 생성하세요."
            log_info "접속 URL: http://${WEB_ACCESS_IP}:${WEB_PORT}"
        else
            log_success "데이터베이스에 이미 ${USER_COUNT}명의 사용자가 존재합니다. (스킵)"
        fi
    else
        log_info "아직 테이블이 생성되지 않았습니다."
        log_info "API 컨테이너가 시작된 후 웹 인터페이스에서 관리자 계정을 생성하세요."
        log_info "접속 URL: http://${WEB_ACCESS_IP}:${WEB_PORT}"
    fi
}

# ============================================
# 함수: 이미지 확인
# ============================================
check_images() {
    log_section "Docker 이미지 확인"

    local REQUIRED_IMAGES=(
        "docker.io/langgenius/dify-api:latest"
        "docker.io/langgenius/dify-web:latest"
        "docker.io/langgenius/dify-sandbox:0.2.12"
        "docker.io/langgenius/dify-plugin-daemon:latest"
        "docker.io/library/nginx:latest"
    )

    local ALL_PRESENT=true

    for image in "${REQUIRED_IMAGES[@]}"; do
        if podman images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${image}$"; then
            log_success "✓ ${image}"
        else
            log_error "✗ ${image} - 누락됨"
            ALL_PRESENT=false
        fi
    done

    echo ""
    if [ "$ALL_PRESENT" = true ]; then
        log_success "모든 필수 이미지가 존재합니다!"
        return 0
    else
        log_error "일부 이미지가 누락되었습니다."
        return 1
    fi
}

# ============================================
# 함수: 이미지 로드
# ============================================
load_images() {
    log_section "Docker 이미지 로드"

    if [ ! -d "${IMAGES_DIR}" ]; then
        log_error "이미지 디렉토리가 없습니다: ${IMAGES_DIR}"
        return 1
    fi

    local IMAGE_FILES=(
        "dify-api-latest.tar"
        "dify-web-latest.tar"
        "dify-sandbox-latest.tar"
        "dify-plugin-daemon-latest.tar"
        "nginx-docker.io-library-nginx-latest.tar"
    )

    for image_file in "${IMAGE_FILES[@]}"; do
        local image_path="${IMAGES_DIR}/${image_file}"

        if [ -f "${image_path}" ]; then
            log_info "로드 중: ${image_file}"
            if podman load -i "${image_path}"; then
                log_success "✓ ${image_file} 로드 완료"
            else
                log_error "✗ ${image_file} 로드 실패"
                return 1
            fi
        else
            log_warning "파일 없음: ${image_file}"
        fi
    done

    echo ""
    log_success "모든 이미지 로드 완료!"
    return 0
}

# ============================================
# 함수: 네트워크 생성
# [2026-01-23] 단순화: podman 네트워크만 사용
# ============================================
create_network() {
    log_section "Podman 네트워크 설정"

    # podman 네트워크는 기본으로 존재함
    if podman network exists "${NETWORK_NAME}" 2>/dev/null; then
        log_success "네트워크 '${NETWORK_NAME}' 사용 준비 완료"
    else
        log_info "네트워크 '${NETWORK_NAME}' 생성 중..."
        podman network create "${NETWORK_NAME}"
        log_success "네트워크 생성 완료 ✓"
    fi

    # Redis 컨테이너 확인
    log_info "Redis 컨테이너 확인 중: ${REDIS_CONTAINER_NAME}"

    # Redis가 실행 중인지 확인 (최대 30초 대기)
    local REDIS_WAIT=0
    local MAX_WAIT=30

    while [ $REDIS_WAIT -lt $MAX_WAIT ]; do
        if podman ps --format "{{.Names}}" | grep -q "^${REDIS_CONTAINER_NAME}$"; then
            log_success "Redis 컨테이너가 실행 중입니다. ✓"
            break
        fi

        if [ $REDIS_WAIT -eq 0 ]; then
            log_warning "Redis 컨테이너가 실행되지 않았습니다. 대기 중..."
            log_info "※ 다른 터미널에서 podman-start-remote.sh를 먼저 실행하세요."
        fi

        sleep 2
        REDIS_WAIT=$((REDIS_WAIT + 2))
        echo -n "."
    done
    echo ""

    # Redis가 실행 중인지 최종 확인
    if ! podman ps --format "{{.Names}}" | grep -q "^${REDIS_CONTAINER_NAME}$"; then
        log_error "Redis 컨테이너 '${REDIS_CONTAINER_NAME}'가 실행되지 않았습니다!"
        log_error "podman-start-remote.sh를 먼저 실행하거나 Redis를 수동으로 시작하세요."
        log_info "예: podman start ${REDIS_CONTAINER_NAME}"
        return 1
    fi

    # Redis 컨테이너가 podman 네트워크에 연결되어 있는지 확인
    log_info "Redis 컨테이너 네트워크 연결 확인 중..."

    # 이미 연결되어 있는지 확인
    if podman inspect ${REDIS_CONTAINER_NAME} --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null | grep -q "${NETWORK_NAME}"; then
        log_success "Redis 컨테이너가 이미 ${NETWORK_NAME} 네트워크에 연결되어 있습니다."
    else
        podman network connect "${NETWORK_NAME}" "${REDIS_CONTAINER_NAME}" 2>/dev/null || true
        log_success "Redis 컨테이너를 ${NETWORK_NAME} 네트워크에 연결했습니다. ✓"
    fi

    # Redis 연결 테스트 (컨테이너 내부에서)
    log_info "Redis 연결 테스트 중..."
    if podman exec ${REDIS_CONTAINER_NAME} redis-cli ping 2>/dev/null | grep -q "PONG"; then
        log_success "Redis 응답 확인: PONG ✓"
    else
        log_warning "Redis 응답 확인 실패 (컨테이너가 아직 시작 중일 수 있습니다)"
    fi
}

# ============================================
# 함수: Sandbox 시작
# ============================================
start_sandbox() {
    local CONTAINER_NAME="${CONTAINER_PREFIX}-sandbox"

    log_info "Sandbox 시작 중..."

    podman run -d \
        --name "${CONTAINER_NAME}" \
        --network "${NETWORK_NAME}" \
        -p 8194:8194 \
        --restart unless-stopped \
        -e API_KEY="${SANDBOX_API_KEY}" \
        -e GIN_MODE=release \
        -e WORKER_TIMEOUT=15 \
        --security-opt seccomp=unconfined \
        --security-opt apparmor=unconfined \
        --cap-add SYS_ADMIN \
        docker.io/langgenius/dify-sandbox:latest

    log_success "✓ Sandbox 시작 완료 (포트: 8194)"
}

# ============================================
# 함수: Plugin Daemon 시작
# ============================================
start_plugin_daemon() {
    local CONTAINER_NAME="${CONTAINER_PREFIX}-plugin-daemon"

    log_info "Plugin Daemon 시작 중..."

    mkdir -p "${VOLUMES_DIR}/plugin-daemon-data"

    podman run -d \
        --name "${CONTAINER_NAME}" \
        --network "${NETWORK_NAME}" \
        -p 5003:5003 \
        --restart unless-stopped \
        -v "${VOLUMES_DIR}/plugin-daemon-data:/app/storage:z" \
        -e LOG_LEVEL=INFO \
        -e SERVER_KEY="${SECRET_KEY}" \
        -e SECRET_KEY="${SECRET_KEY}" \
        -e GIN_MODE=release \
        -e SERVER_PORT=5003 \
        -e DIFY_INNER_API_URL="http://${CONTAINER_PREFIX}-api:5001" \
        -e DIFY_INNER_API_KEY="${SECRET_KEY}" \
        -e PLUGIN_REMOTE_INSTALLING_HOST="https://marketplace.dify.ai" \
        -e PLUGIN_REMOTE_INSTALLING_PORT="443" \
        -e PLUGIN_REMOTE_INSTALLING_ENABLED="false" \
        -e PLUGIN_WORKING_PATH="/app/storage/plugins" \
        -e PLUGIN_INSTALLED_PATH="/app/storage/plugins" \
        -e PLUGIN_STORAGE_PATH="/app/storage" \
        -e PLUGIN_ENDPOINT_ENABLED="true" \
        -e PERSISTENCE_STORAGE_PATH="/app/storage/persistence" \
        -e STORAGE_TYPE="local" \
        -e STORAGE_LOCAL_PATH="/app/storage" \
        -e DEBUG_MODE="true" \
        -e REDIS_HOST="${LOCAL_HOST_IP}" \
        -e REDIS_PORT="6380" \
        -e REDIS_PASSWORD="${REDIS_PASSWORD}" \
        -e REDIS_DB=0 \
        -e DB_USERNAME="${DB_USERNAME}" \
        -e DB_PASSWORD="${DB_PASSWORD}" \
        -e DB_HOST="${DB_HOST}" \
        -e DB_PORT="${DB_PORT}" \
        -e DB_DATABASE="${DB_DATABASE}" \
        docker.io/langgenius/dify-plugin-daemon:latest

    log_success "✓ Plugin Daemon 시작 완료 (포트: 5003)"
}

# ============================================
# 함수: API 시작
# ============================================
start_api() {
    local CONTAINER_NAME="${CONTAINER_PREFIX}-api"

    log_info "API 시작 중..."

    mkdir -p "${VOLUMES_DIR}/api-storage"
    mkdir -p "${VOLUMES_DIR}/api-logs"

    podman run -d \
        --name "${CONTAINER_NAME}" \
        --network "${NETWORK_NAME}" \
        -p 5001:5001 \
        --restart unless-stopped \
        -v "${VOLUMES_DIR}/api-storage:/app/api/storage:z" \
        -v "${VOLUMES_DIR}/api-logs:/app/api/logs:z" \
        -e MODE=api \
        -e LOG_LEVEL=INFO \
        -e SECRET_KEY="${SECRET_KEY}" \
        -e DEPLOY_ENV=production \
        -e CONSOLE_WEB_URL="http://${WEB_ACCESS_IP}:${WEB_PORT}" \
        -e CONSOLE_API_URL="http://${WEB_ACCESS_IP}:5001" \
        -e SERVICE_API_URL="http://${WEB_ACCESS_IP}:5001" \
        -e APP_WEB_URL="http://${WEB_ACCESS_IP}:${WEB_PORT}" \
        -e CONSOLE_CORS_ALLOW_ORIGINS="http://${WEB_ACCESS_IP}:${WEB_PORT},http://${LOCAL_HOST_IP}:${WEB_PORT},http://localhost:${WEB_PORT},*" \
        -e WEB_API_CORS_ALLOW_ORIGINS="http://${WEB_ACCESS_IP}:${WEB_PORT},http://${LOCAL_HOST_IP}:${WEB_PORT},http://localhost:${WEB_PORT},*" \
        -e DB_USERNAME="${DB_USERNAME}" \
        -e DB_PASSWORD="${DB_PASSWORD}" \
        -e DB_HOST="${DB_HOST}" \
        -e DB_PORT="${DB_PORT}" \
        -e DB_DATABASE="${DB_DATABASE}" \
        -e REDIS_HOST="${REDIS_HOST}" \
        -e REDIS_PORT="${REDIS_PORT}" \
        -e REDIS_PASSWORD="${REDIS_PASSWORD}" \
        -e REDIS_DB=0 \
        -e REDIS_USE_SSL=false \
        -e CELERY_BROKER_URL="redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/1" \
        -e VECTOR_STORE=milvus \
        -e MILVUS_HOST="${MILVUS_HOST}" \
        -e MILVUS_PORT="${MILVUS_PORT}" \
        -e MILVUS_SECURE=false \
        -e CODE_EXECUTION_ENDPOINT="http://${CONTAINER_PREFIX}-sandbox:8194" \
        -e CODE_EXECUTION_API_KEY="${SANDBOX_API_KEY}" \
        -e STORAGE_TYPE=local \
        -e STORAGE_LOCAL_PATH=storage \
        -e MIGRATION_ENABLED=true \
        -e INNER_API_KEY="${SECRET_KEY}" \
        -e PLUGIN_DAEMON_URL="http://${CONTAINER_PREFIX}-plugin-daemon:5003" \
        -e PLUGIN_DAEMON_KEY="${SECRET_KEY}" \
        -e INNER_API_KEY_FOR_PLUGIN="${SECRET_KEY}" \
        docker.io/langgenius/dify-api:latest

    log_success "✓ API 시작 완료 (포트: 5001)"
}

# ============================================
# 함수: Worker 시작
# ============================================
start_worker() {
    local CONTAINER_NAME="${CONTAINER_PREFIX}-worker"

    log_info "Worker 시작 중..."

    podman run -d \
        --name "${CONTAINER_NAME}" \
        --network "${NETWORK_NAME}" \
        --restart unless-stopped \
        -v "${VOLUMES_DIR}/api-storage:/app/api/storage:z" \
        -v "${VOLUMES_DIR}/api-logs:/app/api/logs:z" \
        -e MODE=worker \
        -e LOG_LEVEL=INFO \
        -e SECRET_KEY="${SECRET_KEY}" \
        -e DEPLOY_ENV=production \
        -e DB_USERNAME="${DB_USERNAME}" \
        -e DB_PASSWORD="${DB_PASSWORD}" \
        -e DB_HOST="${DB_HOST}" \
        -e DB_PORT="${DB_PORT}" \
        -e DB_DATABASE="${DB_DATABASE}" \
        -e REDIS_HOST="${REDIS_HOST}" \
        -e REDIS_PORT="${REDIS_PORT}" \
        -e REDIS_PASSWORD="${REDIS_PASSWORD}" \
        -e REDIS_DB=0 \
        -e CELERY_BROKER_URL="redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/1" \
        -e VECTOR_STORE=milvus \
        -e MILVUS_HOST="${MILVUS_HOST}" \
        -e MILVUS_PORT="${MILVUS_PORT}" \
        -e STORAGE_TYPE=local \
        -e STORAGE_LOCAL_PATH=storage \
        -e PLUGIN_DAEMON_URL="http://${CONTAINER_PREFIX}-plugin-daemon:5003" \
        -e PLUGIN_DAEMON_KEY="${SECRET_KEY}" \
        -e INNER_API_KEY_FOR_PLUGIN="${SECRET_KEY}" \
        docker.io/langgenius/dify-api:latest

    log_success "✓ Worker 시작 완료"
}

# ============================================
# 함수: Web 시작
# ============================================
start_web() {
    local CONTAINER_NAME="${CONTAINER_PREFIX}-web"

    log_info "Web 시작 중..."

    podman run -d \
        --name "${CONTAINER_NAME}" \
        --network "${NETWORK_NAME}" \
        -p ${WEB_PORT}:3000 \
        --restart unless-stopped \
        -e CONSOLE_API_URL="http://${WEB_ACCESS_IP}:5001" \
        -e APP_API_URL="http://${WEB_ACCESS_IP}:5001" \
        docker.io/langgenius/dify-web:latest

    log_success "✓ Web 시작 완료 (포트: ${WEB_PORT})"
}

# ============================================
# 함수: Nginx 시작
# ============================================
start_nginx() {
    local CONTAINER_NAME="${CONTAINER_PREFIX}-nginx"

    log_info "Nginx 시작 중..."

    mkdir -p "${CONFIG_DIR}/nginx"
    cat > "${CONFIG_DIR}/nginx/nginx.conf" << 'NGINX_EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_size "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 15M;

    upstream dify-api {
        server dify-api:5001;
    }

    upstream dify-web {
        server dify-web:3000;
    }

    server {
        listen 80;
        server_name _;

        location /console/api {
            proxy_pass http://dify-api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /api {
            proxy_pass http://dify-api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /v1 {
            proxy_pass http://dify-api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /files {
            proxy_pass http://dify-api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            proxy_pass http://dify-web;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
NGINX_EOF

    podman run -d \
        --name "${CONTAINER_NAME}" \
        --network "${NETWORK_NAME}" \
        -p 80:80 \
        --restart unless-stopped \
        -v "${CONFIG_DIR}/nginx/nginx.conf:/etc/nginx/nginx.conf:z,ro" \
        nginx:latest

    log_success "✓ Nginx 시작 완료 (포트: 80)"
}

# ============================================
# 함수: 환경 체크
# ============================================
check_environment() {
    log_header "환경 체크"

    local CHECK_FAILED=false

    if ! test_remote_connection; then
        CHECK_FAILED=true
    fi

    if ! check_images; then
        CHECK_FAILED=true
    fi

    echo ""
    if [ "$CHECK_FAILED" = true ]; then
        log_error "환경 체크 실패!"
        return 1
    else
        log_success "모든 환경 체크 통과!"
        return 0
    fi
}

# ============================================
# 함수: 모든 컨테이너 시작
# ============================================
start_all_containers() {
    log_section "Dify 컨테이너 순차 시작"

    log_info "※ Redis는 로컬 서버의 기존 ${REDIS_HOST} 컨테이너를 사용합니다"
    echo ""

    start_sandbox
    sleep 3

    start_plugin_daemon
    sleep 3

    start_api
    sleep 5

    start_worker
    sleep 3

    start_web
    sleep 3

    # Nginx 선택적 시작
    if [[ "$USE_NGINX" =~ ^[Yy][Ee][Ss]$ ]]; then
        start_nginx
        sleep 2
    else
        log_info "Nginx는 사용하지 않습니다 (설정: USE_NGINX=$USE_NGINX)"
    fi

    echo ""
    log_success "모든 컨테이너 시작 완료!"
}

# ============================================
# 함수: 전체 설치
# ============================================
install_all() {
    log_header "Dify 전체 설치 시작"

    local TOTAL_STEPS=7
    local CURRENT_STEP=0

    # Step 1: 원격 DB 연결 테스트
    CURRENT_STEP=$((CURRENT_STEP + 1))
    log_step $CURRENT_STEP $TOTAL_STEPS "원격 DB 연결 테스트"
    if ! test_remote_connection; then
        log_error "설치 중단: 원격 DB 연결 실패"
        exit 1
    fi
    sleep 1

    # Step 2: 이미지 확인 및 로드
    CURRENT_STEP=$((CURRENT_STEP + 1))
    log_step $CURRENT_STEP $TOTAL_STEPS "Docker 이미지 확인 및 로드"
    if ! check_images; then
        log_info "이미지 로드를 시작합니다..."
        if ! load_images; then
            log_error "설치 중단: 이미지 로드 실패"
            exit 1
        fi
    fi
    sleep 1

    # Step 3: 기존 컨테이너 정리
    CURRENT_STEP=$((CURRENT_STEP + 1))
    log_step $CURRENT_STEP $TOTAL_STEPS "기존 컨테이너 정리"
    cleanup_existing_containers
    sleep 1

    # Step 4: 포트 확인 및 해제
    CURRENT_STEP=$((CURRENT_STEP + 1))
    log_step $CURRENT_STEP $TOTAL_STEPS "포트 확인 및 해제"
    check_and_free_ports
    sleep 1

    # Step 5: 네트워크 생성 및 Redis 연결
    CURRENT_STEP=$((CURRENT_STEP + 1))
    log_step $CURRENT_STEP $TOTAL_STEPS "네트워크 설정"
    if ! create_network; then
        log_error "네트워크 설정 실패. Redis가 실행 중인지 확인하세요."
        exit 1
    fi
    sleep 1

    # Step 6: DB 초기화
    CURRENT_STEP=$((CURRENT_STEP + 1))
    log_step $CURRENT_STEP $TOTAL_STEPS "데이터베이스 초기화"
    init_database
    create_initial_user
    sleep 1

    # Step 7: 컨테이너 시작
    CURRENT_STEP=$((CURRENT_STEP + 1))
    log_step $CURRENT_STEP $TOTAL_STEPS "Dify 컨테이너 시작"
    start_all_containers

    echo ""
    log_header "설치 완료!"
    show_access_info
}

# ============================================
# 함수: Dify 시작
# ============================================
start_dify() {
    log_header "Dify 시작"

    # 환경 체크
    if ! check_environment; then
        log_error "환경 체크 실패. 'install' 명령을 먼저 실행하세요."
        exit 1
    fi

    # 기존 컨테이너 정리
    cleanup_existing_containers

    # 포트 확인
    check_and_free_ports

    # 네트워크 생성 및 Redis 연결
    if ! create_network; then
        log_error "네트워크 설정 실패. Redis가 실행 중인지 확인하세요."
        exit 1
    fi

    # 컨테이너 시작
    start_all_containers

    echo ""
    log_header "Dify 시작 완료!"
    show_access_info
}

# ============================================
# 함수: 모든 컨테이너 중지
# ============================================
stop_all() {
    log_header "Dify 중지"

    for container in "${CONTAINERS_STOP_ORDER[@]}"; do
        if podman ps -a --filter "name=${container}" --format "{{.Names}}" | grep -q "${container}"; then
            log_info "중지 중: ${container}"
            podman stop "${container}" 2>/dev/null || true
            log_success "✓ ${container} 중지됨"
        fi
    done

    echo ""
    log_success "Dify 중지 완료"
}

# ============================================
# 함수: 재시작
# ============================================
restart_all() {
    log_header "Dify 재시작"

    stop_all
    sleep 3
    start_dify
}

# ============================================
# 함수: 상태 확인
# ============================================
status_all() {
    log_header "Dify 컨테이너 상태"

    echo ""
    log_section "서버 정보"
    echo "  로컬 서버:   ${LOCAL_HOST_IP} (자동 감지)"
    echo "  원격 DB 서버: ${REMOTE_DB_IP}"

    echo ""
    log_section "컨테이너 상태"
    echo ""
    podman ps -a --filter "name=${CONTAINER_PREFIX}-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    echo ""
    log_section "원격 DB 정보"
    echo "  PostgreSQL: ${DB_HOST}:${DB_PORT}"
    echo "  Milvus:     ${MILVUS_HOST}:${MILVUS_PORT}"

    echo ""
    log_section "로컬 리소스"
    echo "  Redis:      ${REDIS_HOST}:${REDIS_PORT} (기존 컨테이너)"

    echo ""
    log_section "Dify 컨테이너 통계"
    local RUNNING_COUNT=$(podman ps --filter "name=${CONTAINER_PREFIX}-" --format "{{.Names}}" | wc -l)
    local TOTAL_COUNT=${#CONTAINERS_ORDER[@]}
    echo "  실행 중: ${RUNNING_COUNT}/${TOTAL_COUNT}"
    echo "  ※ Redis는 기존 컨테이너 사용 (카운트 제외)"

    echo ""
}

# ============================================
# 함수: 로그 확인
# ============================================
logs_container() {
    local CONTAINER=${2:-"${CONTAINER_PREFIX}-api"}

    log_info "컨테이너 로그: ${CONTAINER}"
    echo ""

    if podman ps -a --filter "name=${CONTAINER}" --format "{{.Names}}" | grep -q "${CONTAINER}"; then
        podman logs -f "${CONTAINER}"
    else
        log_error "컨테이너를 찾을 수 없습니다: ${CONTAINER}"
        echo ""
        echo "사용 가능한 컨테이너:"
        podman ps -a --filter "name=${CONTAINER_PREFIX}-" --format "  - {{.Names}}"
    fi
}

# ============================================
# 함수: 전체 삭제
# ============================================
clean_all() {
    log_header "Dify 전체 삭제"

    read -p "정말로 모든 컨테이너와 네트워크를 삭제하시겠습니까? (yes/no): " -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "삭제 취소됨"
        exit 0
    fi

    log_section "컨테이너 삭제"
    for container in "${CONTAINERS_STOP_ORDER[@]}"; do
        if podman ps -a --filter "name=${container}" --format "{{.Names}}" | grep -q "${container}"; then
            log_info "삭제 중: ${container}"
            podman rm -f "${container}" 2>/dev/null || true
            log_success "✓ ${container} 삭제됨"
        fi
    done

    log_section "네트워크 삭제"
    if podman network exists "${NETWORK_NAME}" 2>/dev/null; then
        log_info "네트워크 삭제 중: ${NETWORK_NAME}"
        podman network rm "${NETWORK_NAME}" 2>/dev/null || true
        log_success "✓ 네트워크 삭제됨"
    fi

    echo ""
    log_success "전체 삭제 완료!"
    log_warning "볼륨 데이터는 삭제되지 않았습니다: ${VOLUMES_DIR}"
    log_info "볼륨 삭제: rm -rf ${VOLUMES_DIR}/*"
}

# ============================================
# 함수: 접속 정보 표시
# ============================================
show_access_info() {
    echo ""
    log_section "접속 정보"
    echo ""
    echo "  ${BOLD}로컬 서버:${NC} $LOCAL_HOST_IP (자동 감지)"
    echo ""

    if [[ "$USE_NGINX" =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "  ${BOLD}Web UI (Nginx):${NC}  http://${LOCAL_HOST_IP}"
        echo "  ${BOLD}Console:${NC}         http://${LOCAL_HOST_IP}:9008"
        echo "  ${BOLD}API:${NC}             http://${LOCAL_HOST_IP}:5001"
    else
        echo "  ${BOLD}Web UI:${NC}      http://${LOCAL_HOST_IP}:9008"
        echo "  ${BOLD}API:${NC}         http://${LOCAL_HOST_IP}:5001"
        echo ""
        echo "  ${YELLOW}※ Nginx를 사용하지 않습니다${NC}"
        echo "  ${YELLOW}※ Web과 API에 직접 접속하세요${NC}"
    fi

    echo ""
    log_section "원격 DB 서버"
    echo ""
    echo "  ${BOLD}서버 IP:${NC}    ${REMOTE_DB_IP}"
    echo "  ${BOLD}PostgreSQL:${NC} ${DB_HOST}:${DB_PORT}"
    echo "  ${BOLD}Milvus:${NC}     ${MILVUS_HOST}:${MILVUS_PORT}"
    echo ""
    log_section "로컬 리소스"
    echo ""
    echo "  ${BOLD}Redis:${NC}      ${REDIS_HOST}:${REDIS_PORT} (기존 컨테이너)"
    echo ""
    log_section "관리 명령어"
    echo ""
    echo "  상태 확인:  $0 status"
    echo "  로그 확인:  $0 logs [컨테이너명]"
    echo "  중지:       $0 stop"
    echo "  재시작:     $0 restart"
    echo ""
}

# ============================================
# 메인 실행
# ============================================

# 인자 확인
if [ -z "$1" ]; then
    show_usage
    exit 1
fi

COMMAND=$1

# 설정 로드
check_config
setup_environment

# 명령 실행
case "${COMMAND}" in
    install)
        install_all
        ;;
    start)
        start_dify
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        status_all
        ;;
    logs)
        logs_container "$@"
        ;;
    check)
        check_environment
        ;;
    init-db)
        init_database
        create_initial_user
        ;;
    config)
        interactive_config
        ;;
    clean)
        clean_all
        ;;
    *)
        log_error "알 수 없는 명령어: ${COMMAND}"
        echo ""
        show_usage
        exit 1
        ;;
esac

exit 0
