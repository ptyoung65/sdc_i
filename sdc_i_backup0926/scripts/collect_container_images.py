#!/usr/bin/env python3
"""
Container Images Collection Script for Air-gap Deployment
Builds and exports all Podman container images for offline deployment
"""

import os
import subprocess
import sys
import yaml
import json
from pathlib import Path
from typing import List, Dict, Set
import re

def find_docker_compose_files(project_root: Path) -> List[Path]:
    """Find all docker-compose.yml files in the project"""
    compose_files = []
    
    # Main docker-compose files
    main_files = [
        "docker-compose.yml",
        "services/docker-compose.curated-rag.yml",
        "services/docker-compose.rag-eval.yml", 
        "services/docker-compose.vector-system.yml"
    ]
    
    for compose_file in main_files:
        full_path = project_root / compose_file
        if full_path.exists():
            compose_files.append(full_path)
    
    # Find any other docker-compose files
    for compose_file in project_root.rglob("docker-compose*.yml"):
        if compose_file not in compose_files:
            compose_files.append(compose_file)
    
    return compose_files

def find_containerfiles(project_root: Path) -> List[Path]:
    """Find all Containerfiles and Dockerfiles in the project"""
    containerfiles = []
    
    # Find Containerfiles and Dockerfiles
    for dockerfile in project_root.rglob("Containerfile"):
        containerfiles.append(dockerfile)
    
    for dockerfile in project_root.rglob("Dockerfile"):
        containerfiles.append(dockerfile)
    
    return containerfiles

def extract_images_from_compose(compose_file: Path) -> Dict[str, str]:
    """Extract image names from docker-compose.yml file"""
    images = {}
    
    try:
        with open(compose_file, 'r', encoding='utf-8') as f:
            compose_data = yaml.safe_load(f)
        
        if 'services' in compose_data:
            for service_name, service_config in compose_data['services'].items():
                if 'image' in service_config:
                    images[service_name] = service_config['image']
    
    except Exception as e:
        print(f"Error parsing {compose_file}: {e}")
    
    return images

def get_all_required_images(project_root: Path) -> Dict[str, str]:
    """Get all container images required by the project"""
    all_images = {}
    
    # Find docker-compose files
    compose_files = find_docker_compose_files(project_root)
    
    print(f"Found {len(compose_files)} docker-compose files:")
    for compose_file in compose_files:
        print(f"  - {compose_file}")
        images = extract_images_from_compose(compose_file)
        all_images.update(images)
    
    return all_images

def build_custom_images(project_root: Path, images_dir: Path) -> List[str]:
    """Build custom images from Containerfiles/Dockerfiles"""
    built_images = []
    
    # Find Containerfiles
    containerfiles = find_containerfiles(project_root)
    
    print(f"Found {len(containerfiles)} Containerfiles/Dockerfiles:")
    for containerfile in containerfiles:
        print(f"  - {containerfile}")
    
    # Build images based on project structure
    custom_builds = [
        {
            "name": "sdc-backend",
            "context": ".",
            "file": "Containerfile",
            "target": "backend-builder"
        },
        {
            "name": "sdc-frontend", 
            "context": ".",
            "file": "Containerfile",
            "target": "frontend-builder"
        },
        {
            "name": "sdc-admin-panel",
            "context": "services/admin-panel",
            "file": "services/admin-panel/Containerfile"
        },
        {
            "name": "sdc-vector-db-service",
            "context": "services/vector-db-service", 
            "file": "services/vector-db-service/Containerfile"
        }
    ]
    
    for build_config in custom_builds:
        context_path = project_root / build_config["context"]
        containerfile_path = project_root / build_config.get("file", "Containerfile")
        
        if not containerfile_path.exists():
            print(f"Skipping {build_config['name']}: Containerfile not found at {containerfile_path}")
            continue
        
        print(f"Building {build_config['name']} from {containerfile_path}")
        
        try:
            build_cmd = [
                "podman", "build",
                "-t", build_config["name"],
                "-f", str(containerfile_path),
                str(context_path)
            ]
            
            if "target" in build_config:
                build_cmd.extend(["--target", build_config["target"]])
            
            subprocess.run(build_cmd, check=True, cwd=project_root)
            built_images.append(build_config["name"])
            print(f"✅ Successfully built {build_config['name']}")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build {build_config['name']}: {e}")
    
    return built_images

def pull_external_images(external_images: Dict[str, str]) -> List[str]:
    """Pull external images from registries"""
    pulled_images = []
    
    print(f"Pulling {len(external_images)} external images...")
    
    for service_name, image_name in external_images.items():
        print(f"Pulling {image_name} for service {service_name}")
        
        try:
            subprocess.run(["podman", "pull", image_name], check=True)
            pulled_images.append(image_name)
            print(f"✅ Successfully pulled {image_name}")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to pull {image_name}: {e}")
    
    return pulled_images

def export_images(images: List[str], images_dir: Path) -> None:
    """Export container images as tar files"""
    images_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Exporting {len(images)} images to {images_dir}")
    
    for image in images:
        # Clean image name for filename
        safe_name = re.sub(r'[^\w\-_.]', '_', image.replace('/', '_').replace(':', '_'))
        export_file = images_dir / f"{safe_name}.tar"
        
        print(f"Exporting {image} to {export_file}")
        
        try:
            subprocess.run([
                "podman", "save", 
                "-o", str(export_file),
                image
            ], check=True)
            
            print(f"✅ Exported {image} ({export_file.stat().st_size / 1024 / 1024:.1f} MB)")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to export {image}: {e}")

def create_image_manifest(images: List[str], external_images: Dict[str, str], 
                         built_images: List[str], images_dir: Path) -> None:
    """Create manifest file listing all images"""
    manifest = {
        "built_images": built_images,
        "external_images": dict(external_images),
        "all_images": images,
        "export_info": {
            "total_images": len(images),
            "built_count": len(built_images),
            "external_count": len(external_images)
        }
    }
    
    manifest_file = images_dir / "images_manifest.json"
    
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Created image manifest: {manifest_file}")

def create_load_script(images_dir: Path) -> None:
    """Create script to load all container images"""
    load_script = images_dir / "load_container_images.sh"
    
    script_content = '''#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="$SCRIPT_DIR"

echo "Loading Podman container images for air-gap deployment..."

# Check if podman is available
if ! command -v podman &> /dev/null; then
    echo "Error: Podman not found. Please install Podman first."
    exit 1
fi

echo "Using Podman: $(podman --version)"

# Load all tar files in the images directory
loaded_count=0
failed_count=0

for tar_file in "$IMAGES_DIR"/*.tar; do
    if [ -f "$tar_file" ]; then
        echo "Loading $(basename "$tar_file")..."
        if podman load -i "$tar_file"; then
            echo "✅ Successfully loaded $(basename "$tar_file")"
            ((loaded_count++))
        else
            echo "❌ Failed to load $(basename "$tar_file")"
            ((failed_count++))
        fi
    fi
done

echo ""
echo "=== Container Images Loading Summary ==="
echo "Successfully loaded: $loaded_count images"
echo "Failed to load: $failed_count images"

if [ $failed_count -eq 0 ]; then
    echo "✅ All container images loaded successfully!"
else
    echo "⚠️  Some images failed to load. Check the output above for details."
fi

# List loaded images
echo ""
echo "Available container images:"
podman images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.Created}}"
'''
    
    with open(load_script, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    load_script.chmod(0o755)
    print(f"Created image loading script: {load_script}")

def main():
    """Main function to collect container images"""
    project_root = Path.cwd()
    airgap_dir = project_root / "airgap-deployment"
    images_dir = airgap_dir / "container-images"
    
    print("=== Container Images Collection for Air-gap Deployment ===")
    print(f"Project root: {project_root}")
    print(f"Images directory: {images_dir}")
    
    # Get all required images from docker-compose files
    external_images = get_all_required_images(project_root)
    
    print(f"\nFound {len(external_images)} external images:")
    for service, image in external_images.items():
        print(f"  - {service}: {image}")
    
    all_images = []
    
    try:
        # Build custom images
        print("\n=== Building Custom Images ===")
        built_images = build_custom_images(project_root, images_dir)
        all_images.extend(built_images)
        
        # Pull external images
        print("\n=== Pulling External Images ===")
        pulled_images = pull_external_images(external_images)
        all_images.extend(pulled_images)
        
        # Export all images
        print("\n=== Exporting Images ===")
        export_images(all_images, images_dir)
        
        # Create manifest and scripts
        create_image_manifest(all_images, external_images, built_images, images_dir)
        create_load_script(images_dir)
        
        print("\n=== Container Images Collection Completed ===")
        print(f"Images exported to: {images_dir}")
        print(f"Loading script: {images_dir}/load_container_images.sh")
        print(f"Images manifest: {images_dir}/images_manifest.json")
        
        # Show statistics
        tar_files = list(images_dir.glob("*.tar"))
        if tar_files:
            total_size = sum(f.stat().st_size for f in tar_files)
            print(f"Total exported images: {len(tar_files)}")
            print(f"Total size: {total_size / 1024 / 1024 / 1024:.2f} GB")
        
    except subprocess.CalledProcessError as e:
        print(f"Error collecting container images: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()