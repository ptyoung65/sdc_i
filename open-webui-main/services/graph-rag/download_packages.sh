#!/bin/bash
# =============================================================================
# [인터넷 연결 환경에서 실행] 패키지 다운로드 스크립트
# =============================================================================
# 목적: 에어갭(오프라인) 테스트 서버에 패키지를 전달하기 위해
#       인터넷이 연결된 머신에서 먼저 실행하여 wheel 파일을 다운로드합니다.
#
# 사용법:
#   1. 인터넷 연결 머신에서: bash download_packages.sh
#   2. 생성된 wheel_cache/ 디렉토리를 테스트 서버로 복사
#   3. 테스트 서버에서: bash install_offline.sh
#
# 주의: RHEL/CentOS 9 x86_64 + Python 3.11 기준으로 다운로드됩니다
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_DIR="${SCRIPT_DIR}/wheel_cache"
PYTHON_BIN="${1:-python3.11}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_info() { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }

log_info "=== 오프라인 설치용 패키지 다운로드 ==="
log_info "Python: ${PYTHON_BIN}"
log_info "저장 위치: ${CACHE_DIR}"

mkdir -p "${CACHE_DIR}"

# ─── 핵심 패키지 다운로드 ────────────────────────────────────────────────────
log_info "핵심 패키지 다운로드 중..."
"${PYTHON_BIN}" -m pip download \
    --dest "${CACHE_DIR}" \
    --platform manylinux2014_x86_64 \
    --python-version 311 \
    --only-binary :all: \
    "vector-graph-rag==0.1.3" \
    "pymilvus>=2.4.4" \
    "openai>=1.0.0" \
    "fastapi>=0.100" \
    "uvicorn[standard]" \
    "langchain-core>=0.3" \
    "pydantic>=2.0" \
    "pydantic-settings" \
    "tenacity" \
    "tqdm" \
    "numpy" \
    "sentence-transformers" \
    "transformers" \
    "python-dotenv" \
    2>&1 | tail -5

# ─── torch (CPU 버전, 크기가 커서 별도) ────────────────────────────────────
log_info "PyTorch (CPU) 다운로드 중 ... (약 800MB, 시간이 걸릴 수 있습니다)"
"${PYTHON_BIN}" -m pip download \
    --dest "${CACHE_DIR}" \
    --platform manylinux2014_x86_64 \
    --python-version 311 \
    --only-binary :all: \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    "torch" \
    2>&1 | tail -5

# ─── HuggingFace BAAI/bge-m3 모델 다운로드 (선택) ───────────────────────────
MODEL_CACHE_DIR="${SCRIPT_DIR}/model_cache"
if "${PYTHON_BIN}" -c "from huggingface_hub import snapshot_download" 2>/dev/null; then
    log_info "BAAI/bge-m3 모델 다운로드 중 ... (약 2.3GB)"
    mkdir -p "${MODEL_CACHE_DIR}"
    "${PYTHON_BIN}" - <<'EOF'
import os, sys
from huggingface_hub import snapshot_download
model_dir = os.environ.get("MODEL_CACHE_DIR", "./model_cache")
snapshot_download(
    repo_id="BAAI/bge-m3",
    local_dir=model_dir + "/bge-m3",
    ignore_patterns=["*.onnx", "*.ot", "flax*", "tf_*", "rust_*"],
)
print(f"모델 저장 완료: {model_dir}/bge-m3")
EOF
else
    log_warn "huggingface_hub 미설치 - 모델은 수동으로 다운로드하세요"
    log_warn "huggingface-cli download BAAI/bge-m3 --local-dir ${MODEL_CACHE_DIR}/bge-m3"
fi

# ─── 결과 확인 ──────────────────────────────────────────────────────────────
WHEEL_COUNT=$(ls "${CACHE_DIR}"/*.whl 2>/dev/null | wc -l)
log_info "=== 다운로드 완료 ==="
log_info "wheel 파일 수: ${WHEEL_COUNT}"
log_info "다운로드 위치: ${CACHE_DIR}"
log_info ""
log_info "다음 단계: wheel_cache/ 와 model_cache/ 를 테스트 서버로 복사 후"
log_info "           install_offline.sh 실행"
log_info ""
log_info "복사 명령 예시:"
log_info "  rsync -av ${SCRIPT_DIR}/wheel_cache/ user@test-server:/home/chatpro/open-webui-main/services/graph-rag/wheel_cache/"
log_info "  rsync -av ${SCRIPT_DIR}/model_cache/ user@test-server:/path/to/model_cache/"
