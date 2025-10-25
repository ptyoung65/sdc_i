#!/bin/bash

# Offline Package Preparation Script
# 오프라인 환경에서 설치할 수 있도록 Python 패키지를 다운로드합니다.

set -e

echo "================================================================================"
echo "📦 Offline Package Preparation"
echo "================================================================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OFFLINE_DIR="$SCRIPT_DIR/offline-packages"

# 인터넷 연결 확인
if ! ping -c 1 8.8.8.8 &> /dev/null; then
    echo "❌ 인터넷 연결이 필요합니다."
    echo "   온라인 서버에서 이 스크립트를 실행하세요."
    exit 1
fi

echo "✅ 인터넷 연결 확인 완료"
echo ""

# 오프라인 디렉토리 생성
mkdir -p "$OFFLINE_DIR"

echo "📥 Python 패키지 다운로드 중..."
echo "   대상 디렉토리: $OFFLINE_DIR"
echo ""

# pip 업그레이드
pip3 install --upgrade pip

# 필요한 패키지 다운로드
PACKAGES=(
    "fastapi==0.109.0"
    "uvicorn[standard]==0.27.0"
    "httpx==0.26.0"
    "pydantic==2.5.3"
    "python-dotenv==1.0.0"
)

for package in "${PACKAGES[@]}"; do
    echo "   다운로드 중: $package"
    pip3 download --dest "$OFFLINE_DIR" "$package"
done

echo ""
echo "✅ 다운로드 완료!"
echo ""

# 패키지 목록 생성
echo "📝 패키지 목록 생성 중..."
ls -lh "$OFFLINE_DIR" > "$OFFLINE_DIR/package_list.txt"
cat > "$OFFLINE_DIR/requirements.txt" <<EOF
fastapi==0.109.0
uvicorn[standard]==0.27.0
httpx==0.26.0
pydantic==2.5.3
python-dotenv==1.0.0
EOF

echo "   ✅ requirements.txt 생성 완료"
echo ""

# 설치 방법 안내 문서
cat > "$OFFLINE_DIR/INSTALL_OFFLINE.txt" <<'EOF'
# 오프라인 패키지 설치 가이드

## 설치 방법

1. 모든 패키지 설치:
   pip3 install --no-index --find-links=. -r requirements.txt

2. 개별 패키지 설치:
   pip3 install --no-index --find-links=. fastapi

3. 확인:
   pip3 list | grep -E "fastapi|uvicorn|httpx|pydantic"

## 패키지 목록
- fastapi: 웹 프레임워크
- uvicorn: ASGI 서버
- httpx: HTTP 클라이언트
- pydantic: 데이터 검증
- python-dotenv: 환경 변수 로드
EOF

echo "================================================================================"
echo "✅ 오프라인 패키지 준비 완료!"
echo "================================================================================"
echo ""
echo "📁 패키지 위치: $OFFLINE_DIR"
echo ""
echo "📦 다운로드된 파일:"
ls -lh "$OFFLINE_DIR" | grep ".whl\|.tar.gz"
echo ""
echo "📋 사용 방법:"
echo "   1. offline-packages 디렉토리를 오프라인 서버로 복사"
echo "   2. 오프라인 서버에서 설치:"
echo "      cd offline-packages"
echo "      pip3 install --no-index --find-links=. -r requirements.txt"
echo ""
echo "================================================================================"
