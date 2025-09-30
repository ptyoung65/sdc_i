#!/bin/bash

# 포트 충돌 자동 해결 스크립트
# 제2원칙: 포트 점유 및 확보 우선 정책 적용
# 제13원칙: 오류 해결 기록 및 자동화 정책 적용

set -e

PORT=$1

if [ -z "$PORT" ]; then
    echo "❌ 사용법: $0 <포트번호>"
    echo "예시: $0 3000"
    exit 1
fi

echo "🔧 포트 $PORT 충돌 자동 해결 중..."

# 포트 사용 중인 프로세스 확인
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️ 포트 $PORT이 사용 중입니다. 프로세스를 종료합니다."

    # 포트 사용 중인 프로세스 목록 출력
    echo "📋 포트 $PORT 사용 중인 프로세스:"
    lsof -Pi :$PORT -sTCP:LISTEN

    # 프로세스 강제 종료
    lsof -ti:$PORT | xargs -r kill -9

    # 포트 해제 대기
    sleep 2

    # 포트 해제 확인
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "❌ 포트 $PORT 해제 실패"
        exit 1
    else
        echo "✅ 포트 $PORT 해제 완료"
    fi
else
    echo "✅ 포트 $PORT은 이미 사용 가능합니다."
fi

# err_fix.md에 해결 기록 추가
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "✅ $TIMESTAMP - 포트 $PORT 충돌 해결 완료 (자동화 스크립트)" >> /home/chatpro/sdc_i/err_fix.md

echo "🎉 포트 $PORT 충돌 해결이 완료되었습니다."
echo "📝 해결 내용이 err_fix.md에 기록되었습니다."