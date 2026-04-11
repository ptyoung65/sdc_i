#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${SCRIPT_DIR}/graph_rag_ui.pid"
UI_PORT=3016

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

if [ -f "${PID_FILE}" ]; then
    PID=$(cat "${PID_FILE}")
    if kill -0 "${PID}" 2>/dev/null; then
        echo -e "${GREEN}[INFO]${NC}  UI 서버 종료 (PID: ${PID})"
        kill "${PID}" && sleep 1
        kill -9 "${PID}" 2>/dev/null || true
    fi
    rm -f "${PID_FILE}"
else
    PIDS=$(lsof -ti :"${UI_PORT}" 2>/dev/null || true)
    if [ -n "${PIDS}" ]; then
        echo -e "${GREEN}[INFO]${NC}  포트 ${UI_PORT} 프로세스 종료"
        echo "${PIDS}" | xargs -r kill 2>/dev/null || true
    else
        echo -e "${YELLOW}[WARN]${NC}  실행 중인 UI 서버 없음"
    fi
fi
