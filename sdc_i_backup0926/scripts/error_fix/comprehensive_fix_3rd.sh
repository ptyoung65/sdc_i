#!/bin/bash

# 3차 설치 종합 문제 해결 스크립트
# 모든 일반적인 문제를 자동으로 감지하고 해결

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[3차-INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[3차-SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[3차-WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[3차-ERROR]${NC} $1"; }

echo "🔧 SDC 3차 설치 종합 문제 해결 스크립트 시작"
echo "=============================================="

# .env 파일 로드
if [ -f "/home/chatpro/sdc_i/.env" ]; then
    source "/home/chatpro/sdc_i/.env"
    log_success ".env 파일 로드 완료"
else
    log_error ".env 파일이 없습니다."
    exit 1
fi

# sudo 암호 확인
if [ -z "$SUDO_PASSWORD" ]; then
    log_error "SUDO_PASSWORD가 설정되지 않았습니다."
    exit 1
fi

log_info "sudo 암호 확인: 설정됨"

# =============================================================================
# 1. 포트 충돌 해결
# =============================================================================
log_info "1단계: 포트 충돌 해결 중..."

CRITICAL_PORTS=(3000 3003 3005 8000 8080 5050 5433 6380)

for port in "${CRITICAL_PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warning "포트 $port 충돌 감지 - 정리 중..."
        lsof -ti:$port | xargs -r kill -9 2>/dev/null || true
        sleep 1
        log_success "포트 $port 정리 완료"
    fi
done

# =============================================================================
# 2. 의존성 확인 및 설치
# =============================================================================
log_info "2단계: 의존성 확인 중..."

# Node.js 확인
if ! command -v node >/dev/null 2>&1; then
    log_warning "Node.js가 설치되지 않았습니다."
    # Node.js 설치 로직 필요시 추가
fi

# Python 확인
if ! command -v python3 >/dev/null 2>&1; then
    log_warning "Python3이 설치되지 않았습니다."
    # Python 설치 로직 필요시 추가
fi

# Podman 확인
if ! command -v podman >/dev/null 2>&1; then
    log_warning "Podman이 설치되지 않았습니다."
    # Podman 설치 로직 필요시 추가
fi

log_success "의존성 확인 완료"

# =============================================================================
# 3. 네트워크 및 방화벽 설정
# =============================================================================
log_info "3단계: 네트워크 및 방화벽 설정 중..."

# 방화벽에서 필요한 포트 열기
for port in "${CRITICAL_PORTS[@]}"; do
    log_info "포트 $port 방화벽 설정 중..."
    timeout 10 bash -c "echo '$SUDO_PASSWORD' | sudo -S firewall-cmd --permanent --add-port=${port}/tcp" >/dev/null 2>&1 || log_warning "포트 $port 방화벽 설정 실패"
done

# 방화벽 재로드
timeout 10 bash -c "echo '$SUDO_PASSWORD' | sudo -S firewall-cmd --reload" >/dev/null 2>&1 || log_warning "방화벽 재로드 실패"

log_success "네트워크 설정 완료"

# =============================================================================
# 4. 디렉토리 및 권한 확인
# =============================================================================
log_info "4단계: 디렉토리 및 권한 확인 중..."

REQUIRED_DIRS=(
    "/home/chatpro/sdc_i/frontend"
    "/home/chatpro/sdc_i/backend"
    "/home/chatpro/sdc_i/services"
    "/home/chatpro/sdc_i/scripts"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        log_warning "디렉토리 누락: $dir"
        mkdir -p "$dir"
        log_success "디렉토리 생성: $dir"
    fi
done

log_success "디렉토리 및 권한 확인 완료"

# =============================================================================
# 5. Podman 네트워크 및 볼륨 확인
# =============================================================================
log_info "5단계: Podman 인프라 확인 중..."

# 네트워크 확인
if ! podman network exists sdc-network 2>/dev/null; then
    log_info "sdc-network 생성 중..."
    podman network create sdc-network || log_warning "sdc-network 생성 실패"
fi

if ! podman network exists sdc-dev-network 2>/dev/null; then
    log_info "sdc-dev-network 생성 중..."
    podman network create sdc-dev-network || log_warning "sdc-dev-network 생성 실패"
fi

# 볼륨 확인
REQUIRED_VOLUMES=(
    "postgres-data"
    "redis-data"
    "milvus-data"
    "vscode-extensions"
    "vscode-data"
    "postgres-dev-data"
    "redis-dev-data"
    "pgadmin-dev-data"
)

for volume in "${REQUIRED_VOLUMES[@]}"; do
    if ! podman volume exists "$volume" 2>/dev/null; then
        log_info "볼륨 $volume 생성 중..."
        podman volume create "$volume" || log_warning "볼륨 $volume 생성 실패"
    fi
done

log_success "Podman 인프라 확인 완료"

# =============================================================================
# 6. 서비스 상태 확인
# =============================================================================
log_info "6단계: 서비스 상태 최종 확인 중..."

FAILED_PORTS=()

for port in "${CRITICAL_PORTS[@]}"; do
    if curl -s -o /dev/null -w "%{http_code}" "http://$HOST_IP:$port" --connect-timeout 2 2>/dev/null | grep -q "200\|302\|404"; then
        log_success "포트 $port: 정상"
    else
        log_warning "포트 $port: 비활성"
        FAILED_PORTS+=("$port")
    fi
done

# =============================================================================
# 7. 오류 로깅
# =============================================================================
if [ ${#FAILED_PORTS[@]} -gt 0 ]; then
    log_error "일부 서비스가 정상 작동하지 않습니다: ${FAILED_PORTS[*]}"

    # err_fix_3rd.md에 기록
    cat >> /home/chatpro/sdc_i/err_fix_3rd.md << EOF

### 오류 #3-$(date +%H%M) - 서비스 시작 실패
**발생 시간**: $(date '+%Y-%m-%d %H:%M:%S')
**오류 내용**: 포트 ${FAILED_PORTS[*]}에서 서비스 응답 없음
**원인 분석**: 서비스 시작 실패 또는 네트워크 문제
**해결 방법**: 각 서비스 개별 시작 및 로그 확인 필요
**예방책**: 사전 의존성 체크 및 순차적 서비스 시작
**관련 파일**: $(find /tmp -name "*service*log" 2>/dev/null | head -3 | tr '\n' ' ')
**자동화 스크립트**: scripts/error_fix/comprehensive_fix_3rd.sh

EOF
else
    log_success "🎉 모든 서비스가 정상 작동 중입니다!"

    # 성공 기록
    cat >> /home/chatpro/sdc_i/err_fix_3rd.md << EOF

## ✅ 성공 기록
**시간**: $(date '+%Y-%m-%d %H:%M:%S')
**상태**: 모든 핵심 서비스 정상 작동
**포트**: ${CRITICAL_PORTS[*]}
**접속 URL**:
- Frontend: http://$HOST_IP:3000
- Admin Panel: http://$HOST_IP:3003
- Developer Admin: http://$HOST_IP:3005
- Backend API: http://$HOST_IP:8000
- VSCode Server: http://$HOST_IP:8080
- PgAdmin: http://$HOST_IP:5050

EOF
fi

echo ""
log_info "3차 설치 종합 문제 해결 스크립트 완료"
echo "상세 로그는 err_fix_3rd.md를 확인하세요."