#!/bin/bash
# =============================================================================
# Vector Graph RAG 서비스 시작 스크립트
# =============================================================================
# 사용법:
#   ./start.sh            # 포그라운드 실행
#   ./start.sh --daemon   # 백그라운드 실행
#   ./start.sh --help     # 도움말
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="graph-rag-service"
PID_FILE="${SCRIPT_DIR}/graph_rag.pid"
LOG_FILE="${SCRIPT_DIR}/logs/graph_rag.log"
PYTHON_BIN="/usr/bin/python3.11"
SERVICE_SCRIPT="${SCRIPT_DIR}/graph_rag_service.py"
ENV_FILE="${SCRIPT_DIR}/.env"

# ─── .env 로드 ─────────────────────────────────────────────────────────────
if [ -f "${ENV_FILE}" ]; then
    # shellcheck disable=SC1090
    set -a; source "${ENV_FILE}"; set +a
fi

GRAPH_RAG_PORT="${GRAPH_RAG_PORT:-8015}"
GRAPH_RAG_HOST="${GRAPH_RAG_HOST:-0.0.0.0}"

# ─── 색상 출력 ─────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ─── 도움말 ─────────────────────────────────────────────────────────────────
usage() {
    echo "사용법: $0 [옵션]"
    echo "  --daemon    백그라운드(데몬) 모드로 실행"
    echo "  --help      이 도움말 출력"
    exit 0
}

DAEMON_MODE=false
for arg in "$@"; do
    case "$arg" in
        --daemon) DAEMON_MODE=true ;;
        --help|-h) usage ;;
    esac
done

# ─── 사전 검사 ──────────────────────────────────────────────────────────────
log_info "=== Vector Graph RAG 서비스 시작 ==="

# Python 3.11 확인
if ! command -v "${PYTHON_BIN}" &>/dev/null; then
    log_error "Python 3.11 이 없습니다: ${PYTHON_BIN}"
    log_error "테스트 서버 설치 방법: sudo dnf install python3.11"
    exit 1
fi

# vector-graph-rag 패키지 확인
if ! "${PYTHON_BIN}" -c "import vector_graph_rag" 2>/dev/null; then
    log_error "vector-graph-rag 패키지가 설치되지 않았습니다"
    log_error "설치 방법: ./install_offline.sh"
    exit 1
fi

# python-dotenv 확인
if ! "${PYTHON_BIN}" -c "import dotenv" 2>/dev/null; then
    log_warn "python-dotenv 미설치. pip3.11 install python-dotenv 실행"
    "${PYTHON_BIN}" -m pip install python-dotenv --quiet 2>/dev/null || true
fi

# 이미 실행 중인지 확인
if [ -f "${PID_FILE}" ]; then
    OLD_PID=$(cat "${PID_FILE}")
    if kill -0 "${OLD_PID}" 2>/dev/null; then
        log_warn "이미 실행 중입니다 (PID: ${OLD_PID})"
        log_warn "중지하려면: ./stop.sh"
        exit 0
    else
        rm -f "${PID_FILE}"
    fi
fi

# 포트 사용 중 확인
if ss -tlnp "sport = :${GRAPH_RAG_PORT}" 2>/dev/null | grep -q ":${GRAPH_RAG_PORT}"; then
    log_error "포트 ${GRAPH_RAG_PORT} 가 이미 사용 중입니다"
    log_error "lsof -i :${GRAPH_RAG_PORT} 로 프로세스 확인 후 종료하세요"
    exit 1
fi

# Milvus 연결 확인
MILVUS_HOST=$(echo "${VGRAG_MILVUS_URI:-http://192.168.122.85:19530}" | sed 's|http://||' | cut -d: -f1)
MILVUS_PORT=$(echo "${VGRAG_MILVUS_URI:-http://192.168.122.85:19530}" | sed 's|http://||' | cut -d: -f2)
if ! nc -z -w3 "${MILVUS_HOST}" "${MILVUS_PORT}" 2>/dev/null; then
    log_warn "Milvus 서버(${MILVUS_HOST}:${MILVUS_PORT}) 연결 불가 - 서비스는 시작되지만 기능이 제한될 수 있습니다"
fi

# HuggingFace 모델 캐시 확인
HF_CACHE="${HF_HUB_CACHE:-}"
if [ -n "${HF_CACHE}" ] && [ ! -d "${HF_CACHE}/models--BAAI--bge-m3" ]; then
    log_warn "BAAI/bge-m3 모델 캐시 없음: ${HF_CACHE}/models--BAAI--bge-m3"
    log_warn "첫 실행 시 모델 다운로드가 필요합니다 (에어갭 환경에서는 실패할 수 있음)"
fi

# 디렉토리 생성
mkdir -p "${SCRIPT_DIR}/logs" "${SCRIPT_DIR}/cache/llm" "${SCRIPT_DIR}/cache/ner"

# ─── 실행 ───────────────────────────────────────────────────────────────────
log_info "Milvus URI  : ${VGRAG_MILVUS_URI:-http://192.168.122.85:19530}"
log_info "LLM 모델    : ${VGRAG_LLM_MODEL:-gpt-4o}"
log_info "임베딩 모델  : ${VGRAG_EMBEDDING_MODEL:-BAAI/bge-m3}"
log_info "서비스 포트  : ${GRAPH_RAG_PORT}"
log_info "서비스 주소  : http://$(hostname -I | awk '{print $1}'):${GRAPH_RAG_PORT}"

if [ "${DAEMON_MODE}" = true ]; then
    log_info "백그라운드 모드로 시작합니다..."
    nohup "${PYTHON_BIN}" "${SERVICE_SCRIPT}" \
        >> "${LOG_FILE}" 2>&1 &
    echo $! > "${PID_FILE}"
    sleep 2
    if kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
        log_info "서비스 시작 완료 (PID: $(cat "${PID_FILE}"))"
        log_info "로그: tail -f ${LOG_FILE}"
        log_info "중지: ./stop.sh"
        log_info "상태: curl http://localhost:${GRAPH_RAG_PORT}/health"
    else
        log_error "서비스 시작 실패. 로그 확인: ${LOG_FILE}"
        exit 1
    fi
else
    log_info "포그라운드 모드 (Ctrl+C 로 종료)"
    exec "${PYTHON_BIN}" "${SERVICE_SCRIPT}"
fi
