#!/bin/bash

# Final Air-gap Package Creator - Local Version
set -e

echo "=========================================="
echo "SDC Final Air-gap Package Creator (Local)"
echo "Including container images, source code, and dependencies"
echo "=========================================="

# Configuration
PROJECT_ROOT="/mnt/usb/sdc_i"
PACKAGE_DIR="$PROJECT_ROOT/airgap_package_final"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FINAL_PACKAGE="sdc-complete-airgap-${TIMESTAMP}.tar.gz"

echo "Project root: $PROJECT_ROOT"
echo "Package directory: $PACKAGE_DIR"
echo "Final package: $FINAL_PACKAGE"

# Create package directory
rm -rf "$PACKAGE_DIR" 2>/dev/null || true
mkdir -p "$PACKAGE_DIR"

echo ""
echo "1. Copying complete source code..."
# Copy everything except .git and large build artifacts
rsync -av --exclude='.git' \
          --exclude='__pycache__' \
          --exclude='*.pyc' \
          --exclude='.pytest_cache' \
          --exclude='staging-complete' \
          --exclude='airgap_package_final' \
          --exclude='*.tar.gz' \
          "$PROJECT_ROOT/" "$PACKAGE_DIR/sdc_project/"

echo ""
echo "2. Including container images..."
if [ -d "$PROJECT_ROOT/container_images_usb" ]; then
    cp -r "$PROJECT_ROOT/container_images_usb" "$PACKAGE_DIR/container_images"
    IMAGE_COUNT=$(ls -1 "$PACKAGE_DIR/container_images"/*.tar 2>/dev/null | wc -l)
    IMAGE_SIZE=$(du -sh "$PACKAGE_DIR/container_images" | cut -f1)
    echo "  ✓ Copied $IMAGE_COUNT container images ($IMAGE_SIZE)"
else
    echo "  ⚠ No container images found"
fi

echo ""
echo "3. Creating installation script..."
cat > "$PACKAGE_DIR/install_airgap_complete.sh" << 'EOF'
#!/bin/bash
set -e

echo "=========================================="
echo "SDC Complete Air-gap Installation"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Default installation directory
INSTALL_DIR="/opt/sdc"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -d, --dir PATH    Installation directory (default: /opt/sdc)"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

log_info "Installing SDC to: $INSTALL_DIR"

# Check permissions
if [[ "$INSTALL_DIR" == /opt/* ]] && [ "$EUID" -ne 0 ]; then
    log_error "Root privileges required for system installation"
    log_info "Run with sudo or choose a different directory with -d option"
    exit 1
fi

# Create installation directory
mkdir -p "$INSTALL_DIR"

# Copy project files
if [ -d "sdc_project" ]; then
    log_info "Copying project files..."
    cp -r sdc_project/* "$INSTALL_DIR/"
    log_success "Project files copied"
else
    log_error "sdc_project directory not found"
    exit 1
fi

# Detect container runtime
RUNTIME=""
if command -v podman &> /dev/null; then
    RUNTIME="podman"
elif command -v docker &> /dev/null; then
    RUNTIME="docker"
fi

# Load container images
if [ -d "container_images" ] && [ -n "$RUNTIME" ]; then
    log_info "Loading container images with $RUNTIME..."
    IMAGE_COUNT=0
    for img in container_images/*.tar; do
        if [ -f "$img" ]; then
            log_info "Loading: $(basename $img)"
            $RUNTIME load -i "$img"
            ((IMAGE_COUNT++))
        fi
    done
    log_success "Loaded $IMAGE_COUNT container images"
elif [ -d "container_images" ]; then
    log_warning "Container images found but no runtime available"
    log_info "Install podman or docker to use container images"
elif [ -n "$RUNTIME" ]; then
    log_warning "No container images found"
else
    log_warning "No container runtime or images available"
fi

# Setup environment
cd "$INSTALL_DIR"

if [ -f ".env.example" ] && [ ! -f ".env" ]; then
    cp .env.example .env
    log_info "Created .env file from template"
    log_warning "Edit .env file to configure API keys"
fi

# Make scripts executable
if [ -d "scripts" ]; then
    chmod +x scripts/*.sh 2>/dev/null || true
    chmod +x scripts/*.py 2>/dev/null || true
fi

echo ""
echo "=========================================="
log_success "SDC Complete Air-gap Installation Complete!"
echo "=========================================="
echo ""
log_info "Installation location: $INSTALL_DIR"
echo ""

if [ -n "$RUNTIME" ]; then
    log_info "Container services:"
    echo "  Start all: cd $INSTALL_DIR && $RUNTIME-compose up -d"
    echo "  Stop all: $RUNTIME-compose down"
fi

log_info "Local services:"
echo "  Backend: cd $INSTALL_DIR/backend && python simple_api.py"
echo "  Frontend: cd $INSTALL_DIR/frontend && npm run dev"
echo ""

log_info "Access URLs:"
echo "  Frontend: http://localhost:3000"
echo "  Backend API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""

log_warning "Next steps:"
echo "  1. Configure .env file: nano $INSTALL_DIR/.env"
echo "  2. Ensure ports 3000, 8000 are available"
echo "  3. Start services as needed"
echo ""
EOF

chmod +x "$PACKAGE_DIR/install_airgap_complete.sh"

echo ""
echo "4. Creating comprehensive README..."
cat > "$PACKAGE_DIR/README.md" << EOF
# SDC Korean RAG System - Complete Air-gap Package

## 🚀 Complete Offline Deployment Package

This package contains everything needed to run the SDC Korean RAG System in a completely offline environment:

- ✅ Complete source code
- ✅ Container images ($(ls -1 "$PACKAGE_DIR/container_images"/*.tar 2>/dev/null | wc -l) images)
- ✅ Python virtual environments with dependencies
- ✅ Node.js dependencies
- ✅ Installation scripts and documentation

**Total package size:** $(du -sh "$PACKAGE_DIR" | cut -f1) (uncompressed)

## 📦 Package Contents

\`\`\`
sdc-complete-airgap/
├── README.md                      # This file
├── install_airgap_complete.sh     # Installation script
├── container_images/              # Pre-downloaded container images
│   ├── docker.io_redis_7-alpine.tar
│   ├── docker.io_milvusdb_milvus_v2.3.3.tar
│   └── ... ($(ls -1 "$PACKAGE_DIR/container_images"/*.tar 2>/dev/null | wc -l) total images)
└── sdc_project/                   # Complete project source
    ├── backend/                   # FastAPI backend
    ├── frontend/                  # Next.js frontend
    ├── services/                  # Microservices
    ├── scripts/                   # Management scripts
    └── docker-compose.yml         # Container orchestration
\`\`\`

## ⚡ Quick Installation

### 1. Extract Package
\`\`\`bash
tar -xzf sdc-complete-airgap-*.tar.gz
cd sdc-complete-airgap
\`\`\`

### 2. Install
\`\`\`bash
# System-wide installation (requires sudo)
sudo ./install_airgap_complete.sh

# Or custom location
./install_airgap_complete.sh -d /your/path/sdc
\`\`\`

### 3. Configure
\`\`\`bash
cd [installation_path]
nano .env  # Add your API keys
\`\`\`

### 4. Run Services

**Using Containers:**
\`\`\`bash
podman-compose up -d  # or docker-compose up -d
\`\`\`

**Or locally:**
\`\`\`bash
# Backend (terminal 1)
cd backend
python simple_api.py

# Frontend (terminal 2)
cd frontend
npm run dev
\`\`\`

## 🎯 Access Points

- **Frontend UI:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs

## 💻 System Requirements

### Minimum:
- **OS:** Linux (Ubuntu 20.04+, CentOS 8+)
- **RAM:** 16GB minimum, 32GB recommended
- **Storage:** $(du -sh "$PACKAGE_DIR" | cut -f1) for package + 50GB for operation
- **Python:** 3.8+

### Recommended:
- **Container Runtime:** Podman or Docker
- **Node.js:** 18+ (for frontend development)

## ✅ Included Components

### Container Images ($(ls -1 "$PACKAGE_DIR/container_images"/*.tar 2>/dev/null | wc -l) images)
$(for img in "$PACKAGE_DIR/container_images"/*.tar 2>/dev/null; do
    if [ -f "$img" ]; then
        basename "$img" .tar | sed 's/_/\//g; s/docker\.io\///g' | sed 's/^/- /'
    fi
done 2>/dev/null || echo "- Container images included")

### Backend Services
- FastAPI + Uvicorn server
- SQLAlchemy with PostgreSQL support
- LangChain + LangGraph RAG pipeline
- Multi-format document processing
- Korean-optimized embeddings

### Frontend Application
- Next.js 15 with React
- TypeScript + Tailwind CSS
- Radix UI components
- Real-time chat interface

## 🛠 Development Ready

This package is ready for immediate development:
- All dependencies pre-installed
- Development servers ready to start
- Hot-reload capabilities
- Complete development toolchain

## 📞 Troubleshooting

### Common Issues

1. **Port conflicts:**
   \`\`\`bash
   sudo netstat -tlnp | grep -E "3000|8000"
   \`\`\`

2. **Permission issues:**
   \`\`\`bash
   sudo chown -R \$(whoami):\$(whoami) /installation/path
   \`\`\`

3. **Container runtime not found:**
   - Install podman: \`sudo apt install podman\`
   - Or install docker: \`sudo apt install docker.io\`

## 🚀 Ready for Production

This package can be deployed in completely offline environments with all dependencies included.

---

**SDC Korean RAG System v1.0**
Complete Air-gap Deployment Package
Generated: $(date)
EOF

echo ""
echo "5. Creating final compressed package..."
cd "$PROJECT_ROOT"
tar -czf "$FINAL_PACKAGE" -C "." "airgap_package_final"

# Calculate final sizes
PACKAGE_SIZE=$(du -sh "$PACKAGE_DIR" | cut -f1)
COMPRESSED_SIZE=$(du -sh "$FINAL_PACKAGE" | cut -f1)

echo ""
echo "=========================================="
echo "✅ Final Air-gap Package Created Successfully!"
echo "=========================================="
echo ""
echo "📦 Package: $PROJECT_ROOT/$FINAL_PACKAGE"
echo "📏 Uncompressed: $PACKAGE_SIZE"
echo "📏 Compressed: $COMPRESSED_SIZE"
echo ""

if [ -d "$PROJECT_ROOT/container_images_usb" ]; then
    IMAGE_COUNT=$(ls -1 "$PROJECT_ROOT/container_images_usb"/*.tar 2>/dev/null | wc -l)
    IMAGE_SIZE=$(du -sh "$PROJECT_ROOT/container_images_usb" | cut -f1)
    echo "🐳 Container Images: $IMAGE_COUNT files ($IMAGE_SIZE)"
fi

echo ""
echo "✅ Package Contents:"
echo "  • Complete source code"
echo "  • All container images"
echo "  • Installation scripts"
echo "  • Documentation"
echo ""
echo "🚀 To deploy on air-gap server:"
echo "  1. Transfer: $FINAL_PACKAGE"
echo "  2. Extract: tar -xzf $(basename "$FINAL_PACKAGE")"
echo "  3. Install: sudo ./install_airgap_complete.sh"
echo "  4. Configure: Edit .env file"
echo "  5. Run: Start services"
echo ""
echo "✅ Ready for complete offline deployment!"
echo "=========================================="