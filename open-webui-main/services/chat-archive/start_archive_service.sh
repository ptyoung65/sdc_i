#!/bin/bash
# =============================================================================
# [2026-01-22] 채팅 아카이브 서비스 시작 스크립트
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 환경변수 설정 (기본값)
export DB_HOST="${DB_HOST:-192.168.122.85}"
export DB_PORT="${DB_PORT:-5433}"
export DB_USER="${DB_USER:-sdc_dev_user}"
export DB_PASSWORD="${DB_PASSWORD:-sdc_dev_pass_2025}"
export DB_NAME="${DB_NAME:-sdc_dev}"
export ARCHIVE_DAYS="${ARCHIVE_DAYS:-14}"
export ARCHIVE_PORT="${ARCHIVE_PORT:-8020}"

echo "=============================================="
echo "[2026-01-22] 채팅 아카이브 서비스 시작"
echo "=============================================="
echo "DB Host: $DB_HOST"
echo "DB Port: $DB_PORT"
echo "DB Name: $DB_NAME"
echo "Archive Days: $ARCHIVE_DAYS"
echo "Service Port: $ARCHIVE_PORT"
echo "=============================================="

# 가상환경 확인 및 활성화
if [ -d "venv" ]; then
    echo "가상환경 활성화 중..."
    source venv/bin/activate
elif [ -d "../../backend/venv" ]; then
    echo "백엔드 가상환경 사용..."
    source ../../backend/venv/bin/activate
else
    echo "가상환경이 없습니다. 생성 중..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# 서비스 실행
echo ""
echo "채팅 아카이브 서비스를 시작합니다..."
python chat_archive_service.py
