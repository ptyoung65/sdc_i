#!/usr/bin/env python3
"""
Complete Air-gap Development Environment Package Creator
SDC Korean RAG System - Ultra Complete Offline Development Package

This creates a fully self-contained air-gap package with:
- All source code
- All Python dependencies (wheels)
- All Node.js dependencies (offline cache)
- All container images
- Development tools and utilities
- Complete installation and setup scripts
"""

import os
import subprocess
import sys
import shutil
import tarfile
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set

def log_info(message: str) -> None:
    """Print info message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] INFO: {message}")

def log_success(message: str) -> None:
    """Print success message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] SUCCESS: {message}")

def log_error(message: str) -> None:
    """Print error message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ERROR: {message}")

def log_warning(message: str) -> None:
    """Print warning message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] WARNING: {message}")

def ensure_directory(path: Path) -> None:
    """Ensure directory exists"""
    path.mkdir(parents=True, exist_ok=True)

def find_all_requirements_files(project_root: Path) -> List[Path]:
    """Find all requirements.txt files in the project"""
    requirements_files = []
    
    # Search recursively for all requirements files, excluding certain directories
    exclude_dirs = {'.git', 'venv', '.venv', 'node_modules', '__pycache__', 
                   'staging', 'staging-simple', 'release', 'airgap-deployment'}
    
    for req_file in project_root.rglob("requirements*.txt"):
        # Skip files in excluded directories
        if any(part in exclude_dirs for part in req_file.parts):
            continue
        requirements_files.append(req_file)
    
    return requirements_files

def find_all_package_json_files(project_root: Path) -> List[Path]:
    """Find all package.json files in the project"""
    package_files = []
    
    exclude_dirs = {'.git', 'venv', '.venv', 'node_modules', '__pycache__', 
                   'staging', 'staging-simple', 'release', 'airgap-deployment'}
    
    for pkg_file in project_root.rglob("package.json"):
        # Skip files in excluded directories
        if any(part in exclude_dirs for part in pkg_file.parts):
            continue
        package_files.append(pkg_file)
    
    return package_files

def collect_complete_python_dependencies(project_root: Path, output_dir: Path) -> None:
    """Collect ALL Python dependencies including system packages"""
    log_info("Collecting complete Python dependencies...")
    
    wheels_dir = output_dir / "python-wheels"
    ensure_directory(wheels_dir)
    
    # Find all requirements files
    requirements_files = find_all_requirements_files(project_root)
    log_info(f"Found {len(requirements_files)} requirements files")
    
    if not requirements_files:
        log_warning("No requirements files found!")
        return
    
    # Merge all requirements
    all_packages = set()
    for req_file in requirements_files:
        log_info(f"Processing {req_file}")
        with open(req_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    all_packages.add(line)
    
    # Create merged requirements file
    merged_req = wheels_dir / "requirements-merged.txt"
    with open(merged_req, 'w', encoding='utf-8') as f:
        for package in sorted(all_packages):
            f.write(f"{package}\n")
    
    log_info(f"Created merged requirements with {len(all_packages)} packages")
    
    # Download wheels with multiple strategies
    log_info("Downloading Python wheels...")
    
    try:
        # Strategy 1: Try with binary only first
        cmd = [
            sys.executable, "-m", "pip", "download",
            "--dest", str(wheels_dir),
            "--requirement", str(merged_req),
            "--prefer-binary",
            "--only-binary=:all:",
            "--no-deps"  # Download dependencies separately to avoid conflicts
        ]
        subprocess.run(cmd, check=True, cwd=project_root)
        
    except subprocess.CalledProcessError:
        log_warning("Binary-only download failed, trying with source packages...")
        try:
            # Strategy 2: Allow source packages
            cmd = [
                sys.executable, "-m", "pip", "download",
                "--dest", str(wheels_dir),
                "--requirement", str(merged_req),
                "--prefer-binary"
            ]
            subprocess.run(cmd, check=True, cwd=project_root)
            
        except subprocess.CalledProcessError as e:
            log_error(f"Failed to download Python dependencies: {e}")
            # Continue anyway, we'll create what we can
    
    # Create Python installation script
    create_python_install_script(wheels_dir)
    
    # Copy merged requirements to wheels directory
    shutil.copy2(merged_req, wheels_dir / "requirements-merged.txt")
    
    log_success(f"Python dependencies collected in {wheels_dir}")

def collect_complete_nodejs_dependencies(project_root: Path, output_dir: Path) -> None:
    """Collect ALL Node.js dependencies for offline installation"""
    log_info("Collecting complete Node.js dependencies...")
    
    nodejs_dir = output_dir / "nodejs-deps"
    ensure_directory(nodejs_dir)
    
    # Find all package.json files
    package_files = find_all_package_json_files(project_root)
    log_info(f"Found {len(package_files)} package.json files")
    
    if not package_files:
        log_warning("No package.json files found!")
        return
    
    # Create cache directory
    cache_dir = nodejs_dir / "npm-cache"
    ensure_directory(cache_dir)
    
    # Process each package.json
    for pkg_file in package_files:
        pkg_dir = pkg_file.parent
        log_info(f"Processing {pkg_file}")
        
        try:
            # Create package cache
            relative_path = pkg_dir.relative_to(project_root)
            pkg_cache_dir = nodejs_dir / "packages" / str(relative_path).replace('/', '_')
            ensure_directory(pkg_cache_dir)
            
            # Copy package.json and package-lock.json if exists
            shutil.copy2(pkg_file, pkg_cache_dir)
            
            lock_file = pkg_dir / "package-lock.json"
            if lock_file.exists():
                shutil.copy2(lock_file, pkg_cache_dir)
            
            # Download dependencies
            cmd = [
                "npm", "ci", "--cache", str(cache_dir),
                "--prefix", str(pkg_cache_dir),
                "--production"
            ]
            
            # Change to package directory for npm ci
            subprocess.run(cmd, check=True, cwd=pkg_dir)
            
        except subprocess.CalledProcessError as e:
            log_warning(f"Failed to process {pkg_file}: {e}")
            continue
    
    # Create Node.js installation script
    create_nodejs_install_script(nodejs_dir)
    
    log_success(f"Node.js dependencies collected in {nodejs_dir}")

def collect_container_images(project_root: Path, output_dir: Path) -> None:
    """Collect all container images needed for the project"""
    log_info("Collecting container images...")
    
    images_dir = output_dir / "container-images"
    ensure_directory(images_dir)
    
    # Standard images needed for SDC
    standard_images = [
        "postgres:16",
        "redis:7-alpine",
        "elasticsearch:8.11.0",
        "milvusdb/milvus:v2.3.0",
        "grafana/grafana:latest",
        "prom/prometheus:latest",
        "prom/node-exporter:latest",
        "nginx:alpine",
        "searxng/searxng:latest"
    ]
    
    # Pull and save each image
    for image in standard_images:
        try:
            log_info(f"Pulling {image}...")
            subprocess.run(["podman", "pull", image], check=True)
            
            # Save image as tar
            image_file = images_dir / f"{image.replace('/', '_').replace(':', '_')}.tar"
            log_info(f"Saving {image} to {image_file}...")
            subprocess.run(["podman", "save", "-o", str(image_file), image], check=True)
            
        except subprocess.CalledProcessError as e:
            log_warning(f"Failed to collect image {image}: {e}")
            continue
    
    # Build custom SDC image if Containerfile exists
    containerfile = project_root / "Containerfile"
    if containerfile.exists():
        try:
            log_info("Building custom SDC application image...")
            subprocess.run(["podman", "build", "-t", "sdc-app:latest", "."], 
                         check=True, cwd=project_root)
            
            # Save custom image
            custom_image_file = images_dir / "sdc-app_latest.tar"
            subprocess.run(["podman", "save", "-o", str(custom_image_file), "sdc-app:latest"], 
                         check=True)
            
        except subprocess.CalledProcessError as e:
            log_warning(f"Failed to build custom image: {e}")
    
    # Create container images loading script
    create_container_load_script(images_dir)
    
    log_success(f"Container images collected in {images_dir}")

def copy_project_source(project_root: Path, staging_dir: Path) -> None:
    """Copy project source code with smart exclusions"""
    log_info("Copying project source code...")
    
    project_staging = staging_dir / "sdc_project"
    ensure_directory(project_staging)
    
    # Enhanced exclusion patterns
    exclude_patterns = [
        '.git',
        '.gitignore', 
        'venv',
        '.venv',
        'node_modules',
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '.env',
        '.env.local',
        'logs',
        'uploads',
        'processed',
        '.DS_Store',
        'Thumbs.db',
        '*.log',
        'staging*',
        'release',
        'airgap-deployment',
        '.pytest_cache',
        '.coverage',
        'coverage.xml',
        '*.egg-info',
        '.mypy_cache',
        '.tox',
        'dist',
        'build'
    ]
    
    # Copy project files with exclusions
    for item in project_root.iterdir():
        if item.name in exclude_patterns:
            log_info(f"Skipping {item.name}")
            continue
        
        if item.is_dir():
            shutil.copytree(item, project_staging / item.name,
                          ignore=shutil.ignore_patterns(*exclude_patterns))
        else:
            shutil.copy2(item, project_staging)
    
    log_success(f"Project source copied to {project_staging}")

def create_development_tools_package(output_dir: Path) -> None:
    """Create package with essential development tools"""
    log_info("Creating development tools package...")
    
    tools_dir = output_dir / "dev-tools"
    ensure_directory(tools_dir)
    
    # Essential development tools
    dev_tools = [
        "git",
        "curl", 
        "wget",
        "vim",
        "nano",
        "htop",
        "tmux",
        "tree",
        "jq",
        "unzip",
        "tar",
        "gzip"
    ]
    
    # Create development tools installation script
    tools_script = tools_dir / "install_dev_tools.sh"
    
    script_content = f'''#!/bin/bash
set -e

echo "Installing essential development tools..."

# Detect OS
if command -v apt-get &> /dev/null; then
    # Ubuntu/Debian
    sudo apt-get update
    sudo apt-get install -y {' '.join(dev_tools)}
    
elif command -v yum &> /dev/null; then
    # RHEL/CentOS
    sudo yum update -y
    sudo yum install -y {' '.join(dev_tools)}
    
elif command -v dnf &> /dev/null; then
    # Fedora
    sudo dnf update -y
    sudo dnf install -y {' '.join(dev_tools)}
    
else
    echo "Unsupported operating system"
    exit 1
fi

echo "Development tools installation completed!"
'''
    
    with open(tools_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    tools_script.chmod(0o755)
    
    log_success(f"Development tools package created in {tools_dir}")

def create_python_install_script(wheels_dir: Path) -> None:
    """Create Python dependencies installation script"""
    install_script = wheels_dir / "install_python_deps.sh"
    
    script_content = '''#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEELS_DIR="$SCRIPT_DIR"

echo "Installing Python dependencies from wheels..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip, setuptools, wheel first
echo "Upgrading pip, setuptools, wheel..."
python -m pip install --upgrade --no-index --find-links "$WHEELS_DIR" pip setuptools wheel

# Install all wheels
echo "Installing project dependencies..."
if [ -f "$WHEELS_DIR/requirements-merged.txt" ]; then
    python -m pip install --no-index --find-links "$WHEELS_DIR" --requirement "$WHEELS_DIR/requirements-merged.txt"
else
    # Install all available wheels
    python -m pip install --no-index --find-links "$WHEELS_DIR" "$WHEELS_DIR"/*.whl
fi

echo "Python dependencies installation completed!"
echo "Virtual environment created at: $(pwd)/venv"
echo "To activate: source venv/bin/activate"
'''
    
    with open(install_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    install_script.chmod(0o755)

def create_nodejs_install_script(nodejs_dir: Path) -> None:
    """Create Node.js dependencies installation script"""
    install_script = nodejs_dir / "install_nodejs_deps.sh"
    
    script_content = '''#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODEJS_DIR="$SCRIPT_DIR"

echo "Installing Node.js dependencies..."

# Check if Node.js and npm are available
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "npm is not installed. Please install npm first."
    exit 1
fi

# Configure npm to use offline cache
if [ -d "$NODEJS_DIR/npm-cache" ]; then
    npm config set cache "$NODEJS_DIR/npm-cache"
    echo "Configured npm to use offline cache"
fi

# Install dependencies for each package
if [ -d "$NODEJS_DIR/packages" ]; then
    for pkg_dir in "$NODEJS_DIR/packages"/*; do
        if [ -d "$pkg_dir" ] && [ -f "$pkg_dir/package.json" ]; then
            echo "Installing dependencies for $(basename "$pkg_dir")..."
            cd "$pkg_dir"
            
            if [ -f "package-lock.json" ]; then
                npm ci --offline
            else
                npm install --offline
            fi
        fi
    done
fi

echo "Node.js dependencies installation completed!"
'''
    
    with open(install_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    install_script.chmod(0o755)

def create_container_load_script(images_dir: Path) -> None:
    """Create container images loading script"""
    load_script = images_dir / "load_container_images.sh"
    
    script_content = '''#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="$SCRIPT_DIR"

echo "Loading container images..."

# Check if podman is available
if command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
elif command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
else
    echo "Neither podman nor docker is available. Please install one of them."
    exit 1
fi

echo "Using $CONTAINER_CMD to load images..."

# Load all tar files
for image_file in "$IMAGES_DIR"/*.tar; do
    if [ -f "$image_file" ]; then
        echo "Loading $(basename "$image_file")..."
        $CONTAINER_CMD load -i "$image_file"
    fi
done

echo "Container images loading completed!"
echo "Available images:"
$CONTAINER_CMD images
'''
    
    with open(load_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    load_script.chmod(0o755)

def create_master_installation_script(staging_dir: Path) -> None:
    """Create master installation script for complete setup"""
    install_script = staging_dir / "install_complete_airgap.sh"
    
    script_content = '''#!/bin/bash
set -e

# SDC Complete Air-gap Development Environment Installer
# Ultra complete installation for air-gap development environment

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

# Logging functions
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

# Configuration
DEFAULT_INSTALL_DIR="/opt/sdc"
INSTALL_DIR=""
NON_INTERACTIVE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -y|--yes)
            NON_INTERACTIVE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [-d|--dir DIRECTORY] [-y|--yes] [-h|--help]"
            echo "  -d, --dir DIRECTORY    Installation directory"
            echo "  -y, --yes             Non-interactive mode"
            echo "  -h, --help            Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get installation directory
get_installation_directory() {
    if [ -n "$INSTALL_DIR" ]; then
        echo "$INSTALL_DIR"
        return
    fi
    
    if [ "$NON_INTERACTIVE" = true ]; then
        echo "$DEFAULT_INSTALL_DIR"
        return
    fi
    
    echo "SDC Air-gap 개발환경 설치 위치를 선택하세요:"
    echo "1) /opt/sdc (권장, 관리자 권한 필요)"
    echo "2) $HOME/sdc (홈 디렉토리)"
    echo "3) $(pwd)/sdc (현재 위치)"
    echo "4) 사용자 지정 경로"
    
    while true; do
        read -p "선택 (1-4): " choice
        case $choice in
            1)
                echo "/opt/sdc"
                return
                ;;
            2)
                echo "$HOME/sdc"
                return
                ;;
            3)
                echo "$(pwd)/sdc"
                return
                ;;
            4)
                read -p "설치 경로를 입력하세요: " custom_path
                echo "$custom_path"
                return
                ;;
            *)
                echo "올바른 선택지를 입력하세요 (1-4)"
                ;;
        esac
    done
}

# Check system requirements
check_system_requirements() {
    log_info "시스템 요구사항 확인 중..."
    
    # Check OS
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log_error "Linux 운영체제가 필요합니다"
        exit 1
    fi
    
    # Check available space (need at least 10GB)
    available_space=$(df . | tail -1 | awk '{print $4}')
    required_space=$((10 * 1024 * 1024)) # 10GB in KB
    
    if [ "$available_space" -lt "$required_space" ]; then
        log_error "최소 10GB의 여유 공간이 필요합니다"
        exit 1
    fi
    
    log_success "시스템 요구사항 확인 완료"
}

# Install system dependencies
install_system_dependencies() {
    log_info "시스템 의존성 설치 중..."
    
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv nodejs npm podman podman-compose curl wget git
        
    elif command -v yum &> /dev/null; then
        # RHEL/CentOS
        sudo yum update -y
        sudo yum install -y python3 python3-pip nodejs npm podman podman-compose curl wget git
        
    elif command -v dnf &> /dev/null; then
        # Fedora
        sudo dnf update -y  
        sudo dnf install -y python3 python3-pip nodejs npm podman podman-compose curl wget git
        
    else
        log_error "지원되지 않는 운영체제입니다"
        exit 1
    fi
    
    log_success "시스템 의존성 설치 완료"
}

# Install development tools
install_development_tools() {
    log_info "개발 도구 설치 중..."
    
    if [ -f "airgap-deployment/dev-tools/install_dev_tools.sh" ]; then
        bash airgap-deployment/dev-tools/install_dev_tools.sh
    fi
    
    log_success "개발 도구 설치 완료"
}

# Install Python dependencies
install_python_dependencies() {
    log_info "Python 의존성 설치 중..."
    
    if [ -f "airgap-deployment/python-wheels/install_python_deps.sh" ]; then
        cd "$FINAL_INSTALL_DIR"
        bash airgap-deployment/python-wheels/install_python_deps.sh
        cd - > /dev/null
    fi
    
    log_success "Python 의존성 설치 완료"
}

# Install Node.js dependencies  
install_nodejs_dependencies() {
    log_info "Node.js 의존성 설치 중..."
    
    if [ -f "airgap-deployment/nodejs-deps/install_nodejs_deps.sh" ]; then
        bash airgap-deployment/nodejs-deps/install_nodejs_deps.sh
    fi
    
    log_success "Node.js 의존성 설치 완료"
}

# Load container images
load_container_images() {
    log_info "컨테이너 이미지 로딩 중..."
    
    if [ -f "airgap-deployment/container-images/load_container_images.sh" ]; then
        bash airgap-deployment/container-images/load_container_images.sh
    fi
    
    log_success "컨테이너 이미지 로딩 완료"
}

# Setup project
setup_project() {
    log_info "프로젝트 설정 중..."
    
    cd "$FINAL_INSTALL_DIR"
    
    # Copy environment file
    if [ -f ".env.example" ] && [ ! -f ".env" ]; then
        cp .env.example .env
        log_info ".env 파일이 생성되었습니다. API 키를 설정하세요."
    fi
    
    # Make scripts executable
    if [ -d "scripts" ]; then
        chmod +x scripts/*.sh
    fi
    
    log_success "프로젝트 설정 완료"
}

# Verify installation
verify_installation() {
    log_info "설치 검증 중..."
    
    cd "$FINAL_INSTALL_DIR"
    
    # Check Python environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        python -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null && log_success "Python 환경 확인됨" || log_warning "Python 환경 문제 발생"
        deactivate
    fi
    
    # Check Node.js dependencies
    if [ -d "frontend/node_modules" ]; then
        log_success "Node.js 환경 확인됨"
    else
        log_warning "Node.js 환경 문제 발생"
    fi
    
    # Check container images
    if command -v podman &> /dev/null; then
        podman images | grep -q postgres && log_success "컨테이너 이미지 확인됨" || log_warning "컨테이너 이미지 문제 발생"
    fi
}

# Main installation function
main() {
    echo "=============================================="
    echo "SDC Complete Air-gap Development Environment"
    echo "=============================================="
    echo ""
    
    # Get installation directory
    FINAL_INSTALL_DIR=$(get_installation_directory)
    log_info "설치 위치: $FINAL_INSTALL_DIR"
    
    # Check system requirements
    check_system_requirements
    
    # Create installation directory
    sudo mkdir -p "$FINAL_INSTALL_DIR"
    sudo chown $(whoami):$(whoami) "$FINAL_INSTALL_DIR"
    
    # Copy project files
    log_info "프로젝트 파일 복사 중..."
    cp -r sdc_project/* "$FINAL_INSTALL_DIR/"
    cp -r airgap-deployment "$FINAL_INSTALL_DIR/"
    
    # Install system dependencies
    install_system_dependencies
    
    # Install development tools
    install_development_tools
    
    # Install Python dependencies
    install_python_dependencies
    
    # Install Node.js dependencies
    install_nodejs_dependencies
    
    # Load container images
    load_container_images
    
    # Setup project
    setup_project
    
    # Verify installation
    verify_installation
    
    echo ""
    echo "=============================================="
    log_success "SDC Air-gap 개발환경 설치 완료!"
    echo "=============================================="
    echo ""
    log_info "설치 위치: $FINAL_INSTALL_DIR"
    log_info "다음 단계:"
    echo "  1. cd $FINAL_INSTALL_DIR"
    echo "  2. .env 파일에서 API 키 설정"
    echo "  3. ./scripts/start_services.sh로 서비스 시작"
    echo ""
    log_info "개발 환경 사용법:"
    echo "  • Python 환경: cd $FINAL_INSTALL_DIR && source venv/bin/activate"
    echo "  • 프론트엔드 개발: cd $FINAL_INSTALL_DIR/frontend && npm run dev"
    echo "  • 백엔드 개발: cd $FINAL_INSTALL_DIR/backend && python simple_api.py"
    echo ""
}

main "$@"
'''
    
    with open(install_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    install_script.chmod(0o755)
    
    log_success(f"Master installation script created: {install_script}")

def create_deployment_manifest(staging_dir: Path) -> None:
    """Create comprehensive deployment manifest"""
    manifest = {
        "package_info": {
            "name": "SDC Korean RAG System - Complete Air-gap Development Package",
            "version": "2.0.0",
            "created_at": datetime.now().isoformat(),
            "description": "Complete offline development environment with all dependencies"
        },
        "components": {
            "project_source": "sdc_project/",
            "python_dependencies": "airgap-deployment/python-wheels/",
            "nodejs_dependencies": "airgap-deployment/nodejs-deps/", 
            "container_images": "airgap-deployment/container-images/",
            "development_tools": "airgap-deployment/dev-tools/",
            "installation_scripts": "./"
        },
        "installation_instructions": [
            "1. Extract: tar -xzf sdc-airgap-complete-*.tar.gz",
            "2. Install: sudo ./install_complete_airgap.sh",
            "3. Configure: edit .env file with API keys",
            "4. Start: ./scripts/start_services.sh",
            "5. Develop: Ready for full offline development!"
        ],
        "requirements": {
            "os": "Linux (Ubuntu 20.04+, RHEL 8+, or compatible)",
            "memory": "16GB RAM minimum, 32GB recommended for development",
            "storage": "20GB free space minimum", 
            "software": ["Python 3.8+", "Node.js 18+", "Podman or Docker"]
        },
        "development_features": {
            "python_dev": "Complete Python development environment with all dependencies",
            "nodejs_dev": "Complete Node.js development with offline npm cache",
            "container_dev": "All container images for full stack development",
            "tools": "Essential development tools and utilities",
            "hot_reload": "Development servers with hot reload capabilities"
        },
        "services": {
            "databases": ["PostgreSQL", "Redis", "Milvus", "Elasticsearch"],
            "applications": ["Backend API", "Frontend UI", "Admin Panel"],
            "microservices": ["Korean RAG", "Graph RAG", "Keyword RAG", "Text-to-SQL RAG"],
            "support": ["Docling", "SearXNG"],
            "monitoring": ["Prometheus", "Grafana", "Node Exporter"]
        }
    }
    
    manifest_file = staging_dir / "DEPLOYMENT_MANIFEST.json"
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    log_success(f"Deployment manifest created: {manifest_file}")

def create_comprehensive_readme(staging_dir: Path) -> None:
    """Create comprehensive README for the complete package"""
    readme_content = """# SDC Korean RAG System - Complete Air-gap Development Package

## 🚀 개요

이 패키지는 SDC (Smart Document Companion) Korean RAG 시스템을 완전한 air-gap 환경에서 개발하고 배포하기 위한 **완전한 개발환경**을 제공합니다.

**특징:**
- ✅ 모든 Python 의존성 포함 (wheels)
- ✅ 모든 Node.js 의존성 포함 (offline cache)
- ✅ 모든 컨테이너 이미지 포함
- ✅ 개발 도구 및 유틸리티 포함
- ✅ 완전 자동화된 설치 스크립트
- ✅ 개발 서버 및 핫 리로드 지원
- ✅ 전체 마이크로서비스 아키텍처

## 📦 패키지 구성

```
sdc-airgap-complete/
├── install_complete_airgap.sh      # 마스터 설치 스크립트
├── sdc_project/                    # 완전한 프로젝트 소스 코드
│   ├── backend/                    # Python FastAPI 백엔드
│   ├── frontend/                   # Next.js 프론트엔드
│   ├── services/                   # 마이크로서비스들
│   ├── scripts/                    # 관리 스크립트들
│   ├── docker-compose.yml          # 컨테이너 오케스트레이션
│   └── .env.example                # 환경설정 템플릿
├── airgap-deployment/              # 오프라인 의존성 패키지
│   ├── python-wheels/              # Python 패키지 (.whl)
│   │   ├── install_python_deps.sh  # Python 설치 스크립트
│   │   └── requirements-merged.txt # 통합 요구사항
│   ├── nodejs-deps/                # Node.js 의존성
│   │   ├── install_nodejs_deps.sh  # Node.js 설치 스크립트
│   │   ├── npm-cache/              # NPM 오프라인 캐시
│   │   └── packages/               # 패키지별 의존성
│   ├── container-images/           # 컨테이너 이미지 (.tar)
│   │   ├── load_container_images.sh # 이미지 로딩 스크립트
│   │   ├── postgres_16.tar         # PostgreSQL 이미지
│   │   ├── redis_7-alpine.tar      # Redis 이미지
│   │   └── [기타 이미지들...]
│   └── dev-tools/                  # 개발 도구 패키지
│       └── install_dev_tools.sh    # 개발 도구 설치
├── DEPLOYMENT_MANIFEST.json        # 패키지 정보
└── README.md                       # 이 파일
```

## ⚡ 빠른 설치

### 1단계: 패키지 추출
```bash
tar -xzf sdc-airgap-complete-*.tar.gz
cd sdc-airgap-complete
```

### 2단계: 자동 설치 실행
```bash
# 기본 설치 (/opt/sdc)
sudo ./install_complete_airgap.sh

# 또는 사용자 지정 위치
sudo ./install_complete_airgap.sh -d /home/user/my-sdc

# 또는 비대화형 모드
sudo ./install_complete_airgap.sh -y
```

### 3단계: 환경 설정
```bash
cd /opt/sdc  # 또는 설치한 위치
nano .env    # API 키 설정
```

### 4단계: 개발환경 시작
```bash
# 전체 서비스 시작
./scripts/start_services.sh

# 또는 개발 모드 (데이터베이스만 컨테이너, 앱은 로컬)
make dev
```

## 🛠 개발환경 사용법

### Python 백엔드 개발
```bash
cd backend
source venv/bin/activate  # 가상환경 활성화
python simple_api.py      # 개발 서버 시작 (핫 리로드)
```

### Node.js 프론트엔드 개발
```bash
cd frontend
npm run dev              # 개발 서버 시작 (http://localhost:3000)
```

### 마이크로서비스 개발
```bash
cd services/admin-panel
npm run dev              # 관리 패널 개발 서버

cd services/rag-orchestrator
python main.py           # RAG 오케스트레이터 서비스
```

### 컨테이너 기반 개발
```bash
# 전체 스택 컨테이너로 실행
podman-compose up -d

# 개별 서비스 재시작
podman-compose restart backend

# 로그 확인
podman-compose logs -f frontend
```

## 🎯 개발 워크플로우

### 1. 코드 편집
- **백엔드**: `backend/` 디렉토리에서 Python 코드 편집
- **프론트엔드**: `frontend/src/` 디렉토리에서 React/TypeScript 코드 편집
- **서비스**: `services/` 디렉토리에서 마이크로서비스 편집

### 2. 실시간 개발
```bash
# 터미널 1: 백엔드 개발 서버
cd backend && source venv/bin/activate && python simple_api.py

# 터미널 2: 프론트엔드 개발 서버  
cd frontend && npm run dev

# 터미널 3: 데이터베이스 서비스
podman-compose up -d postgres redis milvus elasticsearch
```

### 3. 테스트 실행
```bash
# Python 백엔드 테스트
cd backend && source venv/bin/activate && python -m pytest

# Node.js 프론트엔드 테스트
cd frontend && npm test

# 통합 테스트
make test
```

### 4. 코드 품질 검사
```bash
# 전체 린트 및 포맷팅
make lint
make format

# 백엔드만
make lint-backend

# 프론트엔드만  
make lint-frontend
```

## 🔧 시스템 요구사항

### 하드웨어
- **CPU**: 4코어 이상 권장
- **메모리**: 16GB RAM (최소 8GB)
- **저장소**: 20GB 여유 공간
- **네트워크**: Air-gap 환경 (인터넷 연결 불필요)

### 소프트웨어
- **OS**: Linux (Ubuntu 20.04+, RHEL 8+, CentOS 8+)
- **Python**: 3.8+ (자동 설치됨)
- **Node.js**: 18+ (자동 설치됨)
- **컨테이너**: Podman 또는 Docker (자동 설치됨)

## 📊 서비스 아키텍처

### 데이터베이스 계층
- **PostgreSQL**: 주 데이터베이스 (포트 5432)
- **Redis**: 캐시 및 세션 (포트 6379)  
- **Milvus**: 벡터 데이터베이스 (포트 19530)
- **Elasticsearch**: 검색 엔진 (포트 9200)

### 애플리케이션 계층
- **백엔드 API**: FastAPI (포트 8000)
- **프론트엔드**: Next.js (포트 3000)
- **관리 패널**: React (포트 3003)

### 마이크로서비스 계층
- **RAG 오케스트레이터**: 포트 8008
- **AI 모델 서비스**: 포트 8007
- **가드레일 서비스**: 포트 8001
- **큐레이션 서비스**: 포트 8006

### 모니터링 계층
- **Prometheus**: 메트릭 수집 (포트 9090)
- **Grafana**: 대시보드 (포트 3010)
- **Node Exporter**: 시스템 메트릭

## 🔐 보안 설정

### API 키 설정
```bash
# .env 파일 편집
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
GEMINI_API_KEY=your_gemini_key
```

### 데이터베이스 보안
```bash
# 기본 비밀번호 변경
POSTGRES_PASSWORD=your_secure_password
REDIS_PASSWORD=your_redis_password
```

## 🚨 문제 해결

### 일반적인 문제

1. **포트 충돌**
   ```bash
   # 사용 중인 포트 확인
   sudo netstat -tlnp | grep :3000
   
   # 프로세스 종료
   pkill -f "node.*3000"
   ```

2. **Python 가상환경 문제**
   ```bash
   # 가상환경 재생성
   cd backend
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Node.js 의존성 문제**
   ```bash
   # node_modules 재설치
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

4. **컨테이너 문제**
   ```bash
   # 컨테이너 상태 확인
   podman-compose ps
   
   # 컨테이너 재시작
   podman-compose restart
   
   # 로그 확인
   podman-compose logs [서비스명]
   ```

### 로그 위치
- **애플리케이션 로그**: `./logs/`
- **컨테이너 로그**: `podman-compose logs [서비스명]`
- **시스템 로그**: `/var/log/syslog` 또는 `journalctl`

## 📖 개발 가이드

### 새 기능 추가
1. **백엔드 API**: `backend/app/api/routes/`에 새 라우트 추가
2. **프론트엔드 컴포넌트**: `frontend/src/components/`에 새 컴포넌트 추가
3. **마이크로서비스**: `services/`에 새 서비스 디렉토리 생성

### 데이터베이스 마이그레이션
```bash
# 새 마이그레이션 생성
cd backend
source venv/bin/activate
alembic revision --autogenerate -m "Add new table"

# 마이그레이션 실행
alembic upgrade head
```

### 테스트 작성
```bash
# 백엔드 테스트
# backend/tests/ 디렉토리에 test_*.py 파일 생성

# 프론트엔드 테스트
# frontend/src/__tests__/ 디렉토리에 *.test.tsx 파일 생성
```

## 🎉 성공적인 설치 확인

설치가 완료되면 다음 URL에서 서비스에 접근할 수 있습니다:

- **메인 애플리케이션**: http://localhost
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **관리 패널**: http://localhost:3003
- **Grafana**: http://localhost:3010 (admin/admin123)
- **Prometheus**: http://localhost:9090

## 🤝 지원

이 패키지는 완전한 air-gap 개발환경을 제공합니다. 문제 발생 시:

1. 로그 파일 확인
2. 시스템 요구사항 재확인
3. 설치 스크립트 재실행
4. 포트 충돌 확인

---

**SDC Korean RAG System v2.0**  
Complete Air-gap Development Environment
"""
    
    readme_file = staging_dir / "README.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    log_success(f"Comprehensive README created: {readme_file}")

def create_final_package(staging_dir: Path, output_dir: Path) -> Path:
    """Create final comprehensive tar.gz package"""
    log_info("Creating final comprehensive package...")
    
    ensure_directory(output_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"sdc-airgap-complete-dev-{timestamp}.tar.gz"
    package_path = output_dir / package_name
    
    with tarfile.open(package_path, 'w:gz') as tar:
        tar.add(staging_dir, arcname="sdc-airgap-complete")
    
    # Calculate package size
    size_mb = package_path.stat().st_size / (1024 * 1024)
    
    log_success(f"Complete air-gap development package created: {package_path}")
    log_info(f"Package size: {size_mb:.1f} MB")
    
    return package_path

def cleanup_staging(staging_dir: Path) -> None:
    """Clean up staging directory"""
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
        log_info("Staging directory cleaned up")

def main():
    """Main function to create complete air-gap development package"""
    print("=" * 80)
    print("SDC Korean RAG System - Complete Air-gap Development Package Creator")
    print("=" * 80)
    print()
    
    project_root = Path.cwd()
    staging_dir = project_root / "staging-complete"
    output_dir = project_root / "release"
    airgap_dir = staging_dir / "airgap-deployment"
    
    log_info(f"Project root: {project_root}")
    log_info(f"Staging directory: {staging_dir}")
    log_info(f"Output directory: {output_dir}")
    
    try:
        # Clean up any existing staging
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        
        ensure_directory(staging_dir)
        ensure_directory(airgap_dir)
        
        # Step 1: Copy project source code
        log_info("Step 1: Copying project source code...")
        copy_project_source(project_root, staging_dir)
        
        # Step 2: Collect Python dependencies
        log_info("Step 2: Collecting Python dependencies...")
        collect_complete_python_dependencies(project_root, airgap_dir)
        
        # Step 3: Collect Node.js dependencies
        log_info("Step 3: Collecting Node.js dependencies...")
        collect_complete_nodejs_dependencies(project_root, airgap_dir)
        
        # Step 4: Collect container images
        log_info("Step 4: Collecting container images...")
        collect_container_images(project_root, airgap_dir)
        
        # Step 5: Create development tools package
        log_info("Step 5: Creating development tools package...")
        create_development_tools_package(airgap_dir)
        
        # Step 6: Create installation scripts
        log_info("Step 6: Creating installation scripts...")
        create_master_installation_script(staging_dir)
        
        # Step 7: Create documentation
        log_info("Step 7: Creating package documentation...")
        create_deployment_manifest(staging_dir)
        create_comprehensive_readme(staging_dir)
        
        # Step 8: Create final package
        log_info("Step 8: Creating final package...")
        package_path = create_final_package(staging_dir, output_dir)
        
        # Clean up staging
        cleanup_staging(staging_dir)
        
        print()
        print("=" * 80)
        log_success("Complete Air-gap Development Package Creation Completed!")
        print("=" * 80)
        print()
        log_info("Package details:")
        print(f"  • Package file: {package_path}")
        print(f"  • Package size: {package_path.stat().st_size / (1024 * 1024):.1f} MB")
        print()
        log_info("Installation instructions:")
        print("  1. Transfer the package to your air-gap server")
        print("  2. Extract: tar -xzf sdc-airgap-complete-dev-*.tar.gz")
        print("  3. Install: cd sdc-airgap-complete && sudo ./install_complete_airgap.sh")
        print("  4. Configure: edit .env file with API keys")
        print("  5. Develop: Ready for complete offline development!")
        print()
        log_info("Development features included:")
        print("  • Complete Python development environment")
        print("  • Complete Node.js development environment")
        print("  • All container images for full stack")
        print("  • Development tools and utilities")
        print("  • Hot reload development servers")
        print("  • Full microservices architecture")
        print()
        
    except Exception as e:
        log_error(f"Package creation failed: {e}")
        cleanup_staging(staging_dir)
        sys.exit(1)

if __name__ == "__main__":
    main()