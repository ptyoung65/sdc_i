#!/bin/bash
# =============================================================================
# Vector Graph RAG 서비스 중지 스크립트
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${SCRIPT_DIR}/graph_rag.pid"
GRAPH_RAG_PORT="${GRAPH_RAG_PORT:-8015}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }

if [ -f "${PID_FILE}" ]; then
    PID=$(cat "${PID_FILE}")
    if kill -0 "${PID}" 2>/dev/null; then
        log_info "서비스 종료 중 (PID: ${PID}) ..."
        kill "${PID}"
        sleep 2
        if kill -0 "${PID}" 2>/dev/null; then
            log_warn "정상 종료 실패 - 강제 종료합니다"
            kill -9 "${PID}" 2>/dev/null || true
        fi
        log_info "서비스 종료 완료"
    else
        log_warn "프로세스가 이미 종료되어 있습니다 (PID: ${PID})"
    fi
    rm -f "${PID_FILE}"
else
    # PID 파일 없을 때 포트로 프로세스 찾아 종료
    PIDS=$(lsof -ti :"${GRAPH_RAG_PORT}" 2>/dev/null || true)
    if [ -n "${PIDS}" ]; then
        log_info "포트 ${GRAPH_RAG_PORT} 프로세스 종료: ${PIDS}"
        echo "${PIDS}" | xargs -r kill 2>/dev/null || true
        log_info "종료 완료"
    else
        log_warn "실행 중인 서비스가 없습니다"
    fi
fi
