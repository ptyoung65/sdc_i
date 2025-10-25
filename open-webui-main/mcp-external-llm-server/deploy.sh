#!/bin/bash

# External LLM MCP Server - Remote Deployment Script
# 원격 서버에 MCP 서버를 배포합니다.

set -e

echo "================================================================================"
echo "🚀 External LLM MCP Server - Remote Deployment"
echo "================================================================================"
echo ""

# 설정
REMOTE_HOST="${1}"
REMOTE_USER="${2:-root}"
REMOTE_PORT="${3:-22}"
INSTALL_METHOD="${4:-ssh}"  # ssh 또는 manual

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_NAME="external-llm-mcp-server.tar.gz"

# 사용법 체크
if [ -z "$REMOTE_HOST" ]; then
    echo "사용법: $0 <원격_서버_IP> [사용자] [SSH_포트] [설치방법]"
    echo ""
    echo "예시:"
    echo "  $0 192.168.1.100                    # root 사용자, SSH 포트 22"
    echo "  $0 192.168.1.100 admin               # admin 사용자"
    echo "  $0 192.168.1.100 admin 2222          # 사용자 지정 SSH 포트"
    echo "  $0 192.168.1.100 root 22 manual      # 수동 설치 패키지만 생성"
    echo ""
    echo "설치 방법:"
    echo "  ssh    - SSH로 자동 설치 (기본값)"
    echo "  manual - 패키지만 생성하여 수동 설치"
    echo ""
    exit 1
fi

echo "📋 배포 정보:"
echo "   원격 서버: $REMOTE_HOST"
echo "   사용자: $REMOTE_USER"
echo "   SSH 포트: $REMOTE_PORT"
echo "   설치 방법: $INSTALL_METHOD"
echo ""

# 1. 패키지 생성
echo "📦 배포 패키지 생성 중..."

cd "$SCRIPT_DIR"

# 임시 디렉토리 생성
TMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TMP_DIR/external-llm-mcp-server"
mkdir -p "$PACKAGE_DIR"

# 필요한 파일 복사
cp external_llm_mcp_server.py "$PACKAGE_DIR/"
cp install.sh "$PACKAGE_DIR/"
cp .env.example "$PACKAGE_DIR/" 2>/dev/null || true

# .env 파일이 있으면 복사 (API 키 포함)
if [ -f ".env" ]; then
    echo "   ℹ️  .env 파일 포함 (API 키가 포함될 수 있습니다)"
    cp .env "$PACKAGE_DIR/"
fi

# README 생성
cat > "$PACKAGE_DIR/README_INSTALL.txt" <<'EOF'
# External LLM MCP Server - 설치 가이드

## 설치 방법

1. 압축 해제:
   tar -xzf external-llm-mcp-server.tar.gz
   cd external-llm-mcp-server

2. 설치 스크립트 실행 (root 권한 필요):
   sudo ./install.sh

3. API 키 설정:
   sudo vi /opt/external-llm-mcp-server/.env

   OPENAI_API_KEY=sk-your-key-here
   PERPLEXITY_API_KEY=pplx-your-key-here

4. 서비스 재시작:
   sudo systemctl restart external-llm-mcp

5. 상태 확인:
   systemctl status external-llm-mcp
   curl http://localhost:8100/health

## 방화벽 설정 (필요시)

CentOS/RHEL:
  sudo firewall-cmd --permanent --add-port=8100/tcp
  sudo firewall-cmd --reload

Ubuntu:
  sudo ufw allow 8100/tcp

## Open WebUI 연결

로컬 서버:
  http://localhost:8100/mcp

원격 서버:
  http://YOUR_SERVER_IP:8100/mcp

## 관리 명령어

systemctl status external-llm-mcp   # 상태 확인
systemctl stop external-llm-mcp     # 중지
systemctl start external-llm-mcp    # 시작
systemctl restart external-llm-mcp  # 재시작
journalctl -u external-llm-mcp -f   # 로그 확인
EOF

# 오프라인 패키지 추가 (있으면)
if [ -d "offline-packages" ]; then
    echo "   ✅ 오프라인 패키지 포함"
    cp -r offline-packages "$PACKAGE_DIR/"
fi

# 패키지 압축
cd "$TMP_DIR"
tar -czf "$SCRIPT_DIR/$PACKAGE_NAME" external-llm-mcp-server/
cd "$SCRIPT_DIR"

# 임시 디렉토리 정리
rm -rf "$TMP_DIR"

PACKAGE_SIZE=$(du -h "$PACKAGE_NAME" | cut -f1)
echo "   ✅ 패키지 생성 완료: $PACKAGE_NAME ($PACKAGE_SIZE)"
echo ""

# 2. 배포 방식에 따라 처리
if [ "$INSTALL_METHOD" == "manual" ]; then
    echo "================================================================================"
    echo "✅ 수동 설치 패키지 생성 완료!"
    echo "================================================================================"
    echo ""
    echo "📦 패키지 위치: $SCRIPT_DIR/$PACKAGE_NAME"
    echo ""
    echo "📝 다음 단계:"
    echo "   1. 패키지를 원격 서버로 전송:"
    echo "      scp -P $REMOTE_PORT $PACKAGE_NAME $REMOTE_USER@$REMOTE_HOST:/tmp/"
    echo ""
    echo "   2. 원격 서버에서 설치:"
    echo "      ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST"
    echo "      cd /tmp"
    echo "      tar -xzf $PACKAGE_NAME"
    echo "      cd external-llm-mcp-server"
    echo "      sudo ./install.sh"
    echo ""
    echo "   3. API 키 설정:"
    echo "      sudo vi /opt/external-llm-mcp-server/.env"
    echo "      sudo systemctl restart external-llm-mcp"
    echo ""
    exit 0
fi

# 3. SSH 자동 배포
echo "🔗 원격 서버 연결 확인 중..."

if ! ssh -p "$REMOTE_PORT" -o ConnectTimeout=5 "$REMOTE_USER@$REMOTE_HOST" "echo connected" &>/dev/null; then
    echo "❌ 원격 서버에 연결할 수 없습니다."
    echo ""
    echo "문제 해결:"
    echo "   1. SSH 접속 확인: ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST"
    echo "   2. 방화벽 확인"
    echo "   3. SSH 키 인증 설정"
    echo ""
    echo "   또는 수동 설치 모드 사용:"
    echo "   $0 $REMOTE_HOST $REMOTE_USER $REMOTE_PORT manual"
    exit 1
fi

echo "   ✅ 연결 성공"
echo ""

# 4. 패키지 전송
echo "📤 패키지 전송 중..."
scp -P "$REMOTE_PORT" "$PACKAGE_NAME" "$REMOTE_USER@$REMOTE_HOST:/tmp/"
echo "   ✅ 전송 완료"
echo ""

# 5. 원격 서버에서 설치 실행
echo "🚀 원격 서버에서 설치 중..."
echo ""

ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" <<'ENDSSH'
set -e

echo "================================================================================"
echo "📦 원격 서버에서 설치 시작"
echo "================================================================================"
echo ""

cd /tmp
tar -xzf external-llm-mcp-server.tar.gz
cd external-llm-mcp-server

# 설치 스크립트 실행
chmod +x install.sh
./install.sh

echo ""
echo "================================================================================"
echo "✅ 원격 설치 완료!"
echo "================================================================================"
ENDSSH

# 6. 설치 결과 확인
echo ""
echo "🔍 설치 결과 확인 중..."

HEALTH_CHECK=$(ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" \
    "curl -s http://localhost:8100/health" 2>/dev/null || echo "fail")

if [ "$HEALTH_CHECK" != "fail" ]; then
    echo "   ✅ MCP 서버 정상 작동 중"
    echo ""
    echo "$HEALTH_CHECK" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_CHECK"
else
    echo "   ⚠️  헬스 체크 실패 (서비스는 실행 중일 수 있음)"
    echo "   원격 서버에서 확인: ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST"
    echo "   systemctl status external-llm-mcp"
fi

echo ""
echo "================================================================================"
echo "✅ 배포 완료!"
echo "================================================================================"
echo ""
echo "🌐 접속 URL:"
echo "   로컬 (서버 내부): http://localhost:8100/mcp"
echo "   원격 (외부): http://$REMOTE_HOST:8100/mcp"
echo ""
echo "📝 Open WebUI 설정:"
echo "   Settings → Workspace → Tools → Tool Servers → Add"
echo "   Server URL: http://$REMOTE_HOST:8100/mcp"
echo "   Server Type: mcp"
echo "   Authentication: none"
echo ""
echo "🔑 API 키 설정 (필요시):"
echo "   ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST"
echo "   sudo vi /opt/external-llm-mcp-server/.env"
echo "   sudo systemctl restart external-llm-mcp"
echo ""
echo "🔧 원격 관리:"
echo "   상태 확인: ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST 'systemctl status external-llm-mcp'"
echo "   로그 확인: ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST 'journalctl -u external-llm-mcp -f'"
echo ""
echo "================================================================================"
