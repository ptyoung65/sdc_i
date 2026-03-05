#!/bin/bash

# Perplexity Search MCP Server Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo "🔍 Perplexity Search MCP Server"
echo "================================================================================"

# 사용법 출력
usage() {
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  --model MODEL       Perplexity 모델 (기본: sonar-pro)"
    echo "                      사용 가능: sonar, sonar-pro, sonar-reasoning, sonar-reasoning-pro"
    echo "  --max-tokens N      최대 응답 토큰 수 (기본: 1024)"
    echo "  --temperature N     응답 창의성 0.0~2.0 (기본: 0.2)"
    echo "  --recency PERIOD    검색 기간 필터 (기본: month)"
    echo "                      사용 가능: hour, day, week, month, year"
    echo "  --with-redis        Redis 컨테이너와 함께 실행 (캐싱 활성화)"
    echo "  --no-redis          Redis 없이 실행 (메모리 캐시만 사용, 기본값)"
    echo "  -d, --background    백그라운드 모드로 실행"
    echo "  --stop              서버 중지"
    echo "  -h, --help          도움말 출력"
    echo ""
    echo "예시:"
    echo "  $0                              # 기본 실행"
    echo "  $0 --model sonar                # sonar 모델로 실행"
    echo "  $0 --max-tokens 2048            # 토큰 수 변경"
    echo "  $0 --recency day                # 최근 1일 검색"
    echo "  $0 --with-redis -d              # Redis + 백그라운드"
    echo "  $0 --stop                       # 서버 중지"
    exit 0
}

# 옵션 파싱
USE_REDIS=false
BACKGROUND=false
STOP_SERVER=false
PERPLEXITY_MODEL=""
PERPLEXITY_MAX_TOKENS=""
PERPLEXITY_TEMPERATURE=""
PERPLEXITY_SEARCH_RECENCY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            PERPLEXITY_MODEL="$2"
            shift 2
            ;;
        --max-tokens)
            PERPLEXITY_MAX_TOKENS="$2"
            shift 2
            ;;
        --temperature)
            PERPLEXITY_TEMPERATURE="$2"
            shift 2
            ;;
        --recency)
            PERPLEXITY_SEARCH_RECENCY="$2"
            shift 2
            ;;
        --with-redis)
            USE_REDIS=true
            shift
            ;;
        --no-redis)
            USE_REDIS=false
            shift
            ;;
        -d|--background)
            BACKGROUND=true
            shift
            ;;
        --stop)
            STOP_SERVER=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "알 수 없는 옵션: $1"
            usage
            ;;
    esac
done

# 서버 중지
if [ "$STOP_SERVER" = true ]; then
    echo "서버 중지 중..."

    # Python 서버 중지
    if [ -f "$SCRIPT_DIR/server.pid" ]; then
        PID=$(cat "$SCRIPT_DIR/server.pid")
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo "✅ MCP 서버 중지됨 (PID: $PID)"
        fi
        rm -f "$SCRIPT_DIR/server.pid"
    fi

    # Redis 컨테이너 중지
    if podman ps --format "{{.Names}}" | grep -q "perplexity-redis"; then
        podman stop perplexity-redis
        echo "✅ Redis 컨테이너 중지됨"
    fi

    echo "✅ 완료"
    exit 0
fi

# 환경 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️  .env 파일이 없습니다."
    echo "   .env.example을 복사하여 API 키를 설정하세요:"
    echo "   cp .env.example .env"
    exit 1
else
    # 환경 변수 로드
    set -a
    source .env
    set +a
    echo "✅ .env 파일 로드 완료"
fi

# Redis 설정 덮어쓰기
export USE_REDIS=$USE_REDIS

# 명령줄 옵션으로 환경변수 덮어쓰기
if [ -n "$PERPLEXITY_MODEL" ]; then
    export PERPLEXITY_MODEL=$PERPLEXITY_MODEL
fi
if [ -n "$PERPLEXITY_MAX_TOKENS" ]; then
    export PERPLEXITY_MAX_TOKENS=$PERPLEXITY_MAX_TOKENS
fi
if [ -n "$PERPLEXITY_TEMPERATURE" ]; then
    export PERPLEXITY_TEMPERATURE=$PERPLEXITY_TEMPERATURE
fi
if [ -n "$PERPLEXITY_SEARCH_RECENCY" ]; then
    export PERPLEXITY_SEARCH_RECENCY=$PERPLEXITY_SEARCH_RECENCY
fi

PORT=${MCP_SERVER_PORT:-8200}

# 포트 확인
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  포트 $PORT 가 이미 사용 중입니다!"
    lsof -Pi :$PORT -sTCP:LISTEN
    echo ""
    read -p "   기존 프로세스를 종료하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
        sleep 1
    else
        exit 1
    fi
fi

# Python 의존성 확인
echo "📦 Python 의존성 확인..."
if ! python3 -c "import fastapi, uvicorn, httpx" 2>/dev/null; then
    echo "⚠️  필요한 Python 패키지가 설치되지 않았습니다."
    echo "   pip install -r requirements.txt"
    exit 1
fi
echo "✅ 의존성 확인 완료"

# Redis 컨테이너 시작 (필요시)
if [ "$USE_REDIS" = true ]; then
    echo ""
    echo "🗄️  Redis 컨테이너 시작..."

    # 기존 컨테이너 확인
    if podman ps --format "{{.Names}}" | grep -q "perplexity-redis"; then
        echo "   Redis 컨테이너가 이미 실행 중입니다."
    elif podman ps -a --format "{{.Names}}" | grep -q "perplexity-redis"; then
        # 중지된 컨테이너 시작
        podman start perplexity-redis
        echo "   기존 Redis 컨테이너 시작됨"
    else
        # 새 컨테이너 생성
        podman run -d \
            --name perplexity-redis \
            -p 6379:6379 \
            -v perplexity-redis-data:/data \
            redis:7-alpine \
            redis-server --appendonly yes
        echo "   새 Redis 컨테이너 생성됨"
    fi

    export REDIS_HOST=localhost
    export REDIS_PORT=6379
    sleep 2
    echo "✅ Redis 준비 완료 (localhost:6379)"
fi

# 설정 출력
echo ""
echo "📋 설정:"
echo "   Port: $PORT"
echo "   Model: ${PERPLEXITY_MODEL:-sonar-pro}"
echo "   Max Tokens: ${PERPLEXITY_MAX_TOKENS:-1024}"
echo "   Temperature: ${PERPLEXITY_TEMPERATURE:-0.2}"
echo "   Search Recency: ${PERPLEXITY_SEARCH_RECENCY:-month}"
echo "   Redis: $([ "$USE_REDIS" = true ] && echo "활성화 (localhost:6379)" || echo "비활성화 (메모리 캐시)")"
echo "   API Key: $([ -n "$PERPLEXITY_API_KEY" ] && echo "설정됨" || echo "미설정")"
echo ""

# 실행
if [ "$BACKGROUND" = true ]; then
    echo "🚀 백그라운드 모드로 시작합니다..."
    nohup python3 perplexity_mcp_server.py > /tmp/perplexity-mcp.log 2>&1 &
    PID=$!
    echo $PID > "$SCRIPT_DIR/server.pid"

    sleep 3
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo ""
        echo "✅ 서버 시작됨 (PID: $PID)"
        echo "   Health: http://localhost:$PORT/health"
        echo "   Models: http://localhost:$PORT/v1/models"
        echo "   로그: tail -f /tmp/perplexity-mcp.log"
        echo "   중지: $0 --stop"
    else
        echo "⚠️  헬스 체크 실패. 로그를 확인하세요."
        tail -20 /tmp/perplexity-mcp.log
    fi
else
    echo "🚀 포그라운드 모드로 시작합니다... (종료: Ctrl+C)"
    echo ""
    python3 perplexity_mcp_server.py
fi
