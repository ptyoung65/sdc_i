#!/usr/bin/env python3
"""
Node.js Dependencies Collection Script for Air-gap Deployment
Collects all Node.js/npm dependencies as offline packages for air-gap installation
"""

import os
import subprocess
import sys
import json
import shutil
import tarfile
from pathlib import Path
from typing import List, Dict, Any

def find_package_json_files(project_root: Path) -> List[Path]:
    """Find all package.json files in the project"""
    package_files = []
    
    # Core package.json files
    core_files = [
        "frontend/package.json",
        "services/admin-panel/package.json",
        "services/rag-dashboard/package.json",
        "services/curation-dashboard/package.json"
    ]
    
    for pkg_file in core_files:
        full_path = project_root / pkg_file
        if full_path.exists():
            package_files.append(full_path)
    
    # Find any other package.json files (but avoid node_modules)
    for pkg_file in project_root.rglob("package.json"):
        if "node_modules" not in str(pkg_file) and pkg_file not in package_files:
            package_files.append(pkg_file)
    
    return package_files

def merge_package_dependencies(package_files: List[Path]) -> Dict[str, Any]:
    """Merge all package.json dependencies into a single structure"""
    all_dependencies = {}
    all_dev_dependencies = {}
    
    for pkg_file in package_files:
        print(f"Processing {pkg_file}")
        with open(pkg_file, 'r', encoding='utf-8') as f:
            package_data = json.load(f)
        
        # Merge dependencies
        if 'dependencies' in package_data:
            all_dependencies.update(package_data['dependencies'])
        
        # Merge devDependencies
        if 'devDependencies' in package_data:
            all_dev_dependencies.update(package_data['devDependencies'])
    
    merged_package = {
        "name": "sdc-air-gap-dependencies",
        "version": "1.0.0",
        "description": "Merged dependencies for air-gap deployment",
        "dependencies": all_dependencies,
        "devDependencies": all_dev_dependencies
    }
    
    return merged_package

def create_offline_package_cache(merged_package: Dict[str, Any], cache_dir: Path) -> None:
    """Create offline npm cache for all dependencies"""
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Write merged package.json
    merged_pkg_file = cache_dir / "package.json"
    with open(merged_pkg_file, 'w', encoding='utf-8') as f:
        json.dump(merged_package, f, indent=2)
    
    print(f"Created merged package.json: {merged_pkg_file}")
    
    # Create npm cache directory
    npm_cache_dir = cache_dir / "npm-cache"
    npm_cache_dir.mkdir(exist_ok=True)
    
    print("Creating offline npm cache...")
    
    # Set npm cache directory
    os.environ['npm_config_cache'] = str(npm_cache_dir)
    
    # Install dependencies to create cache
    subprocess.run([
        "npm", "install", 
        "--cache", str(npm_cache_dir),
        "--prefer-offline"
    ], cwd=cache_dir, check=True)
    
    print(f"NPM cache created at: {npm_cache_dir}")

def pack_all_dependencies(merged_package: Dict[str, Any], pack_dir: Path) -> None:
    """Pack all dependencies using npm pack"""
    pack_dir.mkdir(parents=True, exist_ok=True)
    
    all_deps = {}
    all_deps.update(merged_package.get('dependencies', {}))
    all_deps.update(merged_package.get('devDependencies', {}))
    
    print(f"Packing {len(all_deps)} packages...")
    
    failed_packages = []
    
    for package_name, version in all_deps.items():
        try:
            print(f"Packing {package_name}@{version}")
            
            # Use npm pack to download and pack the package
            result = subprocess.run([
                "npm", "pack", f"{package_name}@{version}"
            ], cwd=pack_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                failed_packages.append((package_name, version, result.stderr))
            
        except Exception as e:
            failed_packages.append((package_name, version, str(e)))
    
    if failed_packages:
        print(f"\nFailed to pack {len(failed_packages)} packages:")
        for pkg_name, pkg_version, error in failed_packages:
            print(f"  - {pkg_name}@{pkg_version}: {error}")
    
    # Count successful packs
    tgz_files = list(pack_dir.glob("*.tgz"))
    print(f"Successfully packed {len(tgz_files)} packages")

def create_node_binaries_bundle(node_dir: Path) -> None:
    """Download Node.js and npm binaries for offline installation"""
    node_dir.mkdir(parents=True, exist_ok=True)
    
    print("Downloading Node.js binaries...")
    
    # Get current Node.js version
    node_version_result = subprocess.run(["node", "--version"], capture_output=True, text=True)
    node_version = node_version_result.stdout.strip()
    
    # Get current npm version
    npm_version_result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
    npm_version = npm_version_result.stdout.strip()
    
    print(f"Current Node.js version: {node_version}")
    print(f"Current npm version: {npm_version}")
    
    # Download Node.js Linux binary
    node_download_url = f"https://nodejs.org/dist/{node_version}/node-{node_version}-linux-x64.tar.xz"
    
    try:
        subprocess.run([
            "wget", "-O", f"{node_dir}/node-{node_version}-linux-x64.tar.xz", 
            node_download_url
        ], check=True)
        print(f"Downloaded Node.js binary to {node_dir}")
    except subprocess.CalledProcessError:
        print("Warning: Could not download Node.js binary. Ensure wget is available and internet connection exists.")
    
    # Create version info file
    version_info = {
        "node_version": node_version,
        "npm_version": npm_version,
        "platform": "linux-x64",
        "download_url": node_download_url
    }
    
    with open(node_dir / "versions.json", 'w') as f:
        json.dump(version_info, f, indent=2)

def create_install_script(nodejs_dir: Path) -> None:
    """Create installation script for Node.js dependencies"""
    install_script = nodejs_dir / "install_nodejs_deps.sh"
    
    script_content = '''#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_DIR="$SCRIPT_DIR"
PACK_DIR="$NODE_DIR/packed-modules"
CACHE_DIR="$NODE_DIR/npm-cache"

echo "Installing Node.js dependencies from offline packages..."

# Extract and install Node.js if available
if [ -f "$NODE_DIR"/node-*.tar.xz ]; then
    echo "Extracting Node.js binary..."
    cd "$NODE_DIR"
    tar -xf node-*.tar.xz
    NODE_BINARY_DIR=$(find . -name "node-*-linux-x64" -type d | head -1)
    
    if [ -n "$NODE_BINARY_DIR" ]; then
        export PATH="$NODE_DIR/$NODE_BINARY_DIR/bin:$PATH"
        echo "Node.js binary added to PATH: $NODE_DIR/$NODE_BINARY_DIR/bin"
    fi
fi

# Verify Node.js and npm are available
if ! command -v node &> /dev/null; then
    echo "Error: Node.js not found. Please install Node.js manually."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "Error: npm not found. Please install npm manually."
    exit 1
fi

echo "Using Node.js: $(node --version)"
echo "Using npm: $(npm --version)"

# Set npm to use offline cache if available
if [ -d "$CACHE_DIR" ]; then
    echo "Using offline npm cache: $CACHE_DIR"
    npm config set cache "$CACHE_DIR"
    npm config set prefer-offline true
fi

# Install dependencies for each project component
install_component() {
    local component_path="$1"
    local component_name="$2"
    
    if [ -d "$component_path" ] && [ -f "$component_path/package.json" ]; then
        echo "Installing dependencies for $component_name..."
        cd "$component_path"
        
        # Install using offline cache if available
        if [ -d "$CACHE_DIR" ]; then
            npm ci --cache "$CACHE_DIR" --prefer-offline --no-audit
        else
            # Try to install from packed modules
            if [ -d "$PACK_DIR" ] && [ "$(ls -A "$PACK_DIR"/*.tgz 2>/dev/null)" ]; then
                echo "Installing from packed modules..."
                # This is a simplified approach - in practice, you'd need to resolve dependencies
                npm install --cache "$CACHE_DIR" --prefer-offline --no-audit
            else
                npm install --no-audit
            fi
        fi
        
        echo "✅ $component_name dependencies installed"
        cd - > /dev/null
    else
        echo "⚠️  $component_name not found or no package.json at $component_path"
    fi
}

# Install dependencies for all components
cd "$(dirname "$NODE_DIR")"

install_component "./frontend" "Frontend (Next.js)"
install_component "./services/admin-panel" "Admin Panel"
install_component "./services/rag-dashboard" "RAG Dashboard"  
install_component "./services/curation-dashboard" "Curation Dashboard"

echo ""
echo "✅ Node.js dependencies installation completed!"
echo "All frontend components should now have their dependencies installed."
'''
    
    with open(install_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    install_script.chmod(0o755)
    print(f"Created installation script: {install_script}")

def main():
    """Main function to collect Node.js dependencies"""
    project_root = Path.cwd()
    airgap_dir = project_root / "airgap-deployment"
    nodejs_dir = airgap_dir / "nodejs-deps"
    
    print("=== Node.js Dependencies Collection for Air-gap Deployment ===")
    print(f"Project root: {project_root}")
    print(f"Node.js directory: {nodejs_dir}")
    
    # Find all package.json files
    package_files = find_package_json_files(project_root)
    
    if not package_files:
        print("No package.json files found!")
        return
    
    print(f"Found {len(package_files)} package.json files:")
    for pkg_file in package_files:
        print(f"  - {pkg_file}")
    
    # Merge package dependencies
    merged_package = merge_package_dependencies(package_files)
    
    total_deps = len(merged_package.get('dependencies', {}))
    total_dev_deps = len(merged_package.get('devDependencies', {}))
    
    print(f"Total dependencies: {total_deps}")
    print(f"Total devDependencies: {total_dev_deps}")
    
    try:
        # Create offline package cache
        cache_dir = nodejs_dir / "cache"
        create_offline_package_cache(merged_package, cache_dir)
        
        # Pack all dependencies
        pack_dir = nodejs_dir / "packed-modules"
        pack_all_dependencies(merged_package, pack_dir)
        
        # Download Node.js binaries
        node_binaries_dir = nodejs_dir / "node-binaries"
        create_node_binaries_bundle(node_binaries_dir)
        
        # Create installation script
        create_install_script(nodejs_dir)
        
        print("\n=== Node.js Dependencies Collection Completed ===")
        print(f"Dependencies saved to: {nodejs_dir}")
        print(f"Installation script: {nodejs_dir}/install_nodejs_deps.sh")
        print(f"Merged package.json: {nodejs_dir}/cache/package.json")
        
        # Show statistics
        if (nodejs_dir / "packed-modules").exists():
            tgz_files = list((nodejs_dir / "packed-modules").glob("*.tgz"))
            if tgz_files:
                total_size = sum(f.stat().st_size for f in tgz_files)
                print(f"Packed modules: {len(tgz_files)} files, {total_size / 1024 / 1024:.2f} MB")
        
        if (nodejs_dir / "cache").exists():
            cache_size = sum(f.stat().st_size for f in (nodejs_dir / "cache").rglob("*") if f.is_file())
            print(f"NPM cache size: {cache_size / 1024 / 1024:.2f} MB")
        
    except subprocess.CalledProcessError as e:
        print(f"Error collecting Node.js dependencies: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()