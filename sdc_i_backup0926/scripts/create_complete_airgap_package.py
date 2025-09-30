#!/usr/bin/env python3
"""
Complete Air-gap Package Creator - 완전한 오프라인 배포 패키지
.git 폴더만 제외하고 node_modules, venv 포함한 모든 파일을 포함
"""

import os
import shutil
import tarfile
import json
from pathlib import Path
from datetime import datetime

def log_info(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] INFO: {message}")

def log_success(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] SUCCESS: {message}")

def log_error(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ERROR: {message}")

def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def copy_complete_project(project_root: Path, staging_dir: Path) -> None:
    """Copy complete project excluding only .git folder"""
    log_info("완전한 프로젝트 복사 시작 (모든 파일 포함)...")
    
    project_staging = staging_dir / "sdc_project"
    ensure_directory(project_staging)
    
    # .git 폴더만 제외
    exclude_patterns = ['.git']
    
    copied_size = 0
    for item in project_root.iterdir():
        if item.name in exclude_patterns:
            log_info(f"제외: {item.name}")
            continue
            
        log_info(f"복사 중: {item.name}")
        try:
            if item.is_dir():
                # node_modules, venv 등 모든 디렉토리 포함
                shutil.copytree(item, project_staging / item.name, 
                              ignore=shutil.ignore_patterns('.git'))
            else:
                shutil.copy2(item, project_staging)
            
            # 복사된 크기 계산
            if item.is_dir():
                for root, dirs, files in os.walk(project_staging / item.name):
                    for file in files:
                        fp = os.path.join(root, file)
                        if os.path.exists(fp):
                            copied_size += os.path.getsize(fp)
            else:
                copied_size += (project_staging / item.name).stat().st_size
                
        except Exception as e:
            log_error(f"복사 실패 {item.name}: {e}")
            continue
    
    log_success(f"프로젝트 복사 완료: {project_staging}")
    log_info(f"복사된 크기: {copied_size / (1024**3):.1f} GB")

def create_complete_install_script(staging_dir: Path) -> None:
    """Create comprehensive installation script for complete package"""
    install_script = staging_dir / "install_complete_airgap.sh"
    
    script_content = '''#!/bin/bash
set -e

# Complete SDC Air-gap Installation Script
echo "=============================================="
echo "SDC 완전한 Air-gap 설치 스크립트"  
echo "=============================================="

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get installation directory
get_install_dir() {
    if [ "$#" -eq 1 ]; then
        echo "$1"
        return
    fi
    
    echo "설치 위치를 선택하세요:"
    echo "1) /opt/sdc (권장 - 시스템 전체 설치)"
    echo "2) $HOME/sdc (개인 사용자 설치)"
    echo "3) $(pwd)/sdc (현재 위치)"
    echo "4) 사용자 지정 경로"
    
    read -p "선택 (1-4): " choice
    case $choice in
        1) echo "/opt/sdc" ;;
        2) echo "$HOME/sdc" ;;
        3) echo "$(pwd)/sdc" ;;
        4) read -p "설치 경로 입력: " custom; echo "$custom" ;;
        *) echo "/opt/sdc" ;;
    esac
}

# Check if running as root when needed
check_permissions() {
    if [[ "$INSTALL_DIR" == /opt/* ]] && [ "$EUID" -ne 0 ]; then
        log_error "시스템 디렉토리 설치를 위해 sudo 권한이 필요합니다"
        log_info "다음과 같이 실행하세요: sudo $0"
        exit 1
    fi
}

# Install system dependencies (minimal - assume air-gap)
install_minimal_deps() {
    log_info "필수 시스템 도구 확인 중..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3가 설치되어 있지 않습니다"
        log_info "Air-gap 환경에서 Python3를 먼저 설치하세요"
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_warning "Node.js가 설치되어 있지 않습니다"
        log_info "프론트엔드 실행을 위해 Node.js가 필요합니다"
    fi
    
    # Check Podman/Docker
    if ! command -v podman &> /dev/null && ! command -v docker &> /dev/null; then
        log_warning "Podman 또는 Docker가 설치되어 있지 않습니다"
        log_info "컨테이너 실행을 위해 Podman 또는 Docker가 필요합니다"
    fi
    
    log_success "시스템 요구사항 확인 완료"
}

# Setup project
setup_project() {
    log_info "프로젝트 설정 중..."
    
    cd "$INSTALL_DIR"
    
    # Copy environment file
    if [ -f ".env.example" ] && [ ! -f ".env" ]; then
        cp .env.example .env
        log_info ".env 파일이 생성되었습니다"
        log_warning "API 키를 설정하세요: nano .env"
    fi
    
    # Make scripts executable
    if [ -d "scripts" ]; then
        chmod +x scripts/*.sh 2>/dev/null || true
        log_info "스크립트 실행 권한 설정 완료"
    fi
    
    log_success "프로젝트 설정 완료"
}

# Verify installation
verify_installation() {
    log_info "설치 검증 중..."
    
    cd "$INSTALL_DIR"
    
    # Check Python venv
    if [ -f "backend/venv/bin/python" ]; then
        log_success "Python 가상환경 확인됨"
    else
        log_warning "Python 가상환경이 없습니다"
    fi
    
    # Check Node.js dependencies
    if [ -d "frontend/node_modules" ]; then
        log_success "Node.js 의존성 확인됨"
    else
        log_warning "Node.js 의존성이 없습니다"
    fi
    
    # Check major directories
    for dir in backend frontend services; do
        if [ -d "$dir" ]; then
            log_success "$dir 디렉토리 확인"
        else
            log_warning "$dir 디렉토리가 없습니다"
        fi
    done
}

# Main installation
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            -y|--yes)
                AUTO_YES=true
                shift
                ;;
            -h|--help)
                echo "사용법: $0 [옵션]"
                echo "옵션:"
                echo "  -d, --dir PATH    설치 디렉토리 지정"
                echo "  -y, --yes        자동 설치 (대화형 모드 비활성화)"
                echo "  -h, --help       도움말 표시"
                exit 0
                ;;
            *)
                echo "알 수 없는 옵션: $1"
                exit 1
                ;;
        esac
    done
    
    # Get installation directory
    if [ -z "$INSTALL_DIR" ]; then
        if [ "$AUTO_YES" = true ]; then
            INSTALL_DIR="/opt/sdc"
        else
            INSTALL_DIR=$(get_install_dir)
        fi
    fi
    
    log_info "설치 위치: $INSTALL_DIR"
    
    # Check permissions
    check_permissions
    
    # Create installation directory
    if [[ "$INSTALL_DIR" == /opt/* ]]; then
        sudo mkdir -p "$INSTALL_DIR"
        sudo chown $(whoami):$(whoami) "$INSTALL_DIR"
    else
        mkdir -p "$INSTALL_DIR"
    fi
    
    # Copy project files
    log_info "프로젝트 파일 복사 중..."
    if [ -d "sdc_project" ]; then
        cp -r sdc_project/* "$INSTALL_DIR/"
        log_success "프로젝트 파일 복사 완료"
    else
        log_error "sdc_project 디렉토리를 찾을 수 없습니다"
        exit 1
    fi
    
    # Setup project
    install_minimal_deps
    setup_project
    verify_installation
    
    echo ""
    echo "=============================================="
    log_success "SDC 완전한 Air-gap 설치 완료!"
    echo "=============================================="
    echo ""
    log_info "설치 위치: $INSTALL_DIR"
    echo ""
    log_info "포함된 모든 파일:"
    echo "  ✅ 완전한 소스 코드"
    echo "  ✅ Python 가상환경 (backend/venv) - 6.1GB"
    echo "  ✅ Node.js 의존성 (frontend/node_modules) - 786MB"
    echo "  ✅ 모든 서비스 의존성"
    echo "  ✅ 설정 파일 및 스크립트"
    echo ""
    log_info "즉시 실행 가능:"
    echo "  • 백엔드: cd $INSTALL_DIR/backend && source venv/bin/activate && python simple_api.py"
    echo "  • 프론트엔드: cd $INSTALL_DIR/frontend && npm run dev"
    echo ""
    log_warning "추가 설정:"
    echo "  1. .env 파일에서 API 키 설정: nano $INSTALL_DIR/.env"
    echo "  2. 포트 3000, 8000이 사용 가능한지 확인"
    echo ""
}

main "$@"
'''
    
    with open(install_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    install_script.chmod(0o755)
    log_success(f"완전 설치 스크립트 생성: {install_script}")

def create_complete_readme(staging_dir: Path) -> None:
    """Create comprehensive README for complete package"""
    readme = staging_dir / "README.md"
    
    readme_content = """# SDC Korean RAG System - 완전한 Air-gap 배포 패키지

## 🚀 완전한 오프라인 배포 패키지

이 패키지는 **완전한** SDC Korean RAG 시스템을 포함합니다:
- ✅ 전체 소스 코드
- ✅ Python 가상환경 (backend/venv) - 6.1GB
- ✅ Node.js 의존성 (frontend/node_modules) - 786MB  
- ✅ 모든 서비스 의존성
- ✅ 즉시 실행 가능한 완전한 환경

## 📦 패키지 내용

```
sdc-complete-airgap/
├── README.md                       # 이 파일
├── install_complete_airgap.sh      # 자동 설치 스크립트
└── sdc_project/                    # 완전한 프로젝트 (.git 제외)
    ├── backend/
    │   ├── venv/                   # 완전한 Python 가상환경 (6.1GB)
    │   ├── app/                    # 백엔드 소스 코드
    │   └── requirements.txt        # Python 의존성 목록
    ├── frontend/
    │   ├── node_modules/           # 완전한 Node.js 의존성 (786MB)
    │   ├── src/                    # 프론트엔드 소스 코드
    │   └── package.json            # Node.js 의존성 목록
    ├── services/                   # 마이크로서비스들 (623MB)
    ├── scripts/                    # 관리 스크립트들
    └── docker-compose.yml          # 컨테이너 오케스트레이션
```

**총 크기**: 약 7.5GB (압축 해제 후 19GB)

## ⚡ 빠른 설치 (Air-gap 환경)

### 1. 패키지 추출
```bash
tar -xzf sdc-complete-airgap-*.tar.gz
cd sdc-complete-airgap
```

### 2. 자동 설치
```bash
# 대화형 설치
sudo ./install_complete_airgap.sh

# 또는 자동 설치 (/opt/sdc)
sudo ./install_complete_airgap.sh -y

# 또는 사용자 지정 위치
sudo ./install_complete_airgap.sh -d /your/path
```

### 3. 즉시 실행
```bash
cd [설치위치]

# .env 파일 설정 (API 키 추가)
nano .env

# 백엔드 실행
cd backend
source venv/bin/activate
python simple_api.py

# 새 터미널에서 프론트엔드 실행  
cd frontend
npm run dev
```

## 🎯 즉시 접속 가능

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 💡 Air-gap 환경의 장점

이 패키지는 **완전한 오프라인 실행**이 가능합니다:

1. **인터넷 연결 불필요**: 모든 의존성이 포함됨
2. **즉시 실행 가능**: 추가 다운로드 없음
3. **완전한 개발환경**: 수정, 빌드, 테스트 모두 가능
4. **보안**: 외부 네트워크 접근 없이 안전한 실행

## 🔧 시스템 요구사항

### 최소 요구사항
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+)
- **메모리**: 8GB RAM 최소, 16GB 권장
- **저장공간**: 25GB 여유 공간 (압축 해제 + 실행)
- **Python**: 3.8+ (시스템에 설치 필요)

### 권장 요구사항  
- **Node.js**: 18+ (프론트엔드 실행용)
- **Podman/Docker**: 컨테이너 실행용 (선택사항)

## 📋 포함된 모든 구성요소

### Backend (Python)
- ✅ 완전한 가상환경 (venv)
- ✅ FastAPI + Uvicorn
- ✅ SQLAlchemy, AsyncPG
- ✅ LangChain, LangGraph
- ✅ Sentence-Transformers
- ✅ 모든 AI/ML 라이브러리

### Frontend (Node.js)
- ✅ 완전한 node_modules
- ✅ Next.js 15 + React
- ✅ TypeScript + Tailwind CSS
- ✅ Radix UI 컴포넌트
- ✅ 모든 프론트엔드 의존성

### Services
- ✅ 모든 마이크로서비스
- ✅ Korean RAG 최적화 모델
- ✅ 벡터 데이터베이스 서비스
- ✅ 관리 패널 및 대시보드

## 🚀 개발 시작하기

### 백엔드 개발
```bash
cd backend
source venv/bin/activate  # 이미 모든 라이브러리 설치됨
python simple_api.py
```

### 프론트엔드 개발
```bash
cd frontend  # node_modules 이미 설치됨
npm run dev
```

### 마이크로서비스 개발
```bash
cd services/korean-rag-orchestrator
# 각 서비스별 가상환경 이미 설정됨
python main.py
```

## 📞 문제 해결

### 일반적인 문제

1. **권한 오류**
   ```bash
   chmod +x install_complete_airgap.sh
   sudo chown -R $(whoami):$(whoami) /설치/경로
   ```

2. **포트 충돌**
   ```bash
   # 포트 사용 확인
   sudo netstat -tlnp | grep :3000
   sudo netstat -tlnp | grep :8000
   ```

3. **메모리 부족**
   ```bash
   # 메모리 확인
   free -h
   # 최소 8GB RAM 필요
   ```

## ⚠️ 중요 사항

1. **완전한 패키지**: 추가 다운로드나 설치 불필요
2. **대용량**: 압축 파일이 3-5GB, 해제 후 19GB
3. **즉시 실행**: 설치 후 바로 개발 가능
4. **보안**: .env 파일에서 API 키 설정 필요

---

**SDC Korean RAG System v1.0**  
Complete Air-gap Deployment Package
"""
    
    with open(readme, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    log_success(f"완전 README 생성: {readme}")

def create_complete_package(staging_dir: Path, output_dir: Path) -> Path:
    """Create final complete package"""
    ensure_directory(output_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"sdc-complete-airgap-{timestamp}.tar.gz"
    package_path = output_dir / package_name
    
    log_info("최종 패키지 생성 중... (시간이 오래 걸릴 수 있습니다)")
    
    with tarfile.open(package_path, 'w:gz') as tar:
        tar.add(staging_dir, arcname="sdc-complete-airgap")
    
    size_mb = package_path.stat().st_size / (1024 * 1024)
    log_success(f"완전한 패키지 생성 완료: {package_path} ({size_mb:.1f} MB)")
    
    return package_path

def main():
    print("=" * 60)
    print("SDC 완전한 Air-gap 패키지 생성기")
    print("모든 의존성 포함 (.git만 제외)")
    print("=" * 60)
    
    project_root = Path.cwd()
    staging_dir = project_root / "staging-complete"
    output_dir = project_root / "release"
    
    try:
        # Clean staging
        if staging_dir.exists():
            log_info("기존 staging 디렉토리 정리 중...")
            shutil.rmtree(staging_dir)
        ensure_directory(staging_dir)
        
        # Copy complete project
        log_info("1단계: 완전한 프로젝트 복사...")
        copy_complete_project(project_root, staging_dir)
        
        # Create installation tools
        log_info("2단계: 설치 도구 생성...")
        create_complete_install_script(staging_dir)
        create_complete_readme(staging_dir)
        
        # Create final package
        log_info("3단계: 최종 패키지 생성...")
        package_path = create_complete_package(staging_dir, output_dir)
        
        # Calculate final sizes
        staging_size_gb = sum(f.stat().st_size for f in staging_dir.rglob('*') if f.is_file()) / (1024**3)
        package_size_gb = package_path.stat().st_size / (1024**3)
        
        # Cleanup
        shutil.rmtree(staging_dir)
        
        print()
        print("=" * 60)
        log_success("완전한 Air-gap 패키지 생성 완료!")
        print("=" * 60)
        print()
        print(f"📦 패키지: {package_path}")
        print(f"📏 압축 크기: {package_size_gb:.1f} GB")
        print(f"📏 해제 크기: {staging_size_gb:.1f} GB")
        print()
        print("✅ 포함된 모든 내용:")
        print("  • 완전한 소스 코드")
        print("  • Python 가상환경 (backend/venv)")
        print("  • Node.js 의존성 (frontend/node_modules)")
        print("  • 모든 서비스 의존성")
        print("  • 즉시 실행 가능한 개발환경")
        print()
        print("🚀 Air-gap 서버 설치:")
        print("  1. tar -xzf sdc-complete-airgap-*.tar.gz")
        print("  2. cd sdc-complete-airgap")
        print("  3. sudo ./install_complete_airgap.sh")
        print("  4. 즉시 개발 시작!")
        
    except Exception as e:
        log_error(f"패키지 생성 실패: {e}")
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise

if __name__ == "__main__":
    main()