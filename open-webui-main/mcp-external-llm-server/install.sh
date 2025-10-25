#!/bin/bash

# External LLM MCP Server - Standalone Installation Script
# 이 스크립트는 다른 서버에서도 독립적으로 실행 가능합니다.

set -e

echo "================================================================================"
echo "🚀 External LLM MCP Server - Standalone Installation"
echo "================================================================================"
echo ""

# 설치 디렉토리
INSTALL_DIR="${INSTALL_DIR:-/opt/external-llm-mcp-server}"
SERVICE_USER="${SERVICE_USER:-mcp}"
SERVICE_PORT="${SERVICE_PORT:-8100}"

echo "📋 설치 정보:"
echo "   설치 경로: $INSTALL_DIR"
echo "   서비스 사용자: $SERVICE_USER"
echo "   서비스 포트: $SERVICE_PORT"
echo ""

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then
    echo "❌ 이 스크립트는 root 권한이 필요합니다."
    echo "   sudo ./install.sh 로 실행하세요."
    exit 1
fi

# 1. 시스템 패키지 확인
echo "📦 시스템 패키지 확인 중..."

# Python 3.9+ 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3가 설치되지 않았습니다."
    echo "   CentOS/RHEL: sudo yum install python3"
    echo "   Ubuntu/Debian: sudo apt-get install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}' | cut -d'.' -f1,2)
echo "   ✅ Python $PYTHON_VERSION 발견"

# pip 확인
if ! command -v pip3 &> /dev/null; then
    echo "⚠️  pip3이 설치되지 않았습니다. 설치 중..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3
fi
echo "   ✅ pip3 설치됨"

# 2. 서비스 사용자 생성
echo ""
echo "👤 서비스 사용자 생성 중..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$INSTALL_DIR" "$SERVICE_USER"
    echo "   ✅ 사용자 '$SERVICE_USER' 생성 완료"
else
    echo "   ℹ️  사용자 '$SERVICE_USER' 이미 존재"
fi

# 3. 설치 디렉토리 생성
echo ""
echo "📁 설치 디렉토리 생성 중..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/logs"

# 4. 애플리케이션 파일 복사
echo ""
echo "📋 애플리케이션 파일 복사 중..."

# 현재 스크립트 위치
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 메인 Python 파일 복사
cp "$SCRIPT_DIR/external_llm_mcp_server.py" "$INSTALL_DIR/" || {
    echo "❌ 파일 복사 실패. 현재 디렉토리에 external_llm_mcp_server.py가 있는지 확인하세요."
    exit 1
}

# .env 파일 복사 (있으면)
if [ -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env" "$INSTALL_DIR/"
    echo "   ✅ .env 파일 복사 완료"
elif [ -f "$SCRIPT_DIR/.env.example" ]; then
    cp "$SCRIPT_DIR/.env.example" "$INSTALL_DIR/.env"
    echo "   ℹ️  .env.example → .env 복사 (API 키 설정 필요)"
else
    # 기본 .env 생성
    cat > "$INSTALL_DIR/.env" <<EOF
# External LLM MCP Server Configuration
OPENAI_API_KEY=
PERPLEXITY_API_KEY=
MCP_SERVER_PORT=$SERVICE_PORT
MCP_SERVER_HOST=0.0.0.0
LOG_LEVEL=INFO
EOF
    echo "   ✅ 기본 .env 파일 생성 (API 키 설정 필요)"
fi

# 5. Virtual Environment 생성
echo ""
echo "🐍 Python Virtual Environment 생성 중..."
python3 -m venv "$INSTALL_DIR/venv"
echo "   ✅ Virtual Environment 생성 완료"

# 6. Python 의존성 설치
echo ""
echo "📚 Python 의존성 설치 중..."

# 오프라인 환경 체크
if ping -c 1 8.8.8.8 &> /dev/null; then
    echo "   🌐 온라인 모드: PyPI에서 패키지 설치"
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
    "$INSTALL_DIR/venv/bin/pip" install fastapi uvicorn httpx pydantic python-dotenv
else
    echo "   📦 오프라인 모드: 로컬 캐시 확인"
    if [ -d "$SCRIPT_DIR/offline-packages" ]; then
        "$INSTALL_DIR/venv/bin/pip" install --no-index --find-links="$SCRIPT_DIR/offline-packages" \
            fastapi uvicorn httpx pydantic python-dotenv
    else
        echo "   ⚠️  오프라인 패키지가 없습니다."
        echo "   온라인 서버에서 다음 명령으로 패키지를 다운로드하세요:"
        echo "   pip download -d offline-packages fastapi uvicorn httpx pydantic python-dotenv"
        exit 1
    fi
fi

echo "   ✅ 의존성 설치 완료"

# 7. 권한 설정
echo ""
echo "🔐 권한 설정 중..."
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/external_llm_mcp_server.py"
echo "   ✅ 권한 설정 완료"

# 8. Systemd 서비스 파일 생성
echo ""
echo "⚙️  Systemd 서비스 설정 중..."

cat > /etc/systemd/system/external-llm-mcp.service <<EOF
[Unit]
Description=External LLM MCP Server
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/external_llm_mcp_server.py
Restart=on-failure
RestartSec=5s
StandardOutput=append:$INSTALL_DIR/logs/server.log
StandardError=append:$INSTALL_DIR/logs/error.log

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR/logs

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "   ✅ Systemd 서비스 생성 완료"

# 9. 방화벽 설정
echo ""
echo "🔥 방화벽 설정 중..."

if command -v firewall-cmd &> /dev/null; then
    # CentOS/RHEL firewalld
    firewall-cmd --permanent --add-port=${SERVICE_PORT}/tcp
    firewall-cmd --reload
    echo "   ✅ Firewalld 포트 $SERVICE_PORT 개방 완료"
elif command -v ufw &> /dev/null; then
    # Ubuntu UFW
    ufw allow ${SERVICE_PORT}/tcp
    echo "   ✅ UFW 포트 $SERVICE_PORT 개방 완료"
else
    echo "   ⚠️  방화벽 도구를 찾을 수 없습니다. 수동으로 포트를 개방하세요."
    echo "   포트: $SERVICE_PORT/tcp"
fi

# 10. 서비스 시작
echo ""
echo "🚀 서비스 시작 중..."

systemctl enable external-llm-mcp.service
systemctl start external-llm-mcp.service

sleep 3

# 헬스 체크
if systemctl is-active --quiet external-llm-mcp.service; then
    echo "   ✅ 서비스 시작 성공"

    # 로컬 헬스 체크
    if curl -s http://localhost:${SERVICE_PORT}/health > /dev/null 2>&1; then
        echo "   ✅ 헬스 체크 성공"
    else
        echo "   ⚠️  헬스 체크 실패 (서비스는 실행 중)"
    fi
else
    echo "   ❌ 서비스 시작 실패"
    echo "   로그 확인: journalctl -u external-llm-mcp.service -n 50"
    exit 1
fi

# 11. 서버 정보 출력
echo ""
echo "================================================================================"
echo "✅ 설치 완료!"
echo "================================================================================"
echo ""
echo "📋 서버 정보:"
echo "   설치 경로: $INSTALL_DIR"
echo "   서비스 이름: external-llm-mcp.service"
echo "   포트: $SERVICE_PORT"
echo ""

# 서버 IP 주소 자동 감지
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "🌐 접속 URL:"
echo "   로컬: http://localhost:${SERVICE_PORT}/mcp"
echo "   원격: http://${SERVER_IP}:${SERVICE_PORT}/mcp"
echo ""

echo "📝 Open WebUI 설정:"
echo "   - Local 설정: http://localhost:${SERVICE_PORT}/mcp"
echo "   - Remote 설정: http://${SERVER_IP}:${SERVICE_PORT}/mcp"
echo ""

echo "🔧 관리 명령어:"
echo "   서비스 상태: systemctl status external-llm-mcp"
echo "   서비스 중지: systemctl stop external-llm-mcp"
echo "   서비스 시작: systemctl start external-llm-mcp"
echo "   서비스 재시작: systemctl restart external-llm-mcp"
echo "   로그 확인: journalctl -u external-llm-mcp -f"
echo "   또는: tail -f $INSTALL_DIR/logs/server.log"
echo ""

echo "🔑 API 키 설정:"
echo "   vi $INSTALL_DIR/.env"
echo "   설정 후 서비스 재시작: systemctl restart external-llm-mcp"
echo ""

echo "🧪 테스트:"
echo "   curl http://localhost:${SERVICE_PORT}/health"
echo "   curl http://${SERVER_IP}:${SERVICE_PORT}/health"
echo ""

echo "================================================================================"
