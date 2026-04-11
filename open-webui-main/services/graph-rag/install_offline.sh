#!/bin/bash
# =============================================================================
# [테스트 서버에서 실행] 오프라인 패키지 설치 스크립트
# =============================================================================
# 전제 조건:
#   - download_packages.sh 를 인터넷 머신에서 실행한 후
#     wheel_cache/ 디렉토리가 이 디렉토리에 존재해야 합니다
#   - Python 3.11 이 설치되어 있어야 합니다
#
# 사용법:
#   bash install_offline.sh [--model-dir /path/to/bge-m3]
#
# 설치 항목:
#   1. vector-graph-rag 및 모든 의존 패키지 (오프라인 캐시에서)
#   2. python-dotenv (서비스 .env 파일 읽기용)
#   3. HuggingFace bge-m3 모델 경로 설정
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_DIR="${SCRIPT_DIR}/wheel_cache"
PYTHON_BIN="/usr/bin/python3.11"
MODEL_DIR=""  # 선택적: 사용자 지정 모델 경로

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model-dir) MODEL_DIR="$2"; shift 2 ;;
        --python) PYTHON_BIN="$2"; shift 2 ;;
        *) shift ;;
    esac
done

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

log_info "=== Vector Graph RAG 오프라인 설치 ==="

# ─── 사전 검사 ──────────────────────────────────────────────────────────────
if ! command -v "${PYTHON_BIN}" &>/dev/null; then
    log_error "Python 3.11 없음: ${PYTHON_BIN}"
    log_error "설치: sudo dnf install python3.11 python3.11-pip   # RHEL/CentOS"
    log_error "설치: sudo apt install python3.11 python3.11-pip   # Ubuntu/Debian"
    exit 1
fi

PYTHON_VER=$("${PYTHON_BIN}" --version 2>&1)
log_info "Python 버전: ${PYTHON_VER}"

# ─── 이미 설치되어 있는지 확인 ──────────────────────────────────────────────
if "${PYTHON_BIN}" -c "import vector_graph_rag" 2>/dev/null; then
    INSTALLED_VER=$("${PYTHON_BIN}" -c "import importlib.metadata; print(importlib.metadata.version('vector-graph-rag'))" 2>/dev/null || echo "unknown")
    log_info "vector-graph-rag ${INSTALLED_VER} 이미 설치됨"
    log_warn "재설치하려면: ${PYTHON_BIN} -m pip install --force-reinstall vector-graph-rag"
fi

# ─── wheel 캐시 확인 ────────────────────────────────────────────────────────
if [ -d "${CACHE_DIR}" ] && ls "${CACHE_DIR}"/*.whl 2>/dev/null | grep -q vector.graph.rag; then
    log_info "wheel 캐시 발견: ${CACHE_DIR}"
    WHEEL_COUNT=$(ls "${CACHE_DIR}"/*.whl 2>/dev/null | wc -l)
    log_info "wheel 파일 수: ${WHEEL_COUNT}"
    INSTALL_CMD="${PYTHON_BIN} -m pip install --no-index --find-links ${CACHE_DIR}"
else
    log_warn "wheel 캐시 없음. 온라인 설치를 시도합니다..."
    log_warn "(에어갭 환경에서는 실패합니다. download_packages.sh 를 먼저 실행하세요)"
    INSTALL_CMD="${PYTHON_BIN} -m pip install"
fi

# ─── 패키지 설치 ────────────────────────────────────────────────────────────
log_info "패키지 설치 중..."
${INSTALL_CMD} \
    "vector-graph-rag==0.1.3" \
    "fastapi>=0.100" \
    "uvicorn[standard]" \
    "python-dotenv" \
    2>&1 | grep -E "Successfully|already|error|ERROR" || true

# ─── 설치 확인 ──────────────────────────────────────────────────────────────
log_info "설치 확인 중..."
PACKAGES=(
    "vector_graph_rag"
    "pymilvus"
    "openai"
    "fastapi"
    "uvicorn"
    "torch"
    "transformers"
    "sentence_transformers"
    "langchain_core"
    "pydantic"
    "dotenv"
)

ALL_OK=true
for pkg in "${PACKAGES[@]}"; do
    if "${PYTHON_BIN}" -c "import ${pkg}" 2>/dev/null; then
        log_info "  ✓ ${pkg}"
    else
        log_error "  ✗ ${pkg} - 설치 필요"
        ALL_OK=false
    fi
done

if [ "${ALL_OK}" = false ]; then
    log_error "일부 패키지 설치 실패. wheel_cache/ 를 확인하세요."
    exit 1
fi

# ─── HuggingFace 모델 경로 설정 ─────────────────────────────────────────────
log_info ""
log_info "=== HuggingFace bge-m3 모델 경로 안내 ==="

# 현재 서버의 모델 캐시 위치 자동 감지
POSSIBLE_PATHS=(
    "/home/chatpro/.local/share/containers/storage/volumes/openwebui-data/_data/cache/embedding/models"
    "${HOME}/.cache/huggingface/hub"
    "/app/embeddings/models"
)

FOUND_PATH=""
for p in "${POSSIBLE_PATHS[@]}"; do
    if [ -d "${p}/models--BAAI--bge-m3" ]; then
        FOUND_PATH="${p}"
        break
    fi
done

if [ -n "${FOUND_PATH}" ]; then
    log_info "bge-m3 모델 발견: ${FOUND_PATH}"
    log_info ".env 파일의 HF_HUB_CACHE 가 올바르게 설정되어 있습니다:"
    grep -n "HF_HUB_CACHE" "${SCRIPT_DIR}/.env" 2>/dev/null || true
elif [ -n "${MODEL_DIR}" ] && [ -d "${MODEL_DIR}" ]; then
    log_info "사용자 지정 모델 경로: ${MODEL_DIR}"
    # .env 업데이트
    if grep -q "^HF_HUB_CACHE=" "${SCRIPT_DIR}/.env" 2>/dev/null; then
        sed -i "s|^HF_HUB_CACHE=.*|HF_HUB_CACHE=${MODEL_DIR}|" "${SCRIPT_DIR}/.env"
    else
        echo "HF_HUB_CACHE=${MODEL_DIR}" >> "${SCRIPT_DIR}/.env"
    fi
    log_info ".env HF_HUB_CACHE 업데이트 완료: ${MODEL_DIR}"
else
    log_warn "bge-m3 모델 캐시를 찾을 수 없습니다"
    log_warn "다음 중 하나를 실행하세요:"
    log_warn "  1. .env 의 HF_HUB_CACHE 를 모델이 있는 경로로 수정"
    log_warn "  2. download_packages.sh 로 다운로드한 model_cache/ 를 지정:"
    log_warn "     bash install_offline.sh --model-dir /path/to/model_cache/bge-m3"
    log_warn "  3. TRANSFORMERS_OFFLINE=0 으로 변경 후 온라인 다운로드 허용"
fi

# ─── .env 수정 안내 ─────────────────────────────────────────────────────────
log_info ""
log_info "=== 테스트 서버 설정 확인 ==="
log_info ".env 파일에서 다음 항목을 테스트 서버 환경에 맞게 수정하세요:"
log_info ""
log_info "  VGRAG_MILVUS_URI=http://192.168.122.85:19530    ← Milvus 서버 IP"
log_info "  VGRAG_OPENAI_BASE_URL=http://192.168.0.14:8000/v1  ← LLM 서버 IP"
log_info "  HF_HUB_CACHE=/path/to/bge-m3-parent-dir        ← 모델 캐시 경로"
log_info ""
log_info "=== 설치 완료 ==="
log_info "서비스 시작: cd ${SCRIPT_DIR} && ./start.sh --daemon"
log_info "상태 확인:   curl http://localhost:8015/health"
