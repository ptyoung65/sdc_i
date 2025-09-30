#!/bin/bash

# Container images download script for USB storage
set +e  # Continue on error

echo "=========================================="
echo "SDC Container Images Download to USB"
echo "=========================================="

# Create images directory in USB
IMAGES_DIR="/mnt/usb/sdc_i/container_images_usb"
mkdir -p "$IMAGES_DIR"

# Detect container runtime
if command -v podman &> /dev/null; then
    RUNTIME="podman"
elif command -v docker &> /dev/null; then
    RUNTIME="docker"
else
    echo "Error: No container runtime found"
    exit 1
fi

echo "Using container runtime: $RUNTIME"
echo "Images will be saved to: $IMAGES_DIR"

# Check available space
echo "Available space on /mnt/usb:"
df -h /mnt/usb

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

echo ""
echo "Starting download of ${#IMAGES[@]} container images..."

# Download function with error handling
download_image() {
    local image=$1
    local filename=$(echo $image | tr '/:' '_')
    local tar_file="$IMAGES_DIR/${filename}.tar"

    echo ""
    echo "[$((++counter))/${#IMAGES[@]}] Processing: $image"

    if [ -f "$tar_file" ]; then
        echo "  Already exists, skipping"
        return 0
    fi

    echo "  Pulling image..."
    if timeout 600 $RUNTIME pull "$image" 2>&1; then
        echo "  Saving to tar..."
        if $RUNTIME save -o "$tar_file" "$image" 2>&1; then
            local size=$(du -h "$tar_file" | cut -f1)
            echo "  ✓ Saved: $(basename $tar_file) ($size)"

            # Show remaining space
            local free_space=$(df -h /mnt/usb | tail -1 | awk '{print $4}')
            echo "    Free space remaining: $free_space"

            return 0
        else
            echo "  ✗ Failed to save image"
            rm -f "$tar_file"
            return 1
        fi
    else
        echo "  ✗ Failed to pull image"
        return 1
    fi
}

# Download all images
counter=0
success=0
failed=0

for image in "${IMAGES[@]}"; do
    if download_image "$image"; then
        ((success++))
    else
        ((failed++))
    fi
done

# Final summary
echo ""
echo "=========================================="
echo "Download Summary:"
echo "  Total: ${#IMAGES[@]}"
echo "  Success: $success"
echo "  Failed: $failed"
echo ""

if [ -d "$IMAGES_DIR" ]; then
    FILE_COUNT=$(ls -1 "$IMAGES_DIR"/*.tar 2>/dev/null | wc -l)
    TOTAL_SIZE=$(du -sh "$IMAGES_DIR" 2>/dev/null | cut -f1)
    echo "Downloaded images in $IMAGES_DIR:"
    echo "  Files: $FILE_COUNT"
    echo "  Total size: $TOTAL_SIZE"
    echo ""
    echo "Image files:"
    ls -lh "$IMAGES_DIR"/*.tar 2>/dev/null
fi

echo ""
echo "Final disk usage on /mnt/usb:"
df -h /mnt/usb
echo "=========================================="

if [ $success -gt 0 ]; then
    echo "✓ Container images ready for airgap deployment!"
    exit 0
else
    echo "✗ No images downloaded successfully"
    exit 1
fi