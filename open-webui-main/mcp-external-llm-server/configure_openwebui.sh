#!/bin/bash

# Open WebUI MCP Server Configuration Script
# Local 및 Remote MCP 서버 등록을 자동화합니다.

set -e

echo "================================================================================"
echo "🔧 Open WebUI MCP Server Configuration"
echo "================================================================================"
echo ""

# 설정
OPENWEBUI_URL="${OPENWEBUI_URL:-http://localhost:3000}"
MCP_SERVER_TYPE="${1:-local}"  # local 또는 remote
MCP_SERVER_HOST="${2}"
MCP_SERVER_PORT="${3:-8100}"

# 사용법
if [ "$MCP_SERVER_TYPE" != "local" ] && [ "$MCP_SERVER_TYPE" != "remote" ]; then
    echo "사용법: $0 <타입> [서버_IP] [포트]"
    echo ""
    echo "타입:"
    echo "  local  - 로컬 MCP 서버 등록 (기본값)"
    echo "  remote - 원격 MCP 서버 등록"
    echo ""
    echo "예시:"
    echo "  $0 local                          # 로컬 서버 (localhost:8100)"
    echo "  $0 remote 192.168.1.100           # 원격 서버 (192.168.1.100:8100)"
    echo "  $0 remote 192.168.1.100 8200      # 원격 서버 (사용자 지정 포트)"
    echo ""
    exit 1
fi

# MCP 서버 URL 결정
if [ "$MCP_SERVER_TYPE" == "local" ]; then
    # 로컬: Podman 컨테이너에서 호스트 접근
    MCP_URL="http://host.containers.internal:${MCP_SERVER_PORT}/mcp"
    MCP_DESCRIPTION="Local External LLM Server (ChatGPT, Perplexity)"
    TEST_URL="http://localhost:${MCP_SERVER_PORT}/health"
else
    # 원격: 원격 서버 IP 직접 접근
    if [ -z "$MCP_SERVER_HOST" ]; then
        echo "❌ 원격 서버 IP가 필요합니다."
        echo "   사용법: $0 remote <서버_IP>"
        exit 1
    fi
    MCP_URL="http://${MCP_SERVER_HOST}:${MCP_SERVER_PORT}/mcp"
    MCP_DESCRIPTION="Remote External LLM Server at $MCP_SERVER_HOST (ChatGPT, Perplexity)"
    TEST_URL="http://${MCP_SERVER_HOST}:${MCP_SERVER_PORT}/health"
fi

echo "📋 등록 정보:"
echo "   타입: $MCP_SERVER_TYPE"
echo "   MCP URL: $MCP_URL"
echo "   설명: $MCP_DESCRIPTION"
echo ""

# 1. MCP 서버 연결 테스트
echo "🔍 MCP 서버 연결 테스트 중..."

if curl -s --connect-timeout 5 "$TEST_URL" > /dev/null 2>&1; then
    echo "   ✅ MCP 서버 정상 응답"
    HEALTH_INFO=$(curl -s "$TEST_URL")
    echo "   $HEALTH_INFO" | python3 -m json.tool 2>/dev/null || echo "   $HEALTH_INFO"
else
    echo "   ❌ MCP 서버 연결 실패: $TEST_URL"
    echo ""
    echo "문제 해결:"
    if [ "$MCP_SERVER_TYPE" == "local" ]; then
        echo "   1. MCP 서버 실행 확인: ps aux | grep external_llm_mcp_server"
        echo "   2. 포트 확인: lsof -i :${MCP_SERVER_PORT}"
        echo "   3. 서버 시작: cd mcp-external-llm-server && ./start_server.sh --background"
    else
        echo "   1. 원격 서버에서 서비스 확인: ssh $MCP_SERVER_HOST 'systemctl status external-llm-mcp'"
        echo "   2. 방화벽 확인: ssh $MCP_SERVER_HOST 'firewall-cmd --list-ports'"
        echo "   3. 네트워크 연결: ping $MCP_SERVER_HOST"
    fi
    exit 1
fi

echo ""

# 2. Open WebUI 연결 테스트
echo "🔍 Open WebUI 연결 테스트 중..."

if curl -s --connect-timeout 5 "$OPENWEBUI_URL" > /dev/null 2>&1; then
    echo "   ✅ Open WebUI 정상 응답"
else
    echo "   ❌ Open WebUI 연결 실패: $OPENWEBUI_URL"
    echo ""
    echo "문제 해결:"
    echo "   1. Open WebUI 실행 확인: podman ps | grep open-webui"
    echo "   2. 포트 확인: curl http://localhost:3000"
    exit 1
fi

echo ""

# 3. 등록 정보 생성
echo "📝 MCP 서버 등록 정보 생성 중..."

cat > /tmp/mcp_server_config.json <<EOF
{
  "url": "$MCP_URL",
  "type": "mcp",
  "auth_type": "none",
  "path": "/mcp",
  "config": {
    "name": "External LLM Server ($MCP_SERVER_TYPE)",
    "description": "$MCP_DESCRIPTION"
  }
}
EOF

echo "   ✅ 설정 파일 생성 완료: /tmp/mcp_server_config.json"
echo ""

# 4. 수동 등록 안내
echo "================================================================================"
echo "✅ 준비 완료! 다음 단계를 진행하세요:"
echo "================================================================================"
echo ""
echo "🌐 웹 브라우저에서 Open WebUI 설정:"
echo ""
echo "1. 브라우저에서 Open WebUI 접속:"
echo "   $OPENWEBUI_URL"
echo ""
echo "2. 로그인 후 설정 메뉴 진입:"
echo "   Settings (⚙️) → Workspace → Tools → Tool Servers"
echo ""
echo "3. 'Add' 버튼 클릭 후 다음 정보 입력:"
echo ""
echo "   ┌─────────────────────────────────────────────────────────┐"
echo "   │ Server URL:   $MCP_URL"
echo "   │ Server Type:  mcp"
echo "   │ Auth Type:    none"
echo "   │ Name:         External LLM Server ($MCP_SERVER_TYPE)"
echo "   │ Description:  $MCP_DESCRIPTION"
echo "   └─────────────────────────────────────────────────────────┘"
echo ""
echo "4. 'Verify' 버튼 클릭하여 연결 테스트"
echo ""
echo "5. 'Save' 버튼 클릭하여 저장"
echo ""
echo "================================================================================"
echo ""
echo "🧪 등록 후 테스트:"
echo ""
echo "   Open WebUI 채팅에서 다음과 같이 테스트:"
echo ""
echo "   사용자: ChatGPT를 통해 \"인공지능이란?\" 질문해줘"
echo "   AI: (query_chatgpt 도구 사용) → ChatGPT 응답"
echo ""
echo "   사용자: Perplexity로 \"최신 AI 뉴스\" 검색해줘"
echo "   AI: (query_perplexity 도구 사용) → 웹 검색 결과 + 출처"
echo ""
echo "================================================================================"
echo ""
echo "📊 등록 정보 요약:"
cat /tmp/mcp_server_config.json | python3 -m json.tool
echo ""
echo "================================================================================"
