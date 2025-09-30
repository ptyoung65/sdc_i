#!/usr/bin/env python3
"""
Python Wheels Collection Script for Air-gap Deployment
Collects all Python dependencies as wheel files for offline installation
"""

import os
import subprocess
import sys
from pathlib import Path
import tempfile
import shutil
from typing import List, Set

def find_requirements_files(project_root: Path) -> List[Path]:
    """Find all requirements.txt files in the project"""
    requirements_files = []
    
    # Core requirements files
    core_files = [
        "backend/requirements.txt",
        "backend/requirements-minimal.txt",
        "services/rag-orchestrator/requirements.txt",
        "services/vector-db-service/requirements.txt"
    ]
    
    for req_file in core_files:
        full_path = project_root / req_file
        if full_path.exists():
            requirements_files.append(full_path)
    
    # Find any other requirements files, but exclude air-gap directories
    for req_file in project_root.rglob("requirements*.txt"):
        # Skip files in air-gap deployment directories
        if any(part in ['airgap-deployment', 'sdc-airgap-deployment', 'staging', 'release'] 
               for part in req_file.parts):
            continue
        if req_file not in requirements_files:
            requirements_files.append(req_file)
    
    return requirements_files

def merge_requirements(requirements_files: List[Path], merged_file: Path) -> None:
    """Merge all requirements files into a single file, removing duplicates and resolving conflicts"""
    package_versions = {}
    
    for req_file in requirements_files:
        print(f"Processing {req_file}")
        with open(req_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    # Handle package names with version specifiers
                    if '==' in line:
                        package_name, version = line.split('==', 1)
                        package_name = package_name.strip()
                        version = version.strip()
                        
                        # If we've seen this package before, keep the later version
                        if package_name in package_versions:
                            current_version = package_versions[package_name].split('==')[1]
                            # Simple version comparison - choose the one that comes later lexicographically
                            if version > current_version:
                                package_versions[package_name] = f"{package_name}=={version}"
                        else:
                            package_versions[package_name] = f"{package_name}=={version}"
                    else:
                        # Handle other version specifiers by keeping as-is
                        package_name = line.split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('~=')[0].strip()
                        if package_name not in package_versions:
                            package_versions[package_name] = line
    
    # Ensure directory exists before writing
    merged_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write merged requirements
    with open(merged_file, 'w', encoding='utf-8') as f:
        for package_spec in sorted(package_versions.values()):
            f.write(f"{package_spec}\n")
    
    print(f"Merged {len(package_versions)} unique packages into {merged_file}")
    
    # Print any conflicts that were resolved
    if len(package_versions) < sum(len(open(f).readlines()) for f in requirements_files):
        print("Resolved version conflicts by choosing the latest versions")

def collect_wheels(requirements_file: Path, wheels_dir: Path) -> None:
    """Download all wheel files for the requirements"""
    wheels_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading wheels to {wheels_dir}")
    
    # Use pip download instead of wheel to avoid build issues
    cmd = [
        sys.executable, "-m", "pip", "download",
        "--dest", str(wheels_dir),
        "--requirement", str(requirements_file),
        "--prefer-binary",  # Prefer pre-built wheels
        "--only-binary=:all:",  # Only download binary wheels, skip source builds
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        # Fallback: try without only-binary restriction for packages that don't have wheels
        print("Retrying without binary-only restriction...")
        cmd_fallback = [
            sys.executable, "-m", "pip", "download",
            "--dest", str(wheels_dir),
            "--requirement", str(requirements_file),
            "--prefer-binary",
        ]
        subprocess.run(cmd_fallback, check=True)

def collect_python_stdlib() -> List[str]:
    """Get list of standard library modules to exclude"""
    import sys
    stdlib_modules = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else set()
    
    # Add common stdlib modules for older Python versions
    common_stdlib = {
        'os', 'sys', 'json', 'urllib', 'http', 'collections', 'itertools',
        'functools', 'operator', 'copy', 'pickle', 'threading', 'multiprocessing',
        'subprocess', 'shutil', 'tempfile', 'pathlib', 'datetime', 'time',
        'random', 'math', 'hashlib', 'base64', 'uuid', 'logging', 'traceback',
        'warnings', 'inspect', 'types', 'typing', 'dataclasses', 'enum'
    }
    
    return list(stdlib_modules.union(common_stdlib))

def create_install_script(wheels_dir: Path) -> None:
    """Create installation script for the wheels"""
    install_script = wheels_dir / "install_python_deps.sh"
    
    script_content = '''#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEELS_DIR="$SCRIPT_DIR"

echo "Installing Python dependencies from wheels..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip, setuptools, wheel
echo "Upgrading pip, setuptools, wheel..."
python -m pip install --upgrade --no-index --find-links "$WHEELS_DIR" pip setuptools wheel

# Install all wheels
echo "Installing project dependencies..."
python -m pip install --no-index --find-links "$WHEELS_DIR" --requirement requirements-merged.txt

echo "Python dependencies installation completed!"
echo "Virtual environment created at: $(pwd)/venv"
echo "To activate: source venv/bin/activate"
'''
    
    with open(install_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    install_script.chmod(0o755)
    print(f"Created installation script: {install_script}")

def main():
    """Main function to collect Python wheels"""
    project_root = Path.cwd()
    airgap_dir = project_root / "airgap-deployment"
    wheels_dir = airgap_dir / "python-wheels"
    
    print("=== Python Wheels Collection for Air-gap Deployment ===")
    print(f"Project root: {project_root}")
    print(f"Wheels directory: {wheels_dir}")
    
    # Find all requirements files
    requirements_files = find_requirements_files(project_root)
    
    if not requirements_files:
        print("No requirements.txt files found!")
        return
    
    print(f"Found {len(requirements_files)} requirements files:")
    for req_file in requirements_files:
        print(f"  - {req_file}")
    
    # Create merged requirements file
    merged_requirements = wheels_dir / "requirements-merged.txt"
    merge_requirements(requirements_files, merged_requirements)
    
    try:
        # Collect wheels
        collect_wheels(merged_requirements, wheels_dir)
        
        # Create installation script
        create_install_script(wheels_dir)
        
        # Copy merged requirements to wheels directory
        shutil.copy2(merged_requirements, wheels_dir / "requirements-merged.txt")
        
        print("\n=== Python Wheels Collection Completed ===")
        print(f"Wheels saved to: {wheels_dir}")
        print(f"Installation script: {wheels_dir}/install_python_deps.sh")
        print(f"Merged requirements: {wheels_dir}/requirements-merged.txt")
        
        # Show statistics
        wheel_files = list(wheels_dir.glob("*.whl"))
        print(f"Total wheel files: {len(wheel_files)}")
        
        total_size = sum(f.stat().st_size for f in wheel_files)
        print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
        
    except subprocess.CalledProcessError as e:
        print(f"Error collecting wheels: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()