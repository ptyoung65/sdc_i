#!/bin/bash

# Batch container images download script for air-gap deployment
set +e  # Continue on error

echo "=========================================="
echo "SDC Container Images Batch Download"
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

# List of required images
IMAGES=(
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

# Download each image
for image in "${IMAGES[@]}"; do
    filename=$(echo $image | tr '/:' '_')
    tar_file="$IMAGES_DIR/${filename}.tar"

    echo ""
    echo "Processing: $image"

    if [ -f "$tar_file" ]; then
        echo "  Already exists, skipping"
        continue
    fi

    echo "  Pulling..."
    if timeout 300 $RUNTIME pull "$image" 2>/dev/null; then
        echo "  Saving to tar..."
        if $RUNTIME save -o "$tar_file" "$image" 2>/dev/null; then
            size=$(du -h "$tar_file" | cut -f1)
            echo "  ✓ Saved: $tar_file ($size)"
        else
            echo "  ✗ Failed to save"
            rm -f "$tar_file"
        fi
    else
        echo "  ✗ Failed to pull (timeout or error)"
    fi
done

# Summary
echo ""
echo "=========================================="
if [ -d "$IMAGES_DIR" ]; then
    FILE_COUNT=$(ls -1 "$IMAGES_DIR"/*.tar 2>/dev/null | wc -l)
    TOTAL_SIZE=$(du -sh "$IMAGES_DIR" 2>/dev/null | cut -f1)
    echo "Downloaded images: $FILE_COUNT files, Total: $TOTAL_SIZE"
    echo ""
    ls -lh "$IMAGES_DIR"/*.tar 2>/dev/null
fi
echo "=========================================="