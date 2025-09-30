#!/bin/bash

# IP 설정 스크립트 - 웹서버 IP 주소 쉽게 변경하기
# 제2원칙: 포트 점유 및 확보 우선 정책 준수

set -e

# .env 파일 로드
if [ -f "/home/chatpro/sdc_i/.env" ]; then
    source "/home/chatpro/sdc_i/.env"
fi

echo "🔧 SDC 시스템 IP 설정 도구"
echo "=============================="
echo "🌐 현재 외부 접속 IP: $HOST_IP"
echo "⚠️  IP 변경 시 이 스크립트로 설정을 업데이트하세요!"
echo ""

ENV_FILE="/home/chatpro/sdc_i/frontend/.env.local"

# 현재 설정 표시
echo "📋 현재 설정:"
if [ -f "$ENV_FILE" ]; then
    current_setting=$(grep "^NEXT_PUBLIC_API_URL=" "$ENV_FILE" | head -1)
    if [ -n "$current_setting" ]; then
        echo "   $current_setting"
    else
        echo "   설정 없음"
    fi
else
    echo "   설정 파일 없음"
fi

echo ""
echo "🌐 현재 시스템 IP 주소:"
ip addr show | grep -E "inet [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | grep -v "127.0.0.1" | awk '{print "   " $2}' | head -3

echo ""
echo "⚙️ 설정 옵션:"
echo "1) 자동 감지 (접속 IP에 따라 자동 선택) - 추천"
echo "2) 고정 IP 설정"
echo "3) 로컬호스트 고정"
echo "4) 캐시 설정 변경"
echo "5) 현재 설정 유지"

echo ""
read -p "선택하세요 (1-5): " choice

case $choice in
    1)
        echo "🔄 자동 감지 모드로 설정 중..."
        sed -i 's/^NEXT_PUBLIC_API_URL=.*/NEXT_PUBLIC_API_URL=auto/' "$ENV_FILE"
        echo "✅ 자동 감지 모드로 설정 완료"
        ;;
    2)
        echo ""
        current_ip="$HOST_IP"
        detected_ip=$(ip addr show | grep -E "inet [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | grep -v "127.0.0.1" | head -1 | awk '{print $2}' | cut -d'/' -f1)
        echo "💡 현재 설정된 IP: $current_ip"
        echo "🔍 시스템 감지 IP: $detected_ip"
        read -p "설정할 IP 주소를 입력하세요 (Enter=현재IP 유지): " user_ip

        # 입력이 없으면 현재 IP 유지
        if [ -z "$user_ip" ]; then
            user_ip="$current_ip"
        fi

        if [[ $user_ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "🔄 고정 IP $user_ip 로 설정 중..."
            sed -i "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://$user_ip:8000|" "$ENV_FILE"
            echo "✅ 고정 IP 설정 완료: http://$user_ip:8000"
        else
            echo "❌ 올바른 IP 형식이 아닙니다."
            exit 1
        fi
        ;;
    3)
        echo "🔄 로컬호스트 모드로 설정 중..."
        sed -i 's|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://localhost:8000|' "$ENV_FILE"
        echo "✅ 로컬호스트 모드로 설정 완료"
        ;;
    4)
        echo "🔄 캐시 설정 변경 중..."
        echo ""
        echo "📋 현재 캐시 설정:"
        current_cache=$(grep "^NEXT_CACHE_DISABLED=" "$ENV_FILE" | head -1)
        if [ -n "$current_cache" ]; then
            echo "   $current_cache"
        else
            echo "   설정 없음 (기본값: 캐시 활성화)"
        fi

        echo ""
        echo "🔄 캐시 설정 옵션:"
        echo "1) 캐시 비활성화 (실시간 개발 모드) - 현재 권장"
        echo "2) 캐시 활성화 (프로덕션 모드)"

        echo ""
        read -p "캐시 설정을 선택하세요 (1-2): " cache_choice

        case $cache_choice in
            1)
                echo "🔄 캐시 비활성화 설정 중..."
                sed -i 's/^NEXT_CACHE_DISABLED=.*/NEXT_CACHE_DISABLED=true/' "$ENV_FILE"
                sed -i 's/^NEXT_CACHE_MAX_AGE=.*/NEXT_CACHE_MAX_AGE=0/' "$ENV_FILE"
                sed -i 's/^NEXT_REVALIDATE_TIME=.*/NEXT_REVALIDATE_TIME=0/' "$ENV_FILE"
                echo "✅ 캐시 비활성화 완료 - 실시간 변경 적용됨"
                ;;
            2)
                echo "🔄 캐시 활성화 설정 중..."
                sed -i 's/^NEXT_CACHE_DISABLED=.*/NEXT_CACHE_DISABLED=false/' "$ENV_FILE"
                sed -i 's/^NEXT_CACHE_MAX_AGE=.*/NEXT_CACHE_MAX_AGE=3600/' "$ENV_FILE"
                sed -i 's/^NEXT_REVALIDATE_TIME=.*/NEXT_REVALIDATE_TIME=60/' "$ENV_FILE"
                echo "✅ 캐시 활성화 완료 - 성능 최적화됨"
                ;;
            *)
                echo "❌ 잘못된 선택입니다."
                ;;
        esac
        ;;
    5)
        echo "⏭️ 현재 설정을 유지합니다."
        ;;
    *)
        echo "❌ 잘못된 선택입니다."
        exit 1
        ;;
esac

echo ""
echo "📋 변경된 설정:"
grep "^NEXT_PUBLIC_API_URL=" "$ENV_FILE"

echo ""
echo "🔄 설정을 적용하려면 웹서버를 재시작하세요:"
echo "   cd /home/chatpro/sdc_i/frontend"
echo "   npm run dev"

echo ""
echo "🎉 IP 설정이 완료되었습니다!"