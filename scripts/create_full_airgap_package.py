#!/usr/bin/env python3
"""
완전한 Air-gap 배포 패키지 생성 스크립트
- 모든 소스코드, 의존성, 컨테이너 이미지 포함
- .git 폴더만 제외
"""

import os
import sys
import shutil
import subprocess
import json
import tarfile
from pathlib import Path
from datetime import datetime
import yaml

# ANSI 색상 코드
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_status(message, status="INFO"):
    """상태 메시지 출력"""
    colors = {
        "INFO": Colors.BLUE,
        "SUCCESS": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED
    }
    color = colors.get(status, Colors.BLUE)
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] [{status}]{Colors.ENDC} {message}")

def run_command(cmd, description="", capture_output=False):
    """명령 실행 및 결과 반환"""
    if description:
        print_status(description, "INFO")
    
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print_status(f"Command failed: {result.stderr}", "ERROR")
                return None
            return result.stdout.strip()
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0
    except Exception as e:
        print_status(f"Error running command: {e}", "ERROR")
        return None if capture_output else False

def get_container_images():
    """Docker Compose에서 사용하는 모든 이미지 목록 추출"""
    print_status("Docker Compose 파일에서 이미지 목록 추출 중...", "INFO")
    
    images = []
    compose_file = Path("docker-compose.yml")
    
    if not compose_file.exists():
        print_status("docker-compose.yml 파일을 찾을 수 없습니다", "ERROR")
        return images
    
    try:
        with open(compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        # 외부 이미지 목록
        external_images = [
            "docker.io/pgvector/pgvector:pg16",
            "docker.io/redis:7-alpine",
            "docker.io/milvusdb/milvus:v2.3.3",
            "docker.io/elastic/elasticsearch:8.11.0",
            "docker.io/searxng/searxng:latest",
            "docker.io/prom/prometheus:latest",
            "docker.io/prom/node-exporter:latest",
            "docker.io/zcube/cadvisor:latest",
            "docker.io/grafana/grafana:latest",
            "docker.io/nginx:alpine",
            "ghcr.io/ds4sd/docling:latest"
        ]
        
        # 빌드가 필요한 서비스
        build_services = []
        
        for service_name, service_config in compose_data.get('services', {}).items():
            if 'image' in service_config:
                images.append(service_config['image'])
            elif 'build' in service_config:
                build_services.append(service_name)
        
        # 외부 이미지 추가
        images.extend(external_images)
        
        # 중복 제거
        images = list(set(images))
        
        print_status(f"발견된 외부 이미지: {len(images)}개", "SUCCESS")
        print_status(f"빌드가 필요한 서비스: {len(build_services)}개", "INFO")
        
        return images, build_services
        
    except Exception as e:
        print_status(f"Docker Compose 파일 파싱 실패: {e}", "ERROR")
        return [], []

def build_local_images(staging_dir):
    """로컬 서비스 이미지 빌드"""
    print_status("로컬 서비스 이미지 빌드 중...", "INFO")
    
    # 빌드가 필요한 서비스 목록
    services_to_build = [
        "backend",
        "frontend",
        "rag-orchestrator"
    ]
    
    built_images = []
    
    for service in services_to_build:
        print_status(f"빌드 중: {service}", "INFO")
        cmd = f"podman-compose build {service}"
        if run_command(cmd):
            # 빌드된 이미지 이름 가져오기
            image_name = f"localhost/sdc_i_{service}:latest"
            built_images.append(image_name)
            print_status(f"빌드 완료: {image_name}", "SUCCESS")
        else:
            print_status(f"빌드 실패: {service}", "WARNING")
    
    return built_images

def export_container_images(images, staging_dir):
    """컨테이너 이미지를 tar 파일로 export"""
    images_dir = staging_dir / "container-images"
    images_dir.mkdir(exist_ok=True)
    
    exported_images = []
    
    for image in images:
        print_status(f"이미지 export 중: {image}", "INFO")
        
        # 이미지 이름을 파일명으로 변환
        image_filename = image.replace("/", "_").replace(":", "_") + ".tar"
        image_path = images_dir / image_filename
        
        # 이미지가 로컬에 있는지 확인하고 없으면 pull
        if not run_command(f"podman image exists {image}", capture_output=True):
            print_status(f"이미지 다운로드 중: {image}", "INFO")
            if not run_command(f"podman pull {image}"):
                print_status(f"이미지 다운로드 실패: {image}", "WARNING")
                continue
        
        # 이미지 export
        cmd = f"podman save -o {image_path} {image}"
        if run_command(cmd):
            exported_images.append({
                "name": image,
                "file": image_filename
            })
            print_status(f"Export 완료: {image_filename}", "SUCCESS")
        else:
            print_status(f"Export 실패: {image}", "WARNING")
    
    return exported_images

def copy_project_files(project_root, staging_dir):
    """프로젝트 파일 복사 (.git 제외)"""
    print_status("프로젝트 파일 복사 중...", "INFO")
    
    project_staging = staging_dir / "sdc_project"
    project_staging.mkdir(exist_ok=True)
    
    # 복사할 항목 카운트
    total_items = 0
    copied_items = 0
    
    # .git을 제외한 모든 파일 복사
    for item in project_root.iterdir():
        if item.name == '.git' or item.name == 'staging-full-airgap':
            continue
        
        total_items += 1
        dest = project_staging / item.name
        
        try:
            if item.is_dir():
                # .git을 제외하고 디렉토리 복사
                def ignore_git(dir, contents):
                    return ['.git'] if '.git' in contents else []
                shutil.copytree(item, dest, ignore=ignore_git, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
            
            copied_items += 1
            if copied_items % 100 == 0:
                print_status(f"진행 중: {copied_items}/{total_items} 항목 복사됨", "INFO")
                
        except Exception as e:
            print_status(f"복사 실패 {item.name}: {e}", "WARNING")
    
    # 프로젝트 크기 계산
    total_size = sum(f.stat().st_size for f in project_staging.rglob('*') if f.is_file())
    size_gb = total_size / (1024**3)
    
    print_status(f"프로젝트 파일 복사 완료: {copied_items}개 항목, {size_gb:.2f}GB", "SUCCESS")
    
    return copied_items

def create_install_script(staging_dir, exported_images):
    """Air-gap 환경용 설치 스크립트 생성"""
    print_status("설치 스크립트 생성 중...", "INFO")
    
    script_content = '''#!/bin/bash
# SDC Air-gap 설치 스크립트
# 생성일: ''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '''

set -e

# 색상 정의
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}   SDC Air-gap 설치 시작${NC}"
echo -e "${BLUE}=====================================${NC}"

# 설치 경로 확인
read -p "설치 경로를 입력하세요 [기본: /opt/sdc]: " INSTALL_PATH
INSTALL_PATH=${INSTALL_PATH:-/opt/sdc}

echo -e "${YELLOW}설치 경로: $INSTALL_PATH${NC}"

# 디렉토리 생성
mkdir -p "$INSTALL_PATH"

# 1. 프로젝트 파일 복사
echo -e "${BLUE}[1/4] 프로젝트 파일 복사 중...${NC}"
cp -r sdc_project/* "$INSTALL_PATH/"

# 2. 컨테이너 이미지 로드
echo -e "${BLUE}[2/4] 컨테이너 이미지 로드 중...${NC}"
cd container-images

# 이미지 목록
IMAGES=(
'''
    
    # 이미지 목록 추가
    for img in exported_images:
        script_content += f'    "{img["file"]}"\n'
    
    script_content += ''')

# 각 이미지 로드
for image_file in "${IMAGES[@]}"; do
    if [ -f "$image_file" ]; then
        echo -e "${YELLOW}  로드 중: $image_file${NC}"
        podman load -i "$image_file" || docker load -i "$image_file"
    else
        echo -e "${RED}  파일 없음: $image_file${NC}"
    fi
done

cd ..

# 3. 권한 설정
echo -e "${BLUE}[3/4] 권한 설정 중...${NC}"
cd "$INSTALL_PATH"
chmod +x scripts/*.sh 2>/dev/null || true

# 4. 환경 설정
echo -e "${BLUE}[4/4] 환경 설정 중...${NC}"

# .env 파일 확인
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || echo "# SDC 환경 설정" > .env
    echo -e "${YELLOW}  .env 파일을 설정해주세요${NC}"
fi

# 로그 디렉토리 생성
mkdir -p logs

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}   설치 완료!${NC}"
echo -e "${GREEN}=====================================${NC}"

echo ""
echo "다음 단계:"
echo "1. cd $INSTALL_PATH"
echo "2. .env 파일 수정 (API 키 등 설정)"
echo "3. podman-compose up -d (또는 docker-compose up -d)"
echo ""
echo "서비스 접속:"
echo "  - 메인 UI: http://localhost:3000"
echo "  - Admin Panel: http://localhost:3003"
echo "  - API: http://localhost:8000"
echo ""
'''
    
    install_script = staging_dir / "install.sh"
    install_script.write_text(script_content)
    install_script.chmod(0o755)
    
    print_status("설치 스크립트 생성 완료", "SUCCESS")

def create_readme(staging_dir):
    """README 파일 생성"""
    print_status("README 파일 생성 중...", "INFO")
    
    readme_content = f"""# SDC Air-gap 배포 패키지

## 📦 패키지 정보
- 생성일: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- 프로젝트: SDC (Smart Document Companion)
- 타입: 완전한 Air-gap 배포 패키지

## 📋 포함 내용
- ✅ 전체 소스코드 (프론트엔드/백엔드)
- ✅ Python 가상환경 (venv)
- ✅ Node.js 의존성 (node_modules)
- ✅ 모든 컨테이너 이미지
- ✅ 설정 파일 및 스크립트
- ❌ .git 폴더 (제외됨)

## 🚀 설치 방법

### 1. 패키지 압축 해제
```bash
tar -xzf sdc-airgap-full-*.tar.gz
cd sdc-airgap-deployment
```

### 2. 설치 스크립트 실행
```bash
sudo ./install.sh
```

### 3. 서비스 시작
```bash
cd /opt/sdc  # 또는 설치한 경로
podman-compose up -d
# 또는
docker-compose up -d
```

## 📌 시스템 요구사항
- OS: Linux (RHEL/CentOS/Ubuntu)
- Container: Podman 또는 Docker
- CPU: 최소 4코어 이상
- RAM: 최소 16GB 이상
- Disk: 최소 50GB 이상
- Python: 3.11+ (백엔드용)
- Node.js: 20+ (프론트엔드용)

## 🔧 문제 해결

### 포트 충돌 시
```bash
# scripts/start_with_port_cleanup.sh 사용
./scripts/start_with_port_cleanup.sh
```

### 컨테이너 이미지 로드 실패 시
```bash
# 수동으로 이미지 로드
cd container-images
for img in *.tar; do
    podman load -i "$img"
done
```

## 📞 지원
- 문제 발생 시 로그 확인: `logs/` 디렉토리
- 환경 설정: `.env` 파일 수정
"""
    
    readme_file = staging_dir / "README.md"
    readme_file.write_text(readme_content)
    
    print_status("README 파일 생성 완료", "SUCCESS")

def create_final_package(staging_dir):
    """최종 tar.gz 패키지 생성"""
    print_status("최종 패키지 생성 중...", "INFO")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"sdc-airgap-full-{timestamp}.tar.gz"
    
    # tar 생성 (진행 상황 표시)
    print_status("압축 중... (시간이 걸릴 수 있습니다)", "INFO")
    
    with tarfile.open(package_name, "w:gz") as tar:
        tar.add(staging_dir, arcname="sdc-airgap-deployment")
    
    # 패키지 크기 확인
    package_size = Path(package_name).stat().st_size / (1024**3)
    
    print_status(f"패키지 생성 완료: {package_name} ({package_size:.2f}GB)", "SUCCESS")
    
    return package_name, package_size

def main():
    """메인 실행 함수"""
    print_status("🚀 SDC Air-gap 패키지 생성 시작", "INFO")
    
    # 프로젝트 루트 확인
    project_root = Path.cwd()
    if not (project_root / "docker-compose.yml").exists():
        print_status("docker-compose.yml이 없습니다. 프로젝트 루트에서 실행하세요.", "ERROR")
        sys.exit(1)
    
    # staging 디렉토리 생성
    staging_dir = project_root / "staging-full-airgap"
    if staging_dir.exists():
        print_status("기존 staging 디렉토리 삭제 중...", "INFO")
        shutil.rmtree(staging_dir)
    staging_dir.mkdir()
    
    try:
        # 1. 컨테이너 이미지 목록 가져오기
        external_images, build_services = get_container_images()
        
        # 2. 로컬 이미지 빌드
        print_status("=" * 50, "INFO")
        built_images = build_local_images(staging_dir)
        
        # 3. 모든 이미지 export
        print_status("=" * 50, "INFO")
        all_images = external_images + built_images
        exported_images = export_container_images(all_images, staging_dir)
        
        # 4. 프로젝트 파일 복사
        print_status("=" * 50, "INFO")
        copy_project_files(project_root, staging_dir)
        
        # 5. 설치 스크립트 생성
        create_install_script(staging_dir, exported_images)
        
        # 6. README 생성
        create_readme(staging_dir)
        
        # 7. 최종 패키지 생성
        print_status("=" * 50, "INFO")
        package_name, package_size = create_final_package(staging_dir)
        
        # 8. 정리
        print_status("Staging 디렉토리 정리 중...", "INFO")
        shutil.rmtree(staging_dir)
        
        # 완료 메시지
        print_status("=" * 50, "SUCCESS")
        print_status(f"✅ Air-gap 패키지 생성 완료!", "SUCCESS")
        print_status(f"📦 파일명: {package_name}", "SUCCESS")
        print_status(f"📊 크기: {package_size:.2f}GB", "SUCCESS")
        print_status(f"📍 위치: {project_root / package_name}", "SUCCESS")
        print_status("=" * 50, "SUCCESS")
        
    except Exception as e:
        print_status(f"패키지 생성 실패: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()