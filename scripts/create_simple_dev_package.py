#!/usr/bin/env python3
"""
Simple Air-gap Development Package Creator
Ultra-reliable version that works without complex dependency resolution
"""

import os
import subprocess
import sys
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

def copy_source_code(project_root: Path, staging_dir: Path) -> None:
    """Copy source code with minimal exclusions"""
    log_info("Copying source code...")
    
    project_staging = staging_dir / "sdc_project"
    ensure_directory(project_staging)
    
    # Basic exclusions - only what's absolutely necessary
    exclude_patterns = [
        '.git',
        'venv',
        '.venv',
        'node_modules', 
        '__pycache__',
        '*.pyc',
        '.env',
        'logs',
        'uploads',
        'processed',
        'staging*',
        'release',
        'airgap-deployment'
    ]
    
    for item in project_root.iterdir():
        if any(pattern.replace('*', '') in item.name for pattern in exclude_patterns):
            log_info(f"Skipping {item.name}")
            continue
            
        try:
            if item.is_dir():
                shutil.copytree(item, project_staging / item.name,
                              ignore=shutil.ignore_patterns(*exclude_patterns))
            else:
                shutil.copy2(item, project_staging)
        except Exception as e:
            log_error(f"Failed to copy {item.name}: {e}")
            continue
    
    log_success(f"Source code copied to {project_staging}")

def create_install_script(staging_dir: Path) -> None:
    """Create a simple but comprehensive installation script"""
    install_script = staging_dir / "install_airgap_dev.sh"
    
    script_content = '''#!/bin/bash
set -e

# SDC Air-gap Development Environment Installer
echo "=========================================="
echo "SDC Air-gap Development Environment Setup"
echo "=========================================="

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
    echo "1) /opt/sdc (권장)"
    echo "2) $HOME/sdc (홈 디렉토리)"
    echo "3) $(pwd)/sdc (현재 위치)"
    echo "4) 사용자 지정"
    
    read -p "선택 (1-4): " choice
    case $choice in
        1) echo "/opt/sdc" ;;
        2) echo "$HOME/sdc" ;;
        3) echo "$(pwd)/sdc" ;;
        4) read -p "경로 입력: " custom; echo "$custom" ;;
        *) echo "/opt/sdc" ;;
    esac
}

# Install system dependencies
install_system_deps() {
    log_info "시스템 의존성 설치 중..."
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv nodejs npm podman podman-compose git curl wget
    elif command -v yum &> /dev/null; then
        sudo yum update -y
        sudo yum install -y python3 python3-pip nodejs npm podman podman-compose git curl wget
    elif command -v dnf &> /dev/null; then
        sudo dnf update -y
        sudo dnf install -y python3 python3-pip nodejs npm podman podman-compose git curl wget
    else
        log_error "지원되지 않는 운영체제입니다"
        exit 1
    fi
    
    log_success "시스템 의존성 설치 완료"
}

# Setup Python environment
setup_python() {
    log_info "Python 개발환경 설정 중..."
    
    cd "$INSTALL_DIR"
    
    # Backend Python environment
    if [ -d "backend" ]; then
        cd backend
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip setuptools wheel
        
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
        elif [ -f "requirements-minimal.txt" ]; then
            pip install -r requirements-minimal.txt
        fi
        
        deactivate
        cd ..
        log_success "Backend Python 환경 설정 완료"
    fi
    
    # Services Python environments
    if [ -d "services" ]; then
        for service_dir in services/*/; do
            if [ -f "${service_dir}requirements.txt" ]; then
                log_info "Setting up Python env for $(basename $service_dir)"
                cd "$service_dir"
                python3 -m venv venv
                source venv/bin/activate
                pip install --upgrade pip setuptools wheel
                pip install -r requirements.txt
                deactivate
                cd - > /dev/null
            fi
        done
        log_success "Services Python 환경 설정 완료"
    fi
}

# Setup Node.js environment  
setup_nodejs() {
    log_info "Node.js 개발환경 설정 중..."
    
    cd "$INSTALL_DIR"
    
    # Frontend
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        cd frontend
        npm install
        cd ..
        log_success "Frontend 환경 설정 완료"
    fi
    
    # Admin panel and other Node.js services
    if [ -d "services" ]; then
        for service_dir in services/*/; do
            if [ -f "${service_dir}package.json" ]; then
                log_info "Setting up Node.js env for $(basename $service_dir)"
                cd "$service_dir"
                npm install
                cd - > /dev/null
            fi
        done
        log_success "Node.js services 환경 설정 완료"
    fi
}

# Setup configuration files
setup_config() {
    log_info "구성 파일 설정 중..."
    
    cd "$INSTALL_DIR"
    
    # Copy .env.example to .env if exists
    if [ -f ".env.example" ] && [ ! -f ".env" ]; then
        cp .env.example .env
        log_info ".env 파일이 생성되었습니다. API 키를 설정하세요."
    fi
    
    # Make scripts executable
    if [ -d "scripts" ]; then
        chmod +x scripts/*.sh 2>/dev/null || true
    fi
    
    log_success "구성 파일 설정 완료"
}

# Verify installation
verify_setup() {
    log_info "설치 검증 중..."
    
    cd "$INSTALL_DIR"
    
    # Check Python backend
    if [ -f "backend/venv/bin/python" ]; then
        if backend/venv/bin/python -c "import fastapi, uvicorn" 2>/dev/null; then
            log_success "Python 백엔드 환경 확인됨"
        else
            log_warning "Python 백엔드 환경에 문제가 있을 수 있습니다"
        fi
    fi
    
    # Check Node.js frontend
    if [ -d "frontend/node_modules" ]; then
        log_success "Node.js 프론트엔드 환경 확인됨"
    else
        log_warning "Node.js 프론트엔드 환경에 문제가 있을 수 있습니다"
    fi
    
    # Check if Docker/Podman is working
    if command -v podman &> /dev/null; then
        if podman ps &> /dev/null; then
            log_success "Podman 컨테이너 환경 확인됨"
        else
            log_warning "Podman이 제대로 설정되지 않았을 수 있습니다"
        fi
    fi
}

# Main installation
main() {
    INSTALL_DIR=$(get_install_dir "$@")
    log_info "설치 위치: $INSTALL_DIR"
    
    # Create installation directory
    if [[ "$INSTALL_DIR" == /opt/* ]]; then
        sudo mkdir -p "$INSTALL_DIR"
        sudo chown $(whoami):$(whoami) "$INSTALL_DIR"
    else
        mkdir -p "$INSTALL_DIR"
    fi
    
    # Copy project files
    log_info "프로젝트 파일 복사 중..."
    cp -r sdc_project/* "$INSTALL_DIR/"
    
    # Install system dependencies
    install_system_deps
    
    # Setup environments
    setup_python
    setup_nodejs
    setup_config
    
    # Verify
    verify_setup
    
    echo ""
    echo "=============================================="
    log_success "SDC Air-gap 개발환경 설치 완료!"
    echo "=============================================="
    echo ""
    log_info "설치 위치: $INSTALL_DIR"
    echo ""
    log_info "다음 단계:"
    echo "  1. cd $INSTALL_DIR"
    echo "  2. .env 파일에서 API 키 설정"
    echo "  3. 개발 시작!"
    echo ""
    log_info "개발 서버 실행:"
    echo "  • 백엔드: cd backend && source venv/bin/activate && python simple_api.py"
    echo "  • 프론트엔드: cd frontend && npm run dev"
    echo "  • 전체 서비스: podman-compose up (docker-compose.yml 필요)"
    echo ""
}

main "$@"
'''
    
    with open(install_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    install_script.chmod(0o755)
    log_success(f"설치 스크립트 생성: {install_script}")

def create_readme(staging_dir: Path) -> None:
    """Create simple but comprehensive README"""
    readme = staging_dir / "README.md"
    
    readme_content = """# SDC Korean RAG System - Air-gap 개발환경

## 🚀 빠른 시작

### 1. 패키지 추출
```bash
tar -xzf sdc-dev-airgap-*.tar.gz
cd sdc-dev-airgap
```

### 2. 자동 설치
```bash
# 기본 설치
sudo ./install_airgap_dev.sh

# 또는 사용자 지정 위치에 설치
sudo ./install_airgap_dev.sh /your/custom/path
```

### 3. 개발 시작
```bash
cd [설치위치]

# .env 파일 설정 (API 키 등)
nano .env

# 백엔드 개발 서버
cd backend
source venv/bin/activate
python simple_api.py

# 새 터미널에서 프론트엔드 개발 서버
cd frontend
npm run dev
```

## 📋 포함된 내용

- ✅ 전체 소스 코드
- ✅ 자동화된 설치 스크립트
- ✅ 개발환경 설정 도구
- ✅ 종속성 자동 설치

## 🛠 개발 가이드

### Python 백엔드
- 가상환경: `backend/venv/`
- 실행: `python simple_api.py`
- API 문서: http://localhost:8000/docs

### Next.js 프론트엔드
- 개발서버: `npm run dev`
- 접속: http://localhost:3000
- 빌드: `npm run build`

### 마이크로서비스
각 서비스 디렉토리에서:
- Python 서비스: `python main.py`
- Node.js 서비스: `npm run dev`

## 🔧 시스템 요구사항

- Linux (Ubuntu 20.04+, CentOS 8+)
- Python 3.8+
- Node.js 18+
- 8GB+ RAM 권장
- 10GB+ 저장공간

## 📞 지원

설치 중 문제 발생 시:
1. 로그 메시지 확인
2. 시스템 요구사항 재확인  
3. 수동으로 의존성 설치

---
**SDC Korean RAG System**  
Air-gap Development Package
"""
    
    with open(readme, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    log_success(f"README 생성: {readme}")

def create_package(staging_dir: Path, output_dir: Path) -> Path:
    """Create final package"""
    ensure_directory(output_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"sdc-dev-airgap-{timestamp}.tar.gz"
    package_path = output_dir / package_name
    
    with tarfile.open(package_path, 'w:gz') as tar:
        tar.add(staging_dir, arcname="sdc-dev-airgap")
    
    size_mb = package_path.stat().st_size / (1024 * 1024)
    log_success(f"패키지 생성 완료: {package_path} ({size_mb:.1f} MB)")
    
    return package_path

def main():
    print("=" * 60)
    print("SDC Air-gap 개발환경 패키지 생성기")
    print("=" * 60)
    
    project_root = Path.cwd()
    staging_dir = project_root / "staging-simple-dev" 
    output_dir = project_root / "release"
    
    try:
        # Clean and create staging
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        ensure_directory(staging_dir)
        
        # Copy source code
        copy_source_code(project_root, staging_dir)
        
        # Create installation tools
        create_install_script(staging_dir)
        create_readme(staging_dir)
        
        # Create final package
        package_path = create_package(staging_dir, output_dir)
        
        # Cleanup
        shutil.rmtree(staging_dir)
        
        print()
        print("=" * 60)
        log_success("Air-gap 개발환경 패키지 생성 완료!")
        print("=" * 60)
        print()
        print(f"📦 패키지: {package_path}")
        print(f"📏 크기: {package_path.stat().st_size / (1024 * 1024):.1f} MB")
        print()
        print("🚀 사용법:")
        print("1. air-gap 서버로 파일 전송")
        print("2. tar -xzf sdc-dev-airgap-*.tar.gz")
        print("3. cd sdc-dev-airgap")  
        print("4. sudo ./install_airgap_dev.sh")
        print("5. 개발 시작!")
        
    except Exception as e:
        log_error(f"패키지 생성 실패: {e}")
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        sys.exit(1)

if __name__ == "__main__":
    main()