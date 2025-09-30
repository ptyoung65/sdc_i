#!/bin/bash

# SDC 프로젝트 동적 IP 설정 유틸리티
# 현재 시스템의 IP를 자동으로 감지하거나 환경변수에서 가져옴

get_host_ip() {
    # 1. 환경변수에서 WEB_SERVER_EXTERNAL_IP 확인 (최우선)
    if [ -n "$WEB_SERVER_EXTERNAL_IP" ]; then
        echo "$WEB_SERVER_EXTERNAL_IP"
        return 0
    fi

    # 2. .env 파일에서 WEB_SERVER_EXTERNAL_IP 확인
    if [ -f ".env" ] && grep -q "WEB_SERVER_EXTERNAL_IP=" .env; then
        local web_ip=$(grep "WEB_SERVER_EXTERNAL_IP=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
        if [ -n "$web_ip" ]; then
            echo "$web_ip"
            return 0
        fi
    fi

    # 3. 환경변수에서 HOST_IP 확인 (호환성)
    if [ -n "$HOST_IP" ]; then
        echo "$HOST_IP"
        return 0
    fi

    # 4. .env 파일에서 HOST_IP 확인 (호환성)
    if [ -f ".env" ] && grep -q "HOST_IP=" .env; then
        local env_ip=$(grep "HOST_IP=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
        if [ -n "$env_ip" ]; then
            echo "$env_ip"
            return 0
        fi
    fi

    # 3. 자동 IP 감지 (여러 방법 시도)
    local detected_ip=""

    # 방법 1: ip route를 통한 감지
    detected_ip=$(ip route get 1 2>/dev/null | grep -oP 'src \K\S+' | head -n1)
    if [ -n "$detected_ip" ] && [[ $detected_ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "$detected_ip"
        return 0
    fi

    # 방법 2: hostname -I를 통한 감지
    detected_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -n "$detected_ip" ] && [[ $detected_ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "$detected_ip"
        return 0
    fi

    # 방법 3: ip addr을 통한 감지
    detected_ip=$(ip addr show | grep -oP 'inet \K[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | grep -v '127.0.0.1' | head -n1)
    if [ -n "$detected_ip" ] && [[ $detected_ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "$detected_ip"
        return 0
    fi

    # 기본값으로 localhost 반환
    echo "localhost"
}

# 웹 서버 바인딩 IP 가져오기
get_web_server_bind_ip() {
    # 1. 환경변수에서 WEB_SERVER_BIND_IP 확인
    if [ -n "$WEB_SERVER_BIND_IP" ]; then
        echo "$WEB_SERVER_BIND_IP"
        return 0
    fi

    # 2. .env 파일에서 WEB_SERVER_BIND_IP 확인
    if [ -f ".env" ] && grep -q "WEB_SERVER_BIND_IP=" .env; then
        local bind_ip=$(grep "WEB_SERVER_BIND_IP=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
        if [ -n "$bind_ip" ]; then
            echo "$bind_ip"
            return 0
        fi
    fi

    # 기본값: 모든 인터페이스에 바인딩
    echo "0.0.0.0"
}

# 현재 IP를 .env 파일에 저장
save_host_ip_to_env() {
    local ip=$(get_host_ip)

    if [ -f ".env" ]; then
        # 기존 IP 설정들 제거
        grep -v -E "(HOST_IP=|WEB_SERVER_EXTERNAL_IP=)" .env > .env.tmp && mv .env.tmp .env
    fi

    # 새로운 IP 설정들 추가
    echo "HOST_IP='$ip'" >> .env
    echo "WEB_SERVER_EXTERNAL_IP=$ip" >> .env
    echo "IP 설정이 .env 파일에 저장되었습니다: $ip"
}

# URL 생성 함수
get_service_url() {
    local port=$1
    local path=${2:-""}
    local ip=$(get_host_ip)

    echo "http://$ip:$port$path"
}

# 스크립트가 직접 실행된 경우
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    case "${1:-get}" in
        "get")
            get_host_ip
            ;;
        "save")
            save_host_ip_to_env
            ;;
        "url")
            get_service_url "$2" "$3"
            ;;
        "bind")
            get_web_server_bind_ip
            ;;
        "set-bind")
            if [ -n "$2" ]; then
                if [ -f ".env" ]; then
                    grep -v "WEB_SERVER_BIND_IP=" .env > .env.tmp && mv .env.tmp .env
                fi
                echo "WEB_SERVER_BIND_IP=$2" >> .env
                echo "웹 서버 바인딩 IP가 설정되었습니다: $2"
            else
                echo "사용법: $0 set-bind <IP주소>"
            fi
            ;;
        "set-external")
            if [ -n "$2" ]; then
                if [ -f ".env" ]; then
                    grep -v "WEB_SERVER_EXTERNAL_IP=" .env > .env.tmp && mv .env.tmp .env
                fi
                echo "WEB_SERVER_EXTERNAL_IP=$2" >> .env
                echo "외부 접근 IP가 설정되었습니다: $2"
            else
                echo "사용법: $0 set-external <IP주소>"
            fi
            ;;
        *)
            echo "사용법: $0 [get|save|url|bind|set-bind|set-external]"
            echo "  get                    - 현재 호스트 IP 반환"
            echo "  save                   - 현재 IP를 .env 파일에 저장"
            echo "  url <port> [path]      - 서비스 URL 생성"
            echo "  bind                   - 웹 서버 바인딩 IP 반환"
            echo "  set-bind <IP>          - 웹 서버 바인딩 IP 설정"
            echo "  set-external <IP>      - 외부 접근 IP 설정"
            echo ""
            echo "예시:"
            echo "  $0 get                     # 현재 IP 확인"
            echo "  $0 set-bind 0.0.0.0        # 모든 인터페이스에 바인딩"
            echo "  $0 set-external 10.0.0.100 # 외부 접근용 IP 설정"
            ;;
    esac
fi