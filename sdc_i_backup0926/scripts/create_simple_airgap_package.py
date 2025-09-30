#!/usr/bin/env python3
"""
Simple Air-gap Package Creation Script (Without Python Wheels)
Creates a basic offline deployment package for SDC Korean RAG System
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

def ensure_directory(path: Path) -> None:
    """Ensure directory exists"""
    path.mkdir(parents=True, exist_ok=True)

def copy_project_files(project_root: Path, staging_dir: Path) -> None:
    """Copy project files excluding .git and other unnecessary files"""
    log_info("Copying project files...")
    
    # Files and directories to exclude
    exclude_patterns = [
        '.git',
        '.gitignore',
        'node_modules',
        '__pycache__',
        '*.pyc',
        '.env',
        'venv',
        '.venv',
        'logs',
        'uploads',
        'processed',
        'airgap-deployment',
        'sdc-airgap-deployment',
        'staging',
        'release'
    ]
    
    # Additional check to prevent copying staging into itself
    staging_basename = staging_dir.name
    if staging_basename not in exclude_patterns:
        exclude_patterns.append(staging_basename)
    
    # Copy project files
    project_staging = staging_dir / "sdc_project"
    ensure_directory(project_staging)
    
    for item in project_root.iterdir():
        if item.name in exclude_patterns:
            log_info(f"Skipping {item.name}")
            continue
        
        if item.is_dir():
            shutil.copytree(item, project_staging / item.name, 
                          ignore=shutil.ignore_patterns(*exclude_patterns))
        else:
            shutil.copy2(item, project_staging)
    
    log_success(f"Project files copied to {project_staging}")

def create_deployment_manifest(staging_dir: Path) -> None:
    """Create deployment manifest with package information"""
    log_info("Creating deployment manifest...")
    
    manifest = {
        "package_info": {
            "name": "SDC Korean RAG System Air-gap Deployment (Simple)",
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "description": "Basic offline deployment package for SDC Korean RAG System"
        },
        "components": {
            "project_source": "sdc_project/",
            "installation_scripts": "sdc_project/scripts/"
        },
        "installation_instructions": [
            "1. Extract the package: tar -xzf sdc-airgap-deployment-simple.tar.gz",
            "2. Change to project directory: cd sdc_project", 
            "3. Run installation script: sudo ./scripts/install_airgap.sh",
            "4. Install dependencies manually in air-gap environment",
            "5. Configure environment: edit .env file with your settings",
            "6. Start services: ./scripts/start_services.sh"
        ],
        "requirements": {
            "os": "Linux (Ubuntu 20.04+, RHEL 8+, or compatible)",
            "memory": "8GB RAM minimum, 16GB recommended",
            "storage": "50GB free space minimum",
            "software": [
                "Python 3.8+",
                "Node.js 18+", 
                "Podman or Docker",
                "podman-compose or docker-compose"
            ]
        },
        "services": {
            "databases": ["PostgreSQL", "Redis", "Milvus", "Elasticsearch"],
            "applications": ["Backend API", "Frontend UI"],
            "microservices": ["Korean RAG", "Graph RAG", "Keyword RAG", "Text-to-SQL RAG"],
            "support": ["Docling", "SearXNG"],
            "monitoring": ["Prometheus", "Grafana", "Node Exporter"]
        },
        "notes": {
            "python_dependencies": "Python dependencies must be installed manually in air-gap environment. See requirements.txt files in project.",
            "nodejs_dependencies": "Node.js dependencies must be installed manually. Use 'npm install' in frontend directory.",
            "container_images": "Container images must be built locally using included Containerfile."
        }
    }
    
    manifest_file = staging_dir / "DEPLOYMENT_MANIFEST.json"
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    log_success(f"Deployment manifest created: {manifest_file}")

def create_readme(staging_dir: Path) -> None:
    """Create README file for the simple air-gap package"""
    log_info("Creating README file...")
    
    readme_content = """# SDC Korean RAG System - Simple Air-gap Deployment Package

## 개요

이 패키지는 SDC (Smart Document Companion) Korean RAG 시스템을 인터넷 연결이 없는 air-gap 환경에서 배포하기 위한 기본 소스 코드와 스크립트를 포함하고 있습니다.

**주의**: 이 패키지는 Python wheels와 Node.js 의존성을 포함하지 않습니다. air-gap 환경에서 수동으로 의존성을 설치해야 합니다.

## 패키지 구성

```
sdc-airgap-deployment-simple/
├── sdc_project/                    # 완전한 프로젝트 소스 코드
│   ├── backend/                    # Python FastAPI 백엔드
│   ├── frontend/                   # Next.js 프론트엔드 애플리케이션
│   ├── services/                   # 마이크로서비스 및 관리 패널
│   ├── scripts/                    # 설치 및 관리 스크립트
│   ├── docker-compose.yml          # 컨테이너 오케스트레이션
│   └── Containerfile               # 컨테이너 빌드 정의
├── DEPLOYMENT_MANIFEST.json        # 패키지 정보
└── README.md                       # 이 파일
```

## 시스템 요구사항

- **운영체제**: Linux (Ubuntu 20.04+, RHEL 8+, 또는 호환)
- **메모리**: 최소 8GB RAM, 16GB 권장
- **저장소**: 최소 50GB 여유 공간
- **소프트웨어**: Python 3.8+, Node.js 18+, Podman/Docker, podman-compose/docker-compose

## 설치 과정

### 1. 패키지 추출
```bash
tar -xzf sdc-airgap-deployment-simple-*.tar.gz
cd sdc_project
```

### 2. 시스템 의존성 설치
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv nodejs npm podman podman-compose

# RHEL/CentOS
sudo yum install python3 python3-pip nodejs npm podman podman-compose
```

### 3. Python 의존성 설치
```bash
# 백엔드 의존성
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 서비스 의존성 (각 서비스 디렉토리에서)
cd ../services/rag-orchestrator
pip install -r requirements.txt
# 다른 서비스들도 동일하게 반복
```

### 4. Node.js 의존성 설치
```bash
# 프론트엔드 의존성
cd frontend
npm install
npm run build

# Admin 패널 (필요시)
cd ../services/admin-panel
npm install
npm run build
```

### 5. 환경 구성
```bash
cp .env.example .env
# .env 파일을 편집하여 API 키 및 설정 추가
nano .env
```

### 6. 서비스 시작
```bash
./scripts/start_services.sh
```

## 수동 의존성 설치 가이드

### Python 라이브러리
주요 의존성 목록:
- FastAPI, Uvicorn (웹 서버)
- SQLAlchemy, AsyncPG (데이터베이스)
- PyMilvus (벡터 데이터베이스)
- LangChain, LangGraph (AI 파이프라인)
- Sentence-Transformers (임베딩)

```bash
# 최소 필수 패키지
pip install fastapi uvicorn sqlalchemy asyncpg redis pymilvus
pip install langchain langchain-community langchain-openai
pip install sentence-transformers torch transformers
```

### Node.js 패키지
주요 의존성:
- Next.js, React, TypeScript
- Tailwind CSS, Radix UI
- Zustand (상태 관리)

```bash
# 프론트엔드 빌드
cd frontend
npm install --production
npm run build
```

## 컨테이너 이미지 빌드

```bash
# SDC 애플리케이션 이미지 빌드
podman build -t sdc-app .

# 개별 서비스 이미지 빌드
podman build -t postgres:16 -f services/postgres/Containerfile services/postgres/
podman build -t redis:7 -f services/redis/Containerfile services/redis/
```

## 서비스 관리

### 서비스 시작
```bash
./scripts/start_services.sh
```

### 서비스 중지
```bash
./scripts/stop_services.sh
```

### 상태 확인
```bash
podman-compose ps
```

## 서비스 URL

설치 완료 후 다음 URL로 접속:
- **메인 애플리케이션**: http://localhost
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **Grafana**: http://localhost:3010
- **Prometheus**: http://localhost:9090

## 문제 해결

### 일반적인 문제

1. **Python 의존성 오류**
   ```bash
   # 가상환경 재생성
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Node.js 빌드 오류**
   ```bash
   # node_modules 재설치
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **포트 충돌**
   ```bash
   # 포트 사용 확인
   sudo netstat -tlnp | grep :3000
   # 프로세스 종료
   pkill -f node
   ```

## 지원

이 패키지는 기본적인 소스 코드만 포함합니다. air-gap 환경에서의 완전한 설치를 위해서는 추가적인 수동 작업이 필요합니다.

의존성 설치에 문제가 있는 경우:
1. 각 서비스의 requirements.txt 파일 확인
2. Python/Node.js 버전 호환성 확인
3. 개별 서비스별 설치 테스트

---

**SDC Korean RAG System v1.0**  
Simple Air-gap Deployment Package
"""
    
    readme_file = staging_dir / "README.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    log_success(f"README file created: {readme_file}")

def create_tar_package(staging_dir: Path, output_dir: Path) -> Path:
    """Create final tar.gz package"""
    log_info("Creating final tar.gz package...")
    
    ensure_directory(output_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"sdc-airgap-deployment-simple-{timestamp}.tar.gz"
    package_path = output_dir / package_name
    
    with tarfile.open(package_path, 'w:gz') as tar:
        tar.add(staging_dir, arcname="sdc-airgap-deployment-simple")
    
    # Calculate package size
    size_mb = package_path.stat().st_size / (1024 * 1024)
    
    log_success(f"Simple air-gap package created: {package_path}")
    log_info(f"Package size: {size_mb:.1f} MB")
    
    return package_path

def cleanup_staging(staging_dir: Path) -> None:
    """Clean up staging directory"""
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
        log_info("Staging directory cleaned up")

def main():
    """Main function to create simple air-gap package"""
    print("=" * 60)
    print("SDC Korean RAG System - Simple Air-gap Package Creator")
    print("=" * 60)
    print()
    
    project_root = Path.cwd()
    staging_dir = project_root / "staging-simple"
    output_dir = project_root / "release"
    
    log_info(f"Project root: {project_root}")
    log_info(f"Staging directory: {staging_dir}")
    log_info(f"Output directory: {output_dir}")
    
    try:
        # Clean up any existing staging
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        
        ensure_directory(staging_dir)
        
        # Copy project files
        log_info("Step 1: Copying project files...")
        copy_project_files(project_root, staging_dir)
        
        # Create manifest and documentation
        log_info("Step 2: Creating package documentation...")
        create_deployment_manifest(staging_dir)
        create_readme(staging_dir)
        
        # Create final package
        log_info("Step 3: Creating final package...")
        package_path = create_tar_package(staging_dir, output_dir)
        
        # Clean up staging
        cleanup_staging(staging_dir)
        
        print()
        print("=" * 60)
        log_success("Simple air-gap package creation completed successfully!")
        print("=" * 60)
        print()
        log_info("Package details:")
        print(f"  • Package file: {package_path}")
        print(f"  • Package size: {package_path.stat().st_size / (1024 * 1024):.1f} MB")
        print()
        log_info("Installation instructions:")
        print("  1. Transfer the package to your air-gap server")
        print("  2. Extract: tar -xzf sdc-airgap-deployment-simple-*.tar.gz")
        print("  3. Install system dependencies (Python, Node.js, Podman)")
        print("  4. Install Python dependencies: pip install -r backend/requirements.txt")
        print("  5. Install Node.js dependencies: cd frontend && npm install")
        print("  6. Configure: edit .env file")
        print("  7. Start: ./scripts/start_services.sh")
        print()
        
    except Exception as e:
        log_error(f"Package creation failed: {e}")
        cleanup_staging(staging_dir)
        sys.exit(1)

if __name__ == "__main__":
    main()