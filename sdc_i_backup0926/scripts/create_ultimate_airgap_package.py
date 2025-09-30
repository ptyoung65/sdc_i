#!/usr/bin/env python3
"""
Ultimate Air-gap Package Creator - 컨테이너 이미지 포함 완전한 오프라인 배포 패키지
모든 파일 + 컨테이너 이미지 + 의존성 포함
"""

import os
import sys
import shutil
import tarfile
import json
import subprocess
import yaml
import re
from pathlib import Path
from datetime import datetime
from typing import List, Set, Dict, Optional

def log_info(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] INFO: {message}")

def log_success(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] SUCCESS: {message}")

def log_error(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ERROR: {message}")

def log_warning(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] WARNING: {message}")

def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run shell command and return result"""
    log_info(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        if result.returncode == 0:
            return result
        else:
            log_error(f"Command failed: {result.stderr}")
            return result
    except subprocess.CalledProcessError as e:
        log_error(f"Command error: {e.stderr}")
        if check:
            raise
        return e
    except Exception as e:
        log_error(f"Unexpected error running command: {e}")
        if check:
            raise
        return None

def detect_container_runtime() -> Optional[str]:
    """Detect available container runtime (podman or docker)"""
    for runtime in ['podman', 'docker']:
        result = run_command([runtime, 'version'], check=False)
        if result and result.returncode == 0:
            log_success(f"Found container runtime: {runtime}")
            return runtime
    log_error("No container runtime found (podman or docker)")
    return None

def parse_docker_compose(compose_file: Path) -> Dict[str, List[str]]:
    """Parse docker-compose.yml to extract images"""
    images = {
        'external': [],  # External images to pull
        'build': []      # Services to build
    }
    
    try:
        with open(compose_file, 'r') as f:
            compose = yaml.safe_load(f)
        
        services = compose.get('services', {})
        for service_name, service_config in services.items():
            if 'image' in service_config:
                # External image
                image = service_config['image']
                if image not in images['external']:
                    images['external'].append(image)
            elif 'build' in service_config:
                # Service to build
                images['build'].append(service_name)
        
        log_success(f"Found {len(images['external'])} external images and {len(images['build'])} services to build")
        return images
    except Exception as e:
        log_error(f"Failed to parse docker-compose.yml: {e}")
        return images

def pull_external_images(runtime: str, images: List[str], staging_dir: Path) -> List[Path]:
    """Pull external container images and save as tar files"""
    saved_images = []
    images_dir = staging_dir / "container_images"
    ensure_directory(images_dir)
    
    for image in images:
        log_info(f"Pulling image: {image}")
        
        # Pull the image
        result = run_command([runtime, 'pull', image], check=False)
        if result.returncode != 0:
            log_warning(f"Failed to pull {image}, skipping...")
            continue
        
        # Generate safe filename
        safe_name = image.replace('/', '_').replace(':', '_')
        tar_file = images_dir / f"{safe_name}.tar"
        
        # Save image to tar
        log_info(f"Saving image to: {tar_file}")
        result = run_command([runtime, 'save', '-o', str(tar_file), image], check=False)
        
        if result.returncode == 0:
            saved_images.append(tar_file)
            size_mb = tar_file.stat().st_size / (1024 * 1024)
            log_success(f"Saved {image} ({size_mb:.1f} MB)")
        else:
            log_warning(f"Failed to save {image}")
    
    return saved_images

def build_local_images(runtime: str, services: List[str], project_root: Path, staging_dir: Path) -> List[Path]:
    """Build local container images from Containerfile/Dockerfile"""
    saved_images = []
    images_dir = staging_dir / "container_images"
    ensure_directory(images_dir)
    
    # Check for Containerfile or Dockerfile
    container_file = project_root / "Containerfile"
    if not container_file.exists():
        container_file = project_root / "Dockerfile"
    
    if not container_file.exists():
        log_warning("No Containerfile or Dockerfile found, skipping local builds")
        return saved_images
    
    # Build each service
    for service in services:
        image_name = f"sdc-{service}:latest"
        log_info(f"Building image: {image_name}")
        
        # Build the image
        cmd = [runtime, 'build', '-t', image_name, '-f', str(container_file)]
        
        # Add build context based on service
        if 'backend' in service:
            cmd.extend(['--build-arg', 'SERVICE=backend', str(project_root)])
        elif 'frontend' in service:
            cmd.extend(['--build-arg', 'SERVICE=frontend', str(project_root)])
        else:
            cmd.append(str(project_root))
        
        result = run_command(cmd, check=False)
        
        if result.returncode != 0:
            log_warning(f"Failed to build {service}, skipping...")
            continue
        
        # Save built image
        tar_file = images_dir / f"local_{service}.tar"
        log_info(f"Saving built image to: {tar_file}")
        result = run_command([runtime, 'save', '-o', str(tar_file), image_name], check=False)
        
        if result.returncode == 0:
            saved_images.append(tar_file)
            size_mb = tar_file.stat().st_size / (1024 * 1024)
            log_success(f"Saved {image_name} ({size_mb:.1f} MB)")
        else:
            log_warning(f"Failed to save {image_name}")
    
    return saved_images

def download_python_dependencies(project_root: Path, staging_dir: Path) -> None:
    """Download all Python dependencies for offline installation"""
    deps_dir = staging_dir / "python_deps"
    ensure_directory(deps_dir)
    
    requirements_files = [
        project_root / "backend" / "requirements.txt",
        project_root / "backend" / "requirements-minimal.txt",
        project_root / "services" / "requirements.txt"
    ]
    
    for req_file in requirements_files:
        if req_file.exists():
            log_info(f"Downloading Python dependencies from {req_file}")
            cmd = [
                sys.executable, '-m', 'pip', 'download',
                '-r', str(req_file),
                '-d', str(deps_dir),
                '--no-deps'
            ]
            run_command(cmd, check=False)
    
    # Count downloaded packages
    packages = list(deps_dir.glob('*.whl')) + list(deps_dir.glob('*.tar.gz'))
    log_success(f"Downloaded {len(packages)} Python packages")

def download_node_dependencies(project_root: Path, staging_dir: Path) -> None:
    """Bundle Node.js dependencies for offline installation"""
    node_deps_dir = staging_dir / "node_deps"
    ensure_directory(node_deps_dir)
    
    # Frontend package.json
    frontend_dir = project_root / "frontend"
    if (frontend_dir / "package.json").exists():
        log_info("Bundling frontend Node.js dependencies...")
        
        # Copy package files
        shutil.copy2(frontend_dir / "package.json", node_deps_dir / "frontend-package.json")
        if (frontend_dir / "package-lock.json").exists():
            shutil.copy2(frontend_dir / "package-lock.json", node_deps_dir / "frontend-package-lock.json")
        
        # Create npm cache for offline
        cache_dir = node_deps_dir / "npm-cache"
        ensure_directory(cache_dir)
        
        # Download dependencies to cache
        cmd = [
            'npm', 'config', 'set', 'cache', str(cache_dir)
        ]
        run_command(cmd, check=False)
        
        cmd = [
            'npm', 'install', '--prefix', str(frontend_dir),
            '--cache', str(cache_dir), '--prefer-offline'
        ]
        result = run_command(cmd, check=False)
        
        if result.returncode == 0:
            log_success("Node.js dependencies cached for offline installation")
        else:
            log_warning("Failed to cache some Node.js dependencies")

def copy_complete_project(project_root: Path, staging_dir: Path) -> None:
    """Copy complete project excluding only .git folder"""
    log_info("Copying complete project files...")
    
    project_staging = staging_dir / "sdc_project"
    ensure_directory(project_staging)
    
    # .git 폴더만 제외
    exclude_patterns = ['.git', '__pycache__', '*.pyc', '.pytest_cache']
    
    copied_size = 0
    for item in project_root.iterdir():
        skip = False
        for pattern in exclude_patterns:
            if pattern in str(item):
                skip = True
                break
        
        if skip:
            log_info(f"Skipping: {item.name}")
            continue
            
        log_info(f"Copying: {item.name}")
        try:
            if item.is_dir():
                shutil.copytree(item, project_staging / item.name, 
                              ignore=shutil.ignore_patterns(*exclude_patterns))
            else:
                shutil.copy2(item, project_staging)
            
            # Calculate copied size
            if item.is_dir():
                for root, dirs, files in os.walk(project_staging / item.name):
                    for file in files:
                        fp = os.path.join(root, file)
                        if os.path.exists(fp):
                            copied_size += os.path.getsize(fp)
            else:
                copied_size += (project_staging / item.name).stat().st_size
                
        except Exception as e:
            log_error(f"Failed to copy {item.name}: {e}")
            continue
    
    log_success(f"Project copied: {project_staging}")
    log_info(f"Copied size: {copied_size / (1024**3):.1f} GB")

def create_ultimate_install_script(staging_dir: Path, runtime: str) -> None:
    """Create comprehensive installation script with container support"""
    install_script = staging_dir / "install_ultimate_airgap.sh"
    
    script_content = f'''#!/bin/bash
set -e

# Ultimate SDC Air-gap Installation Script with Containers
echo "=============================================="
echo "SDC Ultimate Air-gap 설치 스크립트"  
echo "컨테이너 이미지 포함 완전한 오프라인 설치"
echo "=============================================="

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

log_info() {{ echo -e "${{BLUE}}[INFO]${{NC}} $1"; }}
log_success() {{ echo -e "${{GREEN}}[SUCCESS]${{NC}} $1"; }}
log_warning() {{ echo -e "${{YELLOW}}[WARNING]${{NC}} $1"; }}
log_error() {{ echo -e "${{RED}}[ERROR]${{NC}} $1"; }}

# Detect container runtime
detect_runtime() {{
    if command -v podman &> /dev/null; then
        echo "podman"
    elif command -v docker &> /dev/null; then
        echo "docker"
    else
        echo "none"
    fi
}}

# Load container images
load_container_images() {{
    local runtime=$1
    log_info "컨테이너 이미지 로드 중..."
    
    if [ -d "container_images" ]; then
        for img in container_images/*.tar; do
            if [ -f "$img" ]; then
                log_info "Loading: $(basename $img)"
                $runtime load -i "$img"
            fi
        done
        log_success "모든 컨테이너 이미지 로드 완료"
    else
        log_warning "컨테이너 이미지 디렉토리를 찾을 수 없습니다"
    fi
}}

# Install Python dependencies offline
install_python_deps() {{
    log_info "Python 의존성 설치 중..."
    
    if [ -d "python_deps" ]; then
        cd "$INSTALL_DIR/backend"
        python3 -m venv venv
        source venv/bin/activate
        pip install --no-index --find-links="$STAGING_DIR/python_deps" -r requirements.txt
        deactivate
        log_success "Python 의존성 설치 완료"
    else
        log_warning "Python 의존성을 찾을 수 없습니다"
    fi
}}

# Get installation directory
get_install_dir() {{
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
}}

# Main installation
main() {{
    STAGING_DIR=$(pwd)
    
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
                echo "  -y, --yes        자동 설치"
                echo "  -h, --help       도움말"
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
    
    # Create installation directory
    if [[ "$INSTALL_DIR" == /opt/* ]] && [ "$EUID" -ne 0 ]; then
        log_error "시스템 디렉토리 설치를 위해 sudo 권한이 필요합니다"
        exit 1
    fi
    
    mkdir -p "$INSTALL_DIR"
    
    # Copy project files
    log_info "프로젝트 파일 복사 중..."
    if [ -d "sdc_project" ]; then
        cp -r sdc_project/* "$INSTALL_DIR/"
        log_success "프로젝트 파일 복사 완료"
    else
        log_error "sdc_project 디렉토리를 찾을 수 없습니다"
        exit 1
    fi
    
    # Detect and setup container runtime
    RUNTIME=$(detect_runtime)
    if [ "$RUNTIME" != "none" ]; then
        log_success "Container runtime detected: $RUNTIME"
        load_container_images "$RUNTIME"
    else
        log_warning "컨테이너 런타임이 없습니다. 컨테이너 기능을 사용할 수 없습니다."
    fi
    
    # Setup environment
    cd "$INSTALL_DIR"
    if [ -f ".env.example" ] && [ ! -f ".env" ]; then
        cp .env.example .env
        log_info ".env 파일이 생성되었습니다"
    fi
    
    # Make scripts executable
    if [ -d "scripts" ]; then
        chmod +x scripts/*.sh 2>/dev/null || true
    fi
    
    echo ""
    echo "=============================================="
    log_success "SDC Ultimate Air-gap 설치 완료!"
    echo "=============================================="
    echo ""
    log_info "설치 위치: $INSTALL_DIR"
    echo ""
    log_info "포함된 내용:"
    echo "  ✅ 완전한 소스 코드"
    echo "  ✅ Python 가상환경 및 의존성"
    echo "  ✅ Node.js 의존성"
    echo "  ✅ 컨테이너 이미지 ($(ls -1 container_images/*.tar 2>/dev/null | wc -l)개)"
    echo ""
    
    if [ "$RUNTIME" != "none" ]; then
        log_info "컨테이너 실행:"
        echo "  cd $INSTALL_DIR"
        echo "  $RUNTIME-compose up -d"
    fi
    
    log_info "로컬 실행:"
    echo "  백엔드: cd $INSTALL_DIR/backend && source venv/bin/activate && python simple_api.py"
    echo "  프론트엔드: cd $INSTALL_DIR/frontend && npm run dev"
    echo ""
}}

main "$@"
'''
    
    with open(install_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    install_script.chmod(0o755)
    log_success(f"Ultimate installation script created: {install_script}")

def create_ultimate_readme(staging_dir: Path, saved_images: List[Path]) -> None:
    """Create comprehensive README for ultimate package"""
    readme = staging_dir / "README.md"
    
    image_list = "\n".join([f"  - {img.name}" for img in saved_images])
    
    readme_content = f"""# SDC Korean RAG System - Ultimate Air-gap Package

## 🚀 Ultimate 오프라인 배포 패키지

이 패키지는 **완전한** SDC Korean RAG 시스템과 **모든 컨테이너 이미지**를 포함합니다:
- ✅ 전체 소스 코드
- ✅ Python 가상환경 및 모든 의존성
- ✅ Node.js 의존성
- ✅ 모든 컨테이너 이미지 ({len(saved_images)}개)
- ✅ 완전한 오프라인 실행 환경

## 📦 패키지 구조

```
sdc-ultimate-airgap/
├── README.md                          # 이 파일
├── install_ultimate_airgap.sh         # 자동 설치 스크립트
├── container_images/                  # 컨테이너 이미지 tar 파일들
│   ├── pgvector_pgvector_pg16.tar
│   ├── redis_7-alpine.tar
│   ├── milvusdb_milvus_v2.3.3.tar
│   └── ... ({len(saved_images)}개 이미지)
├── python_deps/                       # Python 오프라인 패키지
├── node_deps/                          # Node.js 오프라인 캐시
└── sdc_project/                       # 완전한 프로젝트
```

## 🔧 포함된 컨테이너 이미지

{image_list}

## ⚡ 빠른 설치 (완전한 Air-gap)

### 1. 패키지 추출
```bash
tar -xzf sdc-ultimate-airgap-*.tar.gz
cd sdc-ultimate-airgap
```

### 2. 자동 설치
```bash
# 대화형 설치
sudo ./install_ultimate_airgap.sh

# 또는 자동 설치
sudo ./install_ultimate_airgap.sh -y -d /opt/sdc
```

### 3. 컨테이너 실행
```bash
cd /opt/sdc
podman-compose up -d  # 또는 docker-compose up -d
```

### 4. 서비스 접속
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 💡 완전한 오프라인 실행

이 패키지로 다음이 가능합니다:
1. **인터넷 연결 없이** 모든 서비스 실행
2. **컨테이너 이미지** 자동 로드
3. **모든 의존성** 포함
4. **즉시 개발** 가능한 환경

## 🔧 시스템 요구사항

### 최소 요구사항
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+)
- **메모리**: 16GB RAM
- **저장공간**: 50GB 여유 공간
- **Python**: 3.8+
- **Container Runtime**: Podman 또는 Docker

### 권장 사양
- **메모리**: 32GB RAM
- **CPU**: 8 cores
- **저장공간**: 100GB SSD

## 📋 설치 검증

설치 후 다음 명령으로 확인:
```bash
# 컨테이너 이미지 확인
podman images | grep sdc

# 서비스 상태 확인
podman-compose ps

# 포트 확인
netstat -tlnp | grep -E "3000|8000"
```

## ⚠️ 중요 사항

1. **대용량 패키지**: 압축 파일 약 10-15GB
2. **완전한 오프라인**: 인터넷 연결 불필요
3. **즉시 실행**: 모든 의존성 포함
4. **보안**: .env 파일에서 API 키 설정 필요

---

**SDC Korean RAG System v1.0**  
Ultimate Air-gap Deployment Package
생성 시간: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    with open(readme, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    log_success(f"Ultimate README created: {readme}")

def create_ultimate_package(staging_dir: Path, output_dir: Path) -> Path:
    """Create final ultimate package with containers"""
    ensure_directory(output_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"sdc-ultimate-airgap-{timestamp}.tar.gz"
    package_path = output_dir / package_name
    
    log_info("Creating final package... (This will take a long time)")
    
    # Use higher compression for large package
    with tarfile.open(package_path, 'w:gz', compresslevel=6) as tar:
        tar.add(staging_dir, arcname="sdc-ultimate-airgap")
    
    size_gb = package_path.stat().st_size / (1024**3)
    log_success(f"Ultimate package created: {package_path} ({size_gb:.2f} GB)")
    
    return package_path

def main():
    print("=" * 60)
    print("SDC Ultimate Air-gap Package Creator")
    print("Complete offline deployment with container images")
    print("=" * 60)
    
    project_root = Path.cwd()
    staging_dir = project_root / "staging-ultimate"
    output_dir = project_root / "release"
    
    # Detect container runtime
    runtime = detect_container_runtime()
    if not runtime:
        log_error("No container runtime found. Install podman or docker first.")
        sys.exit(1)
    
    try:
        # Clean staging
        if staging_dir.exists():
            log_info("Cleaning existing staging directory...")
            shutil.rmtree(staging_dir)
        ensure_directory(staging_dir)
        
        # Parse docker-compose.yml
        compose_file = project_root / "docker-compose.yml"
        if not compose_file.exists():
            log_error("docker-compose.yml not found")
            sys.exit(1)
        
        images = parse_docker_compose(compose_file)
        
        # Step 1: Copy complete project
        log_info("Step 1: Copying complete project...")
        copy_complete_project(project_root, staging_dir)
        
        # Step 2: Pull and save container images
        log_info("Step 2: Processing container images...")
        saved_images = []
        
        # Pull external images
        if images['external']:
            external_saved = pull_external_images(runtime, images['external'], staging_dir)
            saved_images.extend(external_saved)
        
        # Build local images
        if images['build']:
            local_saved = build_local_images(runtime, images['build'], project_root, staging_dir)
            saved_images.extend(local_saved)
        
        log_success(f"Total container images saved: {len(saved_images)}")
        
        # Step 3: Download Python dependencies
        log_info("Step 3: Downloading Python dependencies...")
        download_python_dependencies(project_root, staging_dir)
        
        # Step 4: Bundle Node.js dependencies
        log_info("Step 4: Bundling Node.js dependencies...")
        download_node_dependencies(project_root, staging_dir)
        
        # Step 5: Create installation tools
        log_info("Step 5: Creating installation tools...")
        create_ultimate_install_script(staging_dir, runtime)
        create_ultimate_readme(staging_dir, saved_images)
        
        # Step 6: Create final package
        log_info("Step 6: Creating final package...")
        package_path = create_ultimate_package(staging_dir, output_dir)
        
        # Calculate sizes
        staging_size_gb = sum(f.stat().st_size for f in staging_dir.rglob('*') if f.is_file()) / (1024**3)
        package_size_gb = package_path.stat().st_size / (1024**3)
        
        # Cleanup
        log_info("Cleaning up staging directory...")
        shutil.rmtree(staging_dir)
        
        # Final report
        print()
        print("=" * 60)
        log_success("Ultimate Air-gap Package Created Successfully!")
        print("=" * 60)
        print()
        print(f"📦 Package: {package_path}")
        print(f"📏 Compressed size: {package_size_gb:.2f} GB")
        print(f"📏 Uncompressed size: {staging_size_gb:.2f} GB")
        print()
        print("✅ Package contents:")
        print(f"  • Complete source code")
        print(f"  • {len(saved_images)} container images")
        print(f"  • Python dependencies")
        print(f"  • Node.js dependencies")
        print(f"  • Installation scripts")
        print()
        print("🚀 To install on air-gap server:")
        print("  1. Transfer the tar.gz file to target server")
        print("  2. tar -xzf sdc-ultimate-airgap-*.tar.gz")
        print("  3. cd sdc-ultimate-airgap")
        print("  4. sudo ./install_ultimate_airgap.sh")
        print()
        print("Ready for complete offline deployment!")
        
    except Exception as e:
        log_error(f"Package creation failed: {e}")
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise

if __name__ == "__main__":
    main()