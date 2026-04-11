#!/bin/bash
# =============================================================================
# Vector Graph RAG 프론트엔드 UI 시작 스크립트
# =============================================================================
# 포트: 3016
# API 프록시: http://localhost:8015 (graph_rag_service.py)
#
# 사용법:
#   ./start-ui.sh             # 포그라운드 (개발 모드)
#   ./start-ui.sh --daemon    # 백그라운드
#   ./start-ui.sh --build     # 프로덕션 빌드 후 serve
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="${SCRIPT_DIR}/frontend"
PID_FILE="${SCRIPT_DIR}/graph_rag_ui.pid"
LOG_FILE="${SCRIPT_DIR}/logs/graph_rag_ui.log"
UI_PORT=3016
API_PORT=8015

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

DAEMON_MODE=false
BUILD_MODE=false
for arg in "$@"; do
    case "$arg" in
        --daemon) DAEMON_MODE=true ;;
        --build)  BUILD_MODE=true ;;
    esac
done

log_info "=== Vector Graph RAG UI 시작 ==="

# ─── 사전 확인 ──────────────────────────────────────────────────────────────
if [ ! -d "${FRONTEND_DIR}/node_modules" ]; then
    log_warn "node_modules 없음. npm install 실행 중..."
    cd "${FRONTEND_DIR}" && npm install --prefer-offline 2>&1 | tail -5
fi

# 백엔드 서비스 확인
if ! curl -sf "http://localhost:${API_PORT}/health" &>/dev/null; then
    log_warn "백엔드 서비스(포트 ${API_PORT})가 응답하지 않습니다"
    log_warn "먼저 시작: ./start.sh --daemon"
fi

# 기존 UI 프로세스 종료
if [ -f "${PID_FILE}" ]; then
    OLD_PID=$(cat "${PID_FILE}")
    if kill -0 "${OLD_PID}" 2>/dev/null; then
        log_info "기존 UI 프로세스 종료 (PID: ${OLD_PID})"
        kill "${OLD_PID}" 2>/dev/null || true
    fi
    rm -f "${PID_FILE}"
fi

mkdir -p "${SCRIPT_DIR}/logs"

log_info "UI 포트  : ${UI_PORT}"
log_info "API 포트  : ${API_PORT} (프록시)"
log_info "접속 주소 : http://$(hostname -I | awk '{print $1}'):${UI_PORT}"

cd "${FRONTEND_DIR}"

if [ "${BUILD_MODE}" = true ]; then
    # ─── 프로덕션 빌드 ──────────────────────────────────────────────────────
    log_info "프로덕션 빌드 중..."
    VGRAG_API_PORT="${API_PORT}" npm run build 2>&1
    log_info "빌드 완료: ${FRONTEND_DIR}/dist/"

    # npx serve 로 정적 파일 서빙
    if command -v npx &>/dev/null; then
        if [ "${DAEMON_MODE}" = true ]; then
            nohup npx serve -s dist -l "${UI_PORT}" >> "${LOG_FILE}" 2>&1 &
            echo $! > "${PID_FILE}"
            log_info "정적 서버 시작 완료 (PID: $(cat "${PID_FILE}"))"
        else
            npx serve -s dist -l "${UI_PORT}"
        fi
    else
        log_warn "npx 없음. 빌드 파일 위치: ${FRONTEND_DIR}/dist/"
        log_warn "별도 웹서버로 서빙하세요 (nginx, python -m http.server 등)"
    fi
else
    # ─── 개발 서버 (Vite) ────────────────────────────────────────────────────
    if [ "${DAEMON_MODE}" = true ]; then
        VGRAG_API_PORT="${API_PORT}" nohup npm run dev >> "${LOG_FILE}" 2>&1 &
        echo $! > "${PID_FILE}"
        sleep 3
        if kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
            log_info "UI 개발 서버 시작 완료 (PID: $(cat "${PID_FILE}"))"
            log_info "접속: http://localhost:${UI_PORT}"
            log_info "로그: tail -f ${LOG_FILE}"
            log_info "중지: ./stop-ui.sh"
        else
            log_error "UI 시작 실패. 로그 확인: ${LOG_FILE}"
            exit 1
        fi
    else
        log_info "개발 모드 시작 (Ctrl+C 로 종료)"
        VGRAG_API_PORT="${API_PORT}" npm run dev
    fi
fi
