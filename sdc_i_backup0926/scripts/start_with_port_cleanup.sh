#!/bin/bash
# SDC 프로젝트 자동 시작 스크립트 (포트 충돌 방지)

set -e

# 환경 변수 로드
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 포트 정리 함수
cleanup_port() {
    local port=$1
    local process_name=$2
    
    log_info "포트 $port 상태 확인 중..."
    
    # 포트를 사용하는 프로세스 확인
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        log_warning "포트 $port이 사용 중입니다 ($process_name)"
        log_info "프로세스 정리 중..."
        
        # 일반 사용자 권한으로 먼저 시도
        echo "$pids" | xargs -r kill -9 2>/dev/null || {
            # sudo 권한으로 시도
            if [ -n "$SUDO_PASSWORD" ]; then
                log_info "sudo 권한으로 포트 $port 정리 중..."
                echo "$SUDO_PASSWORD" | sudo -S lsof -ti:$port | xargs -r sudo kill -9 2>/dev/null || {
                    log_warning "포트 $port 정리 실패, 계속 진행합니다..."
                }
            else
                log_warning "SUDO_PASSWORD가 설정되지 않아 sudo 권한 사용 불가"
            fi
        }
        
        # 잠시 대기
        sleep 2
        
        # 재확인
        if lsof -ti:$port >/dev/null 2>&1; then
            log_error "포트 $port 정리 실패"
            return 1
        else
            log_success "포트 $port 정리 완료"
        fi
    else
        log_success "포트 $port 사용 가능"
    fi
    
    return 0
}

# 메인 포트들 정리
log_info "🔧 SDC 프로젝트 포트 정리 시작"

cleanup_port 3000 "Frontend"
cleanup_port 3003 "Admin Panel" 
cleanup_port 8000 "Backend API"
cleanup_port 8008 "RAG Orchestrator"
cleanup_port 5432 "PostgreSQL"
cleanup_port 6379 "Redis"
cleanup_port 9091 "Milvus"

log_success "✅ 포트 정리 완료"

# 서비스 시작
log_info "🚀 SDC 서비스들 시작 중..."

# 백엔드 서비스 시작
log_info "백엔드 API 시작 중..."
cd /home/ptyoung/work/sdc_i/backend
source venv/bin/activate
python simple_api.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
sleep 3

# 백엔드 상태 확인
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    log_success "백엔드 API 시작 완료 (PID: $BACKEND_PID)"
else
    log_error "백엔드 API 시작 실패"
    exit 1
fi

# 프론트엔드 시작
log_info "프론트엔드 시작 중..."
cd /home/ptyoung/work/sdc_i/frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
sleep 5

# 프론트엔드 상태 확인
if curl -s http://localhost:3000 >/dev/null 2>&1; then
    log_success "프론트엔드 시작 완료 (PID: $FRONTEND_PID)"
else
    log_error "프론트엔드 시작 실패"
fi

# Admin Panel 시작
log_info "Admin Panel 시작 중..."
cd /home/ptyoung/work/sdc_i/services/admin-panel
npm run dev > ../../logs/admin.log 2>&1 &
ADMIN_PID=$!
sleep 5

# Admin Panel 상태 확인
if curl -s http://localhost:3003 >/dev/null 2>&1; then
    log_success "Admin Panel 시작 완료 (PID: $ADMIN_PID)"
else
    log_warning "Admin Panel 시작 확인 중..."
fi

# RAG Orchestrator 시작
log_info "RAG Orchestrator 시작 중..."
cd /home/ptyoung/work/sdc_i/services/rag-orchestrator
python main.py > ../../logs/rag-orchestrator.log 2>&1 &
RAG_PID=$!
sleep 5

# RAG Orchestrator 상태 확인
if curl -s http://localhost:8008/health >/dev/null 2>&1; then
    log_success "RAG Orchestrator 시작 완료 (PID: $RAG_PID)"
else
    log_warning "RAG Orchestrator 시작 확인 중..."
fi

log_success "🎉 SDC 프로젝트 시작 완료!"
log_info "📋 접속 정보:"
log_info "  • 메인 UI: http://localhost:3000"
log_info "  • Admin Panel: http://localhost:3003"
log_info "  • Backend API: http://localhost:8000"
log_info "  • RAG Orchestrator: http://localhost:8008"

log_info "📊 프로세스 ID:"
log_info "  • Backend: $BACKEND_PID"
log_info "  • Frontend: $FRONTEND_PID"
log_info "  • Admin Panel: $ADMIN_PID"
log_info "  • RAG Orchestrator: $RAG_PID"

log_info "🛑 종료하려면: pkill -f 'python simple_api.py|npm run dev|python main.py'"