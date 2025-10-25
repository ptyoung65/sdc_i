#!/bin/bash

# External LLM MCP Server Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=" * 80
echo "🚀 External LLM MCP Server"
echo "="* 80

# 환경 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️  .env 파일이 없습니다."
    echo "   .env.example을 복사하여 API 키를 설정하세요:"
    echo "   cp .env.example .env"
    echo "   vi .env  # API 키 입력"
    echo ""
    echo "   또는 API 키 없이 계속하려면 Enter를 누르세요 (도구 호출 시 파라미터로 전달)"
    read -p "   계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    # 환경 변수 로드
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ .env 파일 로드 완료"
fi

# 포트 확인
PORT=${MCP_SERVER_PORT:-8100}
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  포트 $PORT 가 이미 사용 중입니다!"
    echo "   실행 중인 프로세스:"
    lsof -Pi :$PORT -sTCP:LISTEN
    echo ""
    read -p "   기존 프로세스를 종료하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   프로세스 종료 중..."
        lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
        echo "   ✅ 종료 완료"
        sleep 1
    else
        echo "   ❌ 시작 취소"
        exit 1
    fi
fi

# Python 의존성 확인
echo "📦 Python 의존성 확인..."
if ! python3 -c "import fastapi, uvicorn, httpx" 2>/dev/null; then
    echo "⚠️  필요한 Python 패키지가 설치되지 않았습니다."
    echo "   다음 명령으로 설치하세요:"
    echo "   pip install fastapi uvicorn httpx pydantic"
    exit 1
fi
echo "✅ 의존성 확인 완료"

# 백그라운드 실행 여부
if [ "$1" == "--background" ] || [ "$1" == "-d" ]; then
    echo ""
    echo "🚀 백그라운드 모드로 시작합니다..."
    echo ""
    nohup python3 external_llm_mcp_server.py > /tmp/external-llm-mcp.log 2>&1 &
    PID=$!
    echo "✅ 서버 시작됨 (PID: $PID)"
    echo "   포트: $PORT"
    echo "   로그: tail -f /tmp/external-llm-mcp.log"
    echo "   중지: kill $PID"
    echo ""

    # PID 저장
    echo $PID > "$SCRIPT_DIR/server.pid"

    # 헬스 체크
    sleep 3
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo "✅ MCP 서버 정상 작동 중"
        echo "   Health: http://localhost:$PORT/health"
        echo "   Endpoint: http://localhost:$PORT/mcp"
        echo ""
        echo "📝 Open WebUI 등록 정보:"
        echo "   URL: http://host.containers.internal:$PORT/mcp"
        echo "   Type: mcp"
        echo "   Auth: none"
    else
        echo "⚠️  헬스 체크 실패. 로그를 확인하세요."
        echo "   로그: tail -f /tmp/external-llm-mcp.log"
    fi
else
    echo ""
    echo "🚀 포그라운드 모드로 시작합니다..."
    echo "   (종료: Ctrl+C)"
    echo ""
    python3 external_llm_mcp_server.py
fi
