#!/bin/bash
# =============================================================================
# Vector Graph RAG - 테스트 서버 전체 적용 스크립트
# =============================================================================
#
# 이 스크립트는 테스트 서버에서 vector-graph-rag 서비스를 처음부터 설정하는
# 모든 단계를 기록합니다. 단계별로 실행하거나 전체를 한 번에 실행할 수 있습니다.
#
# 적용 환경:
#   - 서버 OS: RHEL 9 / CentOS Stream 9
#   - 서버 IP: 192.168.122.178 (테스트) / 192.168.122.xxx (실제 서버)
#   - Milvus DB: 192.168.122.85:19530
#   - LLM 서버: http://192.168.0.14:8000/v1
#   - Python: 3.11
#   - 서비스 포트: 8015
#
# 사용법:
#   bash apply_to_test_server.sh [STEP]
#
#   STEP:
#     all          모든 단계 순서대로 실행 (기본값)
#     check        1단계: 환경 사전 확인
#     install      2단계: 패키지 설치
#     configure    3단계: 서비스 설정
#     start        4단계: 서비스 시작
#     verify       5단계: 동작 검증
#     ui           6단계: 프론트엔드 UI 설치 및 시작 (포트 3016)
#     systemd      7단계: systemd 서비스 등록 (부팅 자동 시작)
#
# 원복 방법:
#   git reset --hard c091da2   ← push 전 마지막 커밋으로 원복
#   git push --force origin feature/apply-default-model
# =============================================================================

set -uo pipefail

STEP="${1:-all}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ─── 서버 설정 (환경에 맞게 수정) ────────────────────────────────────────────
MILVUS_HOST="192.168.122.85"
MILVUS_PORT="19530"
LLM_HOST="192.168.0.14"
LLM_PORT="8000"
SERVICE_PORT="8015"
PYTHON_BIN="/usr/bin/python3.11"
SERVICE_USER="${USER:-chatpro}"

# bge-m3 모델 캐시 경로 (서버에서 Open WebUI 컨테이너가 사용하는 볼륨)
HF_MODEL_CACHE="/home/chatpro/.local/share/containers/storage/volumes/openwebui-data/_data/cache/embedding/models"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
log_error()   { echo -e "${RED}[✗]${NC} $*"; }
log_section() { echo -e "\n${BLUE}━━━ $* ━━━${NC}"; }

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: 환경 사전 확인
# ─────────────────────────────────────────────────────────────────────────────
step_check() {
    log_section "STEP 1: 환경 사전 확인"

    # Python 3.11 확인
    if command -v "${PYTHON_BIN}" &>/dev/null; then
        VER=$("${PYTHON_BIN}" --version 2>&1)
        log_info "Python 3.11 존재: ${VER}"
    else
        log_error "Python 3.11 없음. 설치 필요:"
        echo "    sudo dnf install python3.11 python3.11-pip   # RHEL/CentOS"
        echo "    sudo apt install python3.11 python3.11-pip   # Ubuntu/Debian"
    fi

    # vector-graph-rag 패키지 확인
    if "${PYTHON_BIN}" -c "import vector_graph_rag" 2>/dev/null; then
        VER=$("${PYTHON_BIN}" -c "import importlib.metadata; print(importlib.metadata.version('vector-graph-rag'))" 2>/dev/null)
        log_info "vector-graph-rag 설치됨: v${VER}"
    else
        log_warn "vector-graph-rag 미설치 → step install 실행 필요"
    fi

    # Milvus 연결 확인
    if nc -z -w3 "${MILVUS_HOST}" "${MILVUS_PORT}" 2>/dev/null; then
        log_info "Milvus 연결 가능: ${MILVUS_HOST}:${MILVUS_PORT}"
    else
        log_error "Milvus 연결 불가: ${MILVUS_HOST}:${MILVUS_PORT}"
        echo "    확인 사항: Milvus 컨테이너 실행 여부, 방화벽 설정"
    fi

    # LLM 서버 확인
    if curl -sf "http://${LLM_HOST}:${LLM_PORT}/v1/models" --max-time 5 &>/dev/null; then
        log_info "LLM 서버 응답: http://${LLM_HOST}:${LLM_PORT}/v1"
    else
        log_warn "LLM 서버 응답 없음: http://${LLM_HOST}:${LLM_PORT}/v1"
        echo "    (API 키 없이는 /v1/models 에서 401이 정상)"
    fi

    # HuggingFace bge-m3 모델 캐시 확인
    if [ -d "${HF_MODEL_CACHE}/models--BAAI--bge-m3" ]; then
        log_info "bge-m3 모델 캐시 존재: ${HF_MODEL_CACHE}"
    else
        log_warn "bge-m3 모델 캐시 없음: ${HF_MODEL_CACHE}"
        echo "    .env 의 HF_HUB_CACHE 경로를 실제 모델 위치로 수정하세요"
        # 대체 경로 탐색
        for ALT in "${HOME}/.cache/huggingface/hub" "/root/.cache/huggingface/hub"; do
            if [ -d "${ALT}/models--BAAI--bge-m3" ]; then
                log_info "대체 경로 발견: ${ALT}"
                echo "    .env 에서 HF_HUB_CACHE=${ALT} 으로 수정하세요"
                break
            fi
        done
    fi

    # 포트 사용 확인
    if ss -tlnp "sport = :${SERVICE_PORT}" 2>/dev/null | grep -q ":${SERVICE_PORT}"; then
        log_warn "포트 ${SERVICE_PORT} 이미 사용 중 - 기존 프로세스 확인 필요"
        lsof -i :"${SERVICE_PORT}" 2>/dev/null || true
    else
        log_info "포트 ${SERVICE_PORT} 사용 가능"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: 패키지 설치
# ─────────────────────────────────────────────────────────────────────────────
step_install() {
    log_section "STEP 2: 패키지 설치"

    CACHE_DIR="${SCRIPT_DIR}/wheel_cache"

    if "${PYTHON_BIN}" -c "import vector_graph_rag" 2>/dev/null; then
        log_info "vector-graph-rag 이미 설치됨. 건너뜁니다."
        return 0
    fi

    if [ -d "${CACHE_DIR}" ] && ls "${CACHE_DIR}"/*.whl 2>/dev/null | grep -q "vector"; then
        log_info "오프라인 캐시에서 설치: ${CACHE_DIR}"
        # 에어갭 오프라인 설치
        "${PYTHON_BIN}" -m pip install \
            --no-index \
            --find-links "${CACHE_DIR}" \
            "vector-graph-rag==0.1.3" \
            "fastapi>=0.100" \
            "uvicorn[standard]" \
            "python-dotenv"
    else
        log_warn "오프라인 캐시 없음"
        log_warn "온라인 설치를 시도합니다 (에어갭 환경에서는 실패)"
        log_warn "에어갭 환경에서는 먼저 인터넷 머신에서 download_packages.sh 를 실행하세요"
        echo ""
        echo "  # 인터넷 머신에서 실행:"
        echo "  bash ${SCRIPT_DIR}/download_packages.sh"
        echo "  # wheel_cache/ 를 테스트 서버로 복사 후 다시 실행"
        return 1
    fi

    log_info "패키지 설치 완료"
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: 서비스 설정
# ─────────────────────────────────────────────────────────────────────────────
step_configure() {
    log_section "STEP 3: 서비스 설정"

    ENV_FILE="${SCRIPT_DIR}/.env"

    if [ ! -f "${ENV_FILE}" ]; then
        log_error ".env 파일 없음: ${ENV_FILE}"
        return 1
    fi

    # HF_HUB_CACHE 자동 업데이트
    if [ -d "${HF_MODEL_CACHE}/models--BAAI--bge-m3" ]; then
        sed -i "s|^HF_HUB_CACHE=.*|HF_HUB_CACHE=${HF_MODEL_CACHE}|" "${ENV_FILE}"
        log_info "HF_HUB_CACHE 업데이트: ${HF_MODEL_CACHE}"
    else
        log_warn "bge-m3 모델 없음. .env 의 HF_HUB_CACHE 를 수동으로 설정하세요"
    fi

    # 캐시 디렉토리 생성
    mkdir -p "${SCRIPT_DIR}/logs" \
             "${SCRIPT_DIR}/cache/llm" \
             "${SCRIPT_DIR}/cache/ner"
    log_info "캐시 디렉토리 생성 완료"

    # 현재 .env 설정 출력
    log_info "현재 서비스 설정:"
    grep -E "^VGRAG_|^GRAPH_RAG_|^HF_HUB_CACHE|^TRANSFORMERS" "${ENV_FILE}" | \
        grep -v "API_KEY" | \
        sed 's/^/    /'

    log_info ".env 파일: ${ENV_FILE}"
    log_info "수정 필요 시: vi ${ENV_FILE}"
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: 서비스 시작
# ─────────────────────────────────────────────────────────────────────────────
step_start() {
    log_section "STEP 4: 서비스 시작"

    chmod +x "${SCRIPT_DIR}/start.sh" "${SCRIPT_DIR}/stop.sh"

    # 기존 프로세스 정리
    "${SCRIPT_DIR}/stop.sh" 2>/dev/null || true

    # 데몬 모드로 시작
    "${SCRIPT_DIR}/start.sh" --daemon

    # 시작 대기 (모델 로딩 포함, 최대 60초)
    log_info "서비스 초기화 대기 중 (최대 60초) ..."
    for i in $(seq 1 30); do
        sleep 2
        if curl -sf "http://localhost:${SERVICE_PORT}/health" &>/dev/null; then
            log_info "서비스 준비 완료 (${i}x2초 소요)"
            break
        fi
        if [ "${i}" -eq 30 ]; then
            log_error "서비스 시작 실패. 로그 확인:"
            echo "    tail -50 ${SCRIPT_DIR}/logs/graph_rag.log"
        fi
    done
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: 동작 검증
# ─────────────────────────────────────────────────────────────────────────────
step_verify() {
    log_section "STEP 5: 동작 검증"

    chmod +x "${SCRIPT_DIR}/test_service.sh"
    bash "${SCRIPT_DIR}/test_service.sh" || {
        log_error "테스트 실패. 로그 확인:"
        echo "    tail -100 ${SCRIPT_DIR}/logs/graph_rag.log"
        return 1
    }

    log_info ""
    log_info "서비스 API 주소:"
    HOST_IP=$(hostname -I | awk '{print $1}')
    echo "    Health:    curl http://${HOST_IP}:${SERVICE_PORT}/health"
    echo "    Stats:     curl http://${HOST_IP}:${SERVICE_PORT}/stats"
    echo "    API Docs:  http://${HOST_IP}:${SERVICE_PORT}/docs"
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: systemd 서비스 등록 (선택)
# ─────────────────────────────────────────────────────────────────────────────
step_systemd() {
    log_section "STEP 6: systemd 서비스 등록 (부팅 자동 시작)"

    SYSTEMD_FILE="/etc/systemd/system/vector-graph-rag.service"

    cat > /tmp/vector-graph-rag.service <<EOF
[Unit]
Description=Vector Graph RAG Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${SCRIPT_DIR}
EnvironmentFile=${SCRIPT_DIR}/.env
ExecStart=${PYTHON_BIN} ${SCRIPT_DIR}/graph_rag_service.py
ExecStop=/bin/kill -SIGTERM \$MAINPID
Restart=on-failure
RestartSec=10
StandardOutput=append:${SCRIPT_DIR}/logs/graph_rag.log
StandardError=append:${SCRIPT_DIR}/logs/graph_rag.log
SyslogIdentifier=vector-graph-rag

[Install]
WantedBy=multi-user.target
EOF

    if [ "${EUID:-$(id -u)}" -eq 0 ]; then
        cp /tmp/vector-graph-rag.service "${SYSTEMD_FILE}"
        systemctl daemon-reload
        systemctl enable vector-graph-rag
        systemctl start vector-graph-rag
        systemctl status vector-graph-rag --no-pager
        log_info "systemd 서비스 등록 완료"
        echo "    관리 명령어:"
        echo "    sudo systemctl start   vector-graph-rag"
        echo "    sudo systemctl stop    vector-graph-rag"
        echo "    sudo systemctl restart vector-graph-rag"
        echo "    sudo journalctl -u vector-graph-rag -f"
    else
        log_warn "systemd 등록은 root 권한이 필요합니다"
        log_info "다음 명령어로 수동 등록하세요:"
        echo "    sudo cp /tmp/vector-graph-rag.service ${SYSTEMD_FILE}"
        echo "    sudo systemctl daemon-reload"
        echo "    sudo systemctl enable --now vector-graph-rag"
        echo ""
        echo "--- 생성된 서비스 파일 내용 ---"
        cat /tmp/vector-graph-rag.service
        echo "-------------------------------"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────────────────────────────────────
echo "======================================================================="
echo " Vector Graph RAG 테스트 서버 적용 스크립트"
echo " 출처: https://github.com/zilliztech/vector-graph-rag"
echo " 서비스 포트: ${SERVICE_PORT} | Milvus: ${MILVUS_HOST}:${MILVUS_PORT}"
echo "======================================================================="
echo ""
echo "원복 방법 (문제 발생 시):"
echo "  git reset --hard c091da2"
echo "  git push --force origin feature/apply-default-model"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: 프론트엔드 UI 설치 및 시작
# ─────────────────────────────────────────────────────────────────────────────
step_ui() {
    log_section "STEP 6: 프론트엔드 UI (포트 3016)"

    FRONTEND_DIR="${SCRIPT_DIR}/frontend"

    if [ ! -d "${FRONTEND_DIR}" ]; then
        log_error "frontend/ 디렉토리 없음: ${FRONTEND_DIR}"
        log_error "git pull 또는 서비스 디렉토리 동기화 필요"
        return 1
    fi

    # Node.js 확인
    if ! command -v node &>/dev/null; then
        log_error "Node.js 없음. 설치 필요:"
        echo "    sudo dnf install nodejs npm   # RHEL/CentOS"
        echo "    sudo apt install nodejs npm   # Ubuntu/Debian"
        return 1
    fi
    log_info "Node.js: $(node --version), npm: $(npm --version)"

    # npm install
    if [ ! -d "${FRONTEND_DIR}/node_modules" ]; then
        log_info "npm 패키지 설치 중..."
        cd "${FRONTEND_DIR}" && npm install --prefer-offline 2>&1 | tail -5
        cd "${SCRIPT_DIR}"
    else
        log_info "node_modules 이미 존재 (건너뜀)"
    fi

    # UI 시작
    chmod +x "${SCRIPT_DIR}/start-ui.sh" "${SCRIPT_DIR}/stop-ui.sh"
    "${SCRIPT_DIR}/start-ui.sh" --daemon

    log_info ""
    log_info "UI 접속 주소:"
    HOST_IP=$(hostname -I | awk '{print $1}')
    echo "    http://${HOST_IP}:3016"
    echo ""
    echo "    ※ 그래프 RAG 사용 방법:"
    echo "    1. 우상단 [Import] 버튼 → 텍스트/URL/파일 업로드"
    echo "    2. 검색창에 질문 입력 → 그래프 시각화 및 답변 확인"
    echo "    3. 노드 클릭 → 연결된 관계/패시지 탐색"
}

case "${STEP}" in
    all)
        step_check
        step_install
        step_configure
        step_start
        step_verify
        step_ui
        echo ""
        log_info "=== 모든 단계 완료 ==="
        log_info "백엔드 API: http://$(hostname -I | awk '{print $1}'):8015"
        log_info "프론트엔드: http://$(hostname -I | awk '{print $1}'):3016"
        log_info "API 문서:   http://$(hostname -I | awk '{print $1}'):8015/docs"
        ;;
    check)     step_check ;;
    install)   step_install ;;
    configure) step_configure ;;
    start)     step_start ;;
    verify)    step_verify ;;
    ui)        step_ui ;;
    systemd)   step_systemd ;;
    *)
        echo "알 수 없는 STEP: ${STEP}"
        echo "사용법: $0 [all|check|install|configure|start|verify|ui|systemd]"
        exit 1
        ;;
esac
