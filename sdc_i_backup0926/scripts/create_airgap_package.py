#!/usr/bin/env python3
"""
Air-gap Package Creation Script
Creates a complete offline deployment package for SDC Korean RAG System
"""

import os
import subprocess
import sys
import shutil
import tarfile
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

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
        'airgap-deployment',  # Don't copy existing airgap directory
        'sdc-airgap-deployment',  # Don't copy previous air-gap builds
        'staging',  # Don't copy staging directory to prevent recursion
        'release'  # Don't copy release directory
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

def run_collection_scripts(project_root: Path) -> None:
    """Run all dependency collection scripts"""
    scripts_dir = project_root / "scripts"
    
    # Collection scripts to run
    scripts = [
        ("collect_python_wheels.py", "Python wheels"),
        ("collect_nodejs_deps.py", "Node.js dependencies"),
        ("collect_container_images.py", "Container images")
    ]
    
    for script_name, description in scripts:
        script_path = scripts_dir / script_name
        
        if not script_path.exists():
            log_error(f"Script not found: {script_path}")
            continue
        
        log_info(f"Running {description} collection...")
        
        try:
            subprocess.run([sys.executable, str(script_path)], 
                         cwd=project_root, check=True)
            log_success(f"{description} collection completed")
        except subprocess.CalledProcessError as e:
            log_error(f"Failed to collect {description}: {e}")

def create_deployment_manifest(staging_dir: Path) -> None:
    """Create deployment manifest with package information"""
    log_info("Creating deployment manifest...")
    
    manifest = {
        "package_info": {
            "name": "SDC Korean RAG System Air-gap Deployment",
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "description": "Complete offline deployment package for SDC Korean RAG System"
        },
        "components": {
            "project_source": "sdc_project/",
            "python_dependencies": "airgap-deployment/python-wheels/",
            "nodejs_dependencies": "airgap-deployment/nodejs-deps/",
            "installation_scripts": "sdc_project/scripts/"
        },
        "installation_instructions": [
            "1. Extract the package: tar -xzf sdc-airgap-deployment.tar.gz",
            "2. Change to project directory: cd sdc_project",
            "3. Run installation script: sudo ./scripts/install_airgap.sh",
            "4. Configure environment: edit .env file with your settings",
            "5. Start services: ./scripts/start_services.sh",
            "6. Access application at http://localhost:3000"
        ],
        "requirements": {
            "os": "Linux (Ubuntu 20.04+, RHEL 8+, or compatible)",
            "memory": "8GB RAM minimum, 16GB recommended",
            "storage": "50GB free space minimum",
            "software": [
                "Python 3.8+",
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
        }
    }
    
    manifest_file = staging_dir / "DEPLOYMENT_MANIFEST.json"
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    log_success(f"Deployment manifest created: {manifest_file}")

def create_readme(staging_dir: Path) -> None:
    """Create README file for the air-gap package"""
    log_info("Creating README file...")
    
    readme_content = """# SDC Korean RAG System - Air-gap Deployment Package

## Overview

This package contains everything needed to deploy the SDC (Smart Document Companion) Korean RAG System in an air-gap environment without internet connectivity.

## Package Contents

```
sdc-airgap-deployment/
├── sdc_project/                    # Complete project source code
│   ├── backend/                    # Python FastAPI backend
│   ├── frontend/                   # Next.js frontend application
│   ├── services/                   # Microservices and admin panels
│   ├── scripts/                    # Installation and management scripts
│   ├── docker-compose.yml          # Container orchestration
│   └── Containerfile               # Container build definitions
├── airgap-deployment/              # Offline dependencies
│   ├── python-wheels/              # Python packages (.whl files)
│   ├── nodejs-deps/                # Node.js dependencies
│   └── container-images/           # Container images (.tar files)
├── DEPLOYMENT_MANIFEST.json        # Package information
└── README.md                       # This file
```

## System Requirements

- **OS**: Linux (Ubuntu 20.04+, RHEL 8+, or compatible)
- **Memory**: 8GB RAM minimum, 16GB recommended
- **Storage**: 50GB free space minimum
- **Software**: Python 3.8+, Podman/Docker, podman-compose/docker-compose

## Quick Installation

1. **Extract the package**:
   ```bash
   tar -xzf sdc-airgap-deployment.tar.gz
   cd sdc_project
   ```

2. **Run the installation script**:
   ```bash
   # Interactive installation (choose installation directory)
   sudo ./scripts/install_airgap.sh
   
   # Or non-interactive installation (use default directory)
   sudo ./scripts/install_airgap.sh -y
   
   # Or specify custom installation directory
   sudo ./scripts/install_airgap.sh -d /opt/sdc
   ```

3. **Configure environment**:
   ```bash
   # Edit .env file to add your API keys and settings
   nano /path/to/installation/.env
   ```

4. **Start services**:
   ```bash
   # From installation directory
   cd /path/to/installation
   ./scripts/start_services.sh
   
   # Or run from anywhere (script auto-detects project location)
   /path/to/installation/scripts/start_services.sh
   ```

5. **Access the application**:
   - Main Application: http://localhost
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Installation Directory Options

The installation script supports multiple installation directory options:

### Interactive Mode (Default)
```bash
sudo ./scripts/install_airgap.sh
```
Presents a menu with options:
1. Current directory + /sdc
2. Home directory + /sdc  
3. /opt/sdc (requires root)
4. Default location (where package was extracted)
5. Custom path

### Non-Interactive Mode
```bash
sudo ./scripts/install_airgap.sh -y
```
Uses the default installation directory without prompting.

### Custom Directory
```bash
sudo ./scripts/install_airgap.sh -d /custom/path
sudo ./scripts/install_airgap.sh --dir ~/my-sdc-installation
```
Installs to the specified directory.

## Manual Installation Steps

If you prefer manual installation or encounter issues:

### 1. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip podman podman-compose curl wget

# RHEL/CentOS
sudo yum install python3 python3-pip podman podman-compose curl wget
```

### 2. Install Python Dependencies

```bash
cd airgap-deployment/python-wheels
./install_python_deps.sh
```

### 3. Install Node.js Dependencies

```bash
cd ../nodejs-deps
./install_nodejs_deps.sh
```

### 4. Load Container Images

```bash
cd ../container-images
./load_container_images.sh
```

### 5. Setup Project

```bash
cd ../../sdc_project
cp .env.example .env
# Edit .env file with your configuration
```

### 6. Start Services

```bash
./scripts/start_services.sh
```

## Service Management

### Start Services
```bash
./scripts/start_services.sh
```

### Stop Services
```bash
./scripts/stop_services.sh
```

### Check Status
```bash
./scripts/stop_services.sh --status
```

### View Logs
```bash
podman-compose logs -f [service_name]
```

## Configuration

### Environment Variables (.env)

Key configuration options:

```bash
# Database Settings
POSTGRES_USER=sdc_user
POSTGRES_PASSWORD=sdc_password
POSTGRES_DB=sdc_db

# AI Service API Keys (required for full functionality)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
GEMINI_API_KEY=your_gemini_key

# Application Settings
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=http://localhost:3000
```

### Service Ports

- **Frontend**: 3000
- **Backend API**: 8000
- **PostgreSQL**: 5432
- **Redis**: 6379
- **Milvus**: 19530
- **Elasticsearch**: 9200
- **Prometheus**: 9090
- **Grafana**: 3010
- **Nginx**: 80, 443

## Architecture

The SDC system consists of:

- **Frontend**: Next.js React application with TypeScript
- **Backend**: FastAPI Python application with async support
- **Databases**: PostgreSQL, Redis, Milvus (vector), Elasticsearch
- **AI Services**: Multi-LLM support (OpenAI, Anthropic, Google)
- **RAG Pipeline**: Korean-optimized retrieval augmented generation
- **Microservices**: Specialized RAG services for different use cases

## Troubleshooting

### Common Issues

1. **Port conflicts**: Check if ports are already in use
   ```bash
   sudo netstat -tlnp | grep :3000
   ```

2. **Permission errors**: Ensure proper file permissions
   ```bash
   chmod +x scripts/*.sh
   ```

3. **Container issues**: Check Podman status
   ```bash
   podman ps -a
   podman-compose logs
   ```

4. **Memory issues**: Ensure sufficient RAM (8GB minimum)
   ```bash
   free -h
   ```

### Log Locations

- Application logs: `./logs/`
- Container logs: `podman-compose logs [service]`
- System logs: `/var/log/syslog` or `journalctl`

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review container logs for error messages
3. Ensure all system requirements are met
4. Verify environment configuration in .env file

## Security Notes

- Change default passwords in .env file
- Configure firewall to restrict access to necessary ports only
- Regularly update API keys and secrets
- Monitor system logs for unusual activity

---

**SDC Korean RAG System v1.0**
Air-gap Deployment Package
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
    package_name = f"sdc-airgap-deployment-{timestamp}.tar.gz"
    package_path = output_dir / package_name
    
    with tarfile.open(package_path, 'w:gz') as tar:
        tar.add(staging_dir, arcname="sdc-airgap-deployment")
    
    # Calculate package size
    size_mb = package_path.stat().st_size / (1024 * 1024)
    
    log_success(f"Air-gap package created: {package_path}")
    log_info(f"Package size: {size_mb:.1f} MB")
    
    return package_path

def cleanup_staging(staging_dir: Path) -> None:
    """Clean up staging directory"""
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
        log_info("Staging directory cleaned up")

def main():
    """Main function to create air-gap package"""
    print("=" * 60)
    print("SDC Korean RAG System - Air-gap Package Creator")
    print("=" * 60)
    print()
    
    project_root = Path.cwd()
    staging_dir = project_root / "staging"
    output_dir = project_root / "release"
    
    log_info(f"Project root: {project_root}")
    log_info(f"Staging directory: {staging_dir}")
    log_info(f"Output directory: {output_dir}")
    
    try:
        # Clean up any existing staging
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        
        ensure_directory(staging_dir)
        
        # Run dependency collection scripts
        log_info("Step 1: Collecting dependencies...")
        run_collection_scripts(project_root)
        
        # Copy project files
        log_info("Step 2: Copying project files...")
        copy_project_files(project_root, staging_dir)
        
        # Copy airgap-deployment directory
        log_info("Step 3: Copying offline dependencies...")
        airgap_source = project_root / "airgap-deployment"
        if airgap_source.exists():
            shutil.copytree(airgap_source, staging_dir / "airgap-deployment")
            log_success("Offline dependencies copied")
        else:
            log_warning("airgap-deployment directory not found")
        
        # Create manifest and documentation
        log_info("Step 4: Creating package documentation...")
        create_deployment_manifest(staging_dir)
        create_readme(staging_dir)
        
        # Create final package
        log_info("Step 5: Creating final package...")
        package_path = create_tar_package(staging_dir, output_dir)
        
        # Clean up staging
        cleanup_staging(staging_dir)
        
        print()
        print("=" * 60)
        log_success("Air-gap package creation completed successfully!")
        print("=" * 60)
        print()
        log_info("Package details:")
        print(f"  • Package file: {package_path}")
        print(f"  • Package size: {package_path.stat().st_size / (1024 * 1024):.1f} MB")
        print()
        log_info("Installation instructions:")
        print("  1. Transfer the package to your air-gap server")
        print("  2. Extract: tar -xzf sdc-airgap-deployment-*.tar.gz")
        print("  3. Install: cd sdc_project && sudo ./scripts/install_airgap.sh")
        print("  4. Configure: edit .env file")
        print("  5. Start: ./scripts/start_services.sh")
        print()
        
    except Exception as e:
        log_error(f"Package creation failed: {e}")
        cleanup_staging(staging_dir)
        sys.exit(1)

if __name__ == "__main__":
    main()