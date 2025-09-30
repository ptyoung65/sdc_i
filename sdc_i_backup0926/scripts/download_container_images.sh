#!/bin/bash

# Container images download script for air-gap deployment
set -e

echo "=========================================="
echo "SDC Container Images Download Script"
echo "=========================================="

# Create images directory
IMAGES_DIR="container_images"
mkdir -p "$IMAGES_DIR"

# Detect container runtime
if command -v podman &> /dev/null; then
    RUNTIME="podman"
elif command -v docker &> /dev/null; then
    RUNTIME="docker"
else
    echo "Error: No container runtime found (podman or docker)"
    exit 1
fi

echo "Using container runtime: $RUNTIME"

# List of required images from docker-compose.yml
IMAGES=(
    "docker.io/pgvector/pgvector:pg16"
    "docker.io/redis:7-alpine"
    "docker.io/milvusdb/milvus:v2.3.3"
    "docker.elastic.co/elasticsearch/elasticsearch:8.11.1"
    "docker.io/legendofmk/docling-cpu-api:latest"
    "docker.io/searxng/searxng:latest"
    "docker.io/prom/prometheus:latest"
    "docker.io/prom/node-exporter:latest"
    "docker.io/zcube/cadvisor:latest"
    "docker.io/grafana/grafana:latest"
    "docker.io/nginx:alpine"
)

# Function to pull and save image
pull_and_save() {
    local image=$1
    local filename=$(echo $image | tr '/:' '_')
    local tar_file="$IMAGES_DIR/${filename}.tar"

    echo "Processing: $image"

    # Check if already saved
    if [ -f "$tar_file" ]; then
        echo "  Already exists: $tar_file"
        return 0
    fi

    # Pull image
    echo "  Pulling..."
    if $RUNTIME pull "$image"; then
        # Save to tar
        echo "  Saving to tar..."
        if $RUNTIME save -o "$tar_file" "$image"; then
            local size=$(du -h "$tar_file" | cut -f1)
            echo "  Saved: $tar_file ($size)"
            return 0
        else
            echo "  Failed to save $image"
            rm -f "$tar_file"
            return 1
        fi
    else
        echo "  Failed to pull $image"
        return 1
    fi
}

# Download all images
TOTAL=${#IMAGES[@]}
SUCCESS=0
FAILED=0

echo ""
echo "Downloading $TOTAL container images..."
echo ""

for image in "${IMAGES[@]}"; do
    if pull_and_save "$image"; then
        ((SUCCESS++))
    else
        ((FAILED++))
    fi
    echo ""
done

# Summary
echo "=========================================="
echo "Download Summary:"
echo "  Total: $TOTAL"
echo "  Success: $SUCCESS"
echo "  Failed: $FAILED"
echo ""

if [ -d "$IMAGES_DIR" ]; then
    TOTAL_SIZE=$(du -sh "$IMAGES_DIR" | cut -f1)
    FILE_COUNT=$(ls -1 "$IMAGES_DIR"/*.tar 2>/dev/null | wc -l)
    echo "Downloaded images:"
    echo "  Directory: $IMAGES_DIR"
    echo "  Files: $FILE_COUNT"
    echo "  Total size: $TOTAL_SIZE"
fi

echo "=========================================="

if [ $SUCCESS -gt 0 ]; then
    echo "Container images ready for air-gap deployment!"
    exit 0
else
    echo "No images were downloaded successfully."
    exit 1
fi