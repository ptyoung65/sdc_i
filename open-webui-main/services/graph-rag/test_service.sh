#!/bin/bash
# =============================================================================
# Vector Graph RAG 서비스 기능 테스트 스크립트
# =============================================================================
# 사용법:
#   bash test_service.sh                          # localhost:8015 테스트
#   bash test_service.sh --host 192.168.122.178  # 원격 서버 테스트
#   bash test_service.sh --port 8015             # 포트 지정
# =============================================================================

set -uo pipefail

HOST="localhost"
PORT="8015"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host) HOST="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        *) shift ;;
    esac
done

BASE_URL="http://${HOST}:${PORT}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
PASS=0; FAIL=0

pass() { echo -e "${GREEN}[PASS]${NC} $*"; ((PASS++)); }
fail() { echo -e "${RED}[FAIL]${NC} $*"; ((FAIL++)); }
info() { echo -e "${YELLOW}[INFO]${NC} $*"; }

echo "=== Vector Graph RAG 서비스 테스트 ==="
echo "대상: ${BASE_URL}"
echo ""

# ─── 1. Health Check ─────────────────────────────────────────────────────────
info "1. 헬스 체크"
RESP=$(curl -sf "${BASE_URL}/health" 2>/dev/null) && {
    STATUS=$(echo "${RESP}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null || echo "?")
    if [ "${STATUS}" = "ok" ]; then
        pass "GET /health → status=ok"
        echo "       응답: ${RESP}" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read().replace('       응답: ',''))
    for k,v in d.items(): print(f'       {k}: {v}')
except: pass
" 2>/dev/null || true
    else
        fail "GET /health → 예상치 못한 응답: ${RESP}"
    fi
} || fail "GET /health → 연결 실패 (서비스가 실행 중인지 확인)"
echo ""

# ─── 2. Graphs List ──────────────────────────────────────────────────────────
info "2. 그래프 목록"
RESP=$(curl -sf "${BASE_URL}/graphs" 2>/dev/null) && {
    pass "GET /graphs → ${RESP}"
} || fail "GET /graphs → 실패"
echo ""

# ─── 3. Stats ────────────────────────────────────────────────────────────────
info "3. 그래프 통계"
RESP=$(curl -sf "${BASE_URL}/stats?graph_name=default" 2>/dev/null) && {
    pass "GET /stats → ${RESP}"
} || fail "GET /stats → 실패 (Milvus 연결 또는 컬렉션 문제일 수 있음)"
echo ""

# ─── 4. 문서 추가 ────────────────────────────────────────────────────────────
info "4. 테스트 문서 추가 (LLM 트리플렛 추출 포함 - 약 10~30초 소요)"
RESP=$(curl -sf -X POST "${BASE_URL}/documents" \
    -H "Content-Type: application/json" \
    -d '{
        "documents": [
            "아인슈타인은 상대성이론을 개발한 물리학자입니다.",
            "상대성이론은 공간과 시간에 대한 우리의 이해를 혁명적으로 바꾸었습니다.",
            "아인슈타인은 1921년 노벨 물리학상을 수상했습니다."
        ],
        "graph_name": "test"
    }' 2>/dev/null) && {
    ADDED=$(echo "${RESP}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('added_count','?'))" 2>/dev/null || echo "?")
    pass "POST /documents → 추가된 문서 수: ${ADDED}"
} || fail "POST /documents → 실패 (LLM 서버 연결 확인 필요)"
echo ""

# ─── 5. 질의응답 ─────────────────────────────────────────────────────────────
info "5. 그래프 RAG 질의응답"
RESP=$(curl -sf -X POST "${BASE_URL}/query" \
    -H "Content-Type: application/json" \
    -d '{
        "question": "아인슈타인이 개발한 것은 무엇인가요?",
        "graph_name": "test"
    }' 2>/dev/null) && {
    ANSWER=$(echo "${RESP}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('answer','?'))" 2>/dev/null || echo "?")
    if [ -n "${ANSWER}" ] && [ "${ANSWER}" != "?" ]; then
        pass "POST /query → 답변 생성 완료"
        echo "       답변: ${ANSWER}"
    else
        fail "POST /query → 답변 없음: ${RESP}"
    fi
} || fail "POST /query → 실패"
echo ""

# ─── 6. 컬렉션 초기화 (테스트 데이터 정리) ──────────────────────────────────
info "6. 테스트 컬렉션 정리"
RESP=$(curl -sf -X DELETE "${BASE_URL}/collection?graph_name=test" 2>/dev/null) && {
    pass "DELETE /collection?graph_name=test → ${RESP}"
} || fail "DELETE /collection → 실패"
echo ""

# ─── 결과 요약 ───────────────────────────────────────────────────────────────
echo "==============================="
echo "테스트 결과: PASS=${PASS}, FAIL=${FAIL}"
if [ "${FAIL}" -eq 0 ]; then
    echo -e "${GREEN}모든 테스트 통과!${NC}"
    exit 0
else
    echo -e "${RED}일부 테스트 실패. 위 오류를 확인하세요.${NC}"
    exit 1
fi
