#!/bin/bash
set -e

# SDC Air-gap Installation Script
# Installs SDC (Smart Document Companion) Korean RAG System in air-gap environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Installation directory configuration
INSTALL_DIR=""
PROJECT_ROOT=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get installation directory from user
get_installation_directory() {
    echo "=================================="
    echo "SDC Installation Directory Setup"
    echo "=================================="
    echo ""
    
    log_info "현재 위치: $(pwd)"
    log_info "기본 설치 경로: $DEFAULT_PROJECT_ROOT"
    echo ""
    
    # Check if running with -y flag (non-interactive)
    if [ "$1" == "-y" ] || [ "$1" == "--yes" ]; then
        INSTALL_DIR="$DEFAULT_PROJECT_ROOT"
        log_info "Non-interactive mode: Using default installation directory"
    else
        # Interactive mode
        echo "SDC를 설치할 디렉토리를 선택하세요:"
        echo ""
        echo "1) 현재 위치에 설치: $(pwd)/sdc"
        echo "2) 추천 디렉토리에 설치: /home/chatpro/sdc_production"
        echo "3) /opt에 설치: /opt/sdc (관리자 권한 필요)"
        echo "4) 기본 위치에 설치: $DEFAULT_PROJECT_ROOT"
        echo "5) 사용자 지정 경로"
        echo ""
        
        while true; do
            read -p "선택하세요 (1-5) [기본값: 4]: " choice
            choice=${choice:-4}
            
            case $choice in
                1)
                    INSTALL_DIR="$(pwd)/sdc"
                    break
                    ;;
                2)
                    INSTALL_DIR="/home/chatpro/sdc_production"
                    break
                    ;;
                3)
                    INSTALL_DIR="/opt/sdc"
                    if [ "$EUID" -ne 0 ]; then
                        log_warning "/opt에 설치하려면 관리자 권한이 필요합니다."
                        log_info "sudo를 사용하여 다시 실행하거나 다른 위치를 선택하세요."
                        continue
                    fi
                    break
                    ;;
                4)
                    INSTALL_DIR="$DEFAULT_PROJECT_ROOT"
                    break
                    ;;
                5)
                    read -p "설치할 전체 경로를 입력하세요: " custom_path
                    if [ -z "$custom_path" ]; then
                        log_error "경로가 입력되지 않았습니다."
                        continue
                    fi
                    INSTALL_DIR="$custom_path"
                    break
                    ;;
                *)
                    log_error "잘못된 선택입니다. 1-5 중에서 선택하세요."
                    ;;
            esac
        done
    fi
    
    # Expand tilde to home directory
    INSTALL_DIR="${INSTALL_DIR/#\~/$HOME}"
    
    # Convert to absolute path
    INSTALL_DIR="$(cd "$(dirname "$INSTALL_DIR")" 2>/dev/null && pwd)/$(basename "$INSTALL_DIR")" || INSTALL_DIR="$(realpath "$INSTALL_DIR" 2>/dev/null)" || INSTALL_DIR="$INSTALL_DIR"
    
    echo ""
    log_info "선택된 설치 디렉토리: $INSTALL_DIR"
    
    # Check if directory exists and has content
    if [ -d "$INSTALL_DIR" ] && [ "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]; then
        log_warning "디렉토리가 존재하고 비어있지 않습니다: $INSTALL_DIR"
        
        if [ "$1" != "-y" ] && [ "$1" != "--yes" ]; then
            echo ""
            echo "다음 중 선택하세요:"
            echo "1) 계속 진행 (기존 파일과 병합)"
            echo "2) 다른 디렉토리 선택"
            echo "3) 설치 중단"
            
            read -p "선택하세요 (1-3) [기본값: 1]: " overwrite_choice
            overwrite_choice=${overwrite_choice:-1}
            
            case $overwrite_choice in
                1)
                    log_info "기존 디렉토리에 설치를 계속합니다."
                    ;;
                2)
                    get_installation_directory "$@"
                    return
                    ;;
                3)
                    log_info "설치를 중단합니다."
                    exit 0
                    ;;
                *)
                    log_info "기본값으로 계속 진행합니다."
                    ;;
            esac
        fi
    fi
    
    # Set PROJECT_ROOT to the installation directory
    PROJECT_ROOT="$INSTALL_DIR"
    
    echo ""
    log_success "설치 디렉토리 설정 완료: $PROJECT_ROOT"
}

# Check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_warning "Running as root. Some operations may require non-root user."
    fi
}

# Check system requirements
check_system_requirements() {
    log_info "Checking system requirements..."
    
    # Check OS
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log_error "This script is designed for Linux systems"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ $(echo "$python_version >= 3.8" | bc -l) -eq 0 ]]; then
        log_error "Python 3.8 or higher is required. Found: $python_version"
        exit 1
    fi
    
    log_success "Python $python_version found"
    
    # Check for required system packages
    required_packages=("curl" "wget" "tar" "gzip")
    missing_packages=()
    
    for pkg in "${required_packages[@]}"; do
        if ! command -v "$pkg" &> /dev/null; then
            missing_packages+=("$pkg")
        fi
    done
    
    if [ ${#missing_packages[@]} -ne 0 ]; then
        log_error "Missing required packages: ${missing_packages[*]}"
        log_info "Please install them using your package manager:"
        log_info "  Ubuntu/Debian: sudo apt-get install ${missing_packages[*]}"
        log_info "  RHEL/CentOS: sudo yum install ${missing_packages[*]}"
        exit 1
    fi
    
    log_success "System requirements satisfied"
}

# Install Podman if not present
install_podman() {
    if command -v podman &> /dev/null; then
        log_success "Podman already installed: $(podman --version)"
        return 0
    fi
    
    log_info "Installing Podman..."
    
    # Detect distribution
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log_error "Cannot detect OS distribution"
        exit 1
    fi
    
    case $OS in
        "Ubuntu"*)
            sudo apt-get update
            sudo apt-get install -y podman podman-compose
            ;;
        "Debian"*)
            sudo apt-get update
            sudo apt-get install -y podman podman-compose
            ;;
        "CentOS"*|"Red Hat"*)
            sudo yum install -y podman podman-compose
            ;;
        "Fedora"*)
            sudo dnf install -y podman podman-compose
            ;;
        *)
            log_error "Unsupported OS: $OS"
            log_info "Please install Podman manually: https://podman.io/getting-started/installation"
            exit 1
            ;;
    esac
    
    if command -v podman &> /dev/null; then
        log_success "Podman installed successfully: $(podman --version)"
    else
        log_error "Failed to install Podman"
        exit 1
    fi
}

# Copy project files to installation directory
copy_project_files() {
    log_info "Copying project files to installation directory..."
    
    local source_dir="$(dirname "$SCRIPT_DIR")"
    
    # Create installation directory
    mkdir -p "$PROJECT_ROOT"
    
    # Copy all files except .git and other excluded items
    log_info "Copying from $source_dir to $PROJECT_ROOT"
    
    # Use rsync if available for better copying, otherwise use cp
    if command -v rsync &> /dev/null; then
        rsync -av --exclude='.git' --exclude='venv' --exclude='.venv' --exclude='node_modules' \
              --exclude='__pycache__' --exclude='*.pyc' --exclude='logs' --exclude='uploads' \
              --exclude='processed' "$source_dir/" "$PROJECT_ROOT/"
    else
        cp -r "$source_dir"/* "$PROJECT_ROOT/" 2>/dev/null || true
        # Remove excluded directories if they were copied
        rm -rf "$PROJECT_ROOT/.git" "$PROJECT_ROOT/venv" "$PROJECT_ROOT/.venv" \
               "$PROJECT_ROOT/node_modules" "$PROJECT_ROOT/logs" \
               "$PROJECT_ROOT/uploads" "$PROJECT_ROOT/processed" 2>/dev/null || true
        find "$PROJECT_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null || true
    fi
    
    log_success "Project files copied to $PROJECT_ROOT"
}

# Install Python dependencies
install_python_dependencies() {
    log_info "Installing Python dependencies..."
    
    local python_wheels_dir="$PROJECT_ROOT/airgap-deployment/python-wheels"
    
    if [ ! -d "$python_wheels_dir" ]; then
        log_error "Python wheels directory not found: $python_wheels_dir"
        exit 1
    fi
    
    cd "$python_wheels_dir"
    
    if [ -f "install_python_deps.sh" ]; then
        log_info "Running Python dependencies installation script..."
        chmod +x install_python_deps.sh
        ./install_python_deps.sh
        log_success "Python dependencies installed"
    else
        log_error "Python installation script not found"
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Install Node.js dependencies
install_nodejs_dependencies() {
    log_info "Installing Node.js dependencies..."
    
    local nodejs_deps_dir="$PROJECT_ROOT/airgap-deployment/nodejs-deps"
    
    if [ ! -d "$nodejs_deps_dir" ]; then
        log_error "Node.js dependencies directory not found: $nodejs_deps_dir"
        exit 1
    fi
    
    cd "$nodejs_deps_dir"
    
    if [ -f "install_nodejs_deps.sh" ]; then
        log_info "Running Node.js dependencies installation script..."
        chmod +x install_nodejs_deps.sh
        ./install_nodejs_deps.sh
        log_success "Node.js dependencies installed"
    else
        log_error "Node.js installation script not found"
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Load container images
load_container_images() {
    log_info "Loading container images..."
    
    local images_dir="$PROJECT_ROOT/airgap-deployment/container-images"
    
    if [ ! -d "$images_dir" ]; then
        log_error "Container images directory not found: $images_dir"
        exit 1
    fi
    
    cd "$images_dir"
    
    if [ -f "load_container_images.sh" ]; then
        log_info "Running container images loading script..."
        chmod +x load_container_images.sh
        ./load_container_images.sh
        log_success "Container images loaded"
    else
        log_error "Container images loading script not found"
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Setup environment files
setup_environment() {
    log_info "Setting up environment configuration..."
    
    # Copy environment template if .env doesn't exist
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
            log_info "Created .env from .env.example"
            log_warning "Please edit .env file to configure API keys and other settings"
        else
            log_warning ".env.example not found. Creating basic .env file"
            cat > "$PROJECT_ROOT/.env" << 'EOF'
# SDC Air-gap Environment Configuration

# Database Configuration
POSTGRES_USER=sdc_user
POSTGRES_PASSWORD=sdc_password
POSTGRES_DB=sdc_db

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Services (Configure these with your API keys)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
GEMINI_API_KEY=

# Application Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000

# SearXNG
SEARXNG_SECRET=your-secret-key-change-in-production
EOF
        fi
    else
        log_success ".env file already exists"
    fi
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    local dirs=(
        "$PROJECT_ROOT/logs"
        "$PROJECT_ROOT/uploads"
        "$PROJECT_ROOT/processed"
        "$PROJECT_ROOT/data"
    )
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
    
    log_success "Directories created"
}

# Setup systemd services (optional)
setup_systemd_services() {
    if [ "$EUID" -ne 0 ]; then
        log_warning "Skipping systemd service setup (requires root)"
        return 0
    fi
    
    log_info "Setting up systemd services..."
    
    # Create SDC service file
    cat > /etc/systemd/system/sdc-airgap.service << EOF
[Unit]
Description=SDC Korean RAG System (Air-gap)
After=network.target

[Service]
Type=forking
User=sdc
Group=sdc
WorkingDirectory=$PROJECT_ROOT
ExecStart=$PROJECT_ROOT/scripts/start_services.sh
ExecStop=$PROJECT_ROOT/scripts/stop_services.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable sdc-airgap.service
    
    log_success "Systemd service configured"
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."
    
    # Check Python environment
    if [ -d "$PROJECT_ROOT/venv" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
        python -c "import fastapi, uvicorn" &> /dev/null
        if [ $? -eq 0 ]; then
            log_success "Python environment verified"
        else
            log_error "Python environment verification failed"
            return 1
        fi
        deactivate
    else
        log_warning "Python virtual environment not found"
    fi
    
    # Check Podman images
    local expected_images=("postgres" "redis" "milvus" "elasticsearch")
    local missing_images=()
    
    for image in "${expected_images[@]}"; do
        if ! podman images | grep -q "$image"; then
            missing_images+=("$image")
        fi
    done
    
    if [ ${#missing_images[@]} -eq 0 ]; then
        log_success "Container images verified"
    else
        log_warning "Missing container images: ${missing_images[*]}"
    fi
    
    log_success "Installation verification completed"
}

# Display usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -y, --yes           Non-interactive mode (use default installation directory)"
    echo "  -d, --dir PATH      Specify installation directory"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Interactive installation"
    echo "  $0 -y                                 # Non-interactive, default directory"  
    echo "  $0 -d /opt/sdc                       # Install to specific directory"
    echo "  $0 --dir ~/my-sdc --yes               # Non-interactive, custom directory"
    echo ""
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -y|--yes)
                NON_INTERACTIVE=true
                shift
                ;;
            -d|--dir)
                CUSTOM_INSTALL_DIR="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Main installation function
main() {
    # Parse command line arguments
    parse_arguments "$@"
    
    echo "=================================="
    echo "SDC Air-gap Installation Script"
    echo "=================================="
    echo ""
    
    # Get installation directory from user or command line
    if [ -n "$CUSTOM_INSTALL_DIR" ]; then
        # Custom directory specified via command line
        PROJECT_ROOT="$CUSTOM_INSTALL_DIR"
        PROJECT_ROOT="${PROJECT_ROOT/#\~/$HOME}"  # Expand tilde
        log_info "Using specified installation directory: $PROJECT_ROOT"
    else
        # Interactive or default directory selection
        if [ "$NON_INTERACTIVE" = true ]; then
            get_installation_directory "-y"
        else
            get_installation_directory
        fi
    fi
    
    check_root
    check_system_requirements
    
    log_info "Starting SDC air-gap installation to: $PROJECT_ROOT"
    
    # Installation steps
    install_podman
    copy_project_files
    create_directories
    setup_environment
    install_python_dependencies
    install_nodejs_dependencies  
    load_container_images
    setup_systemd_services
    verify_installation
    
    echo ""
    echo "=================================="
    log_success "SDC Air-gap Installation Completed!"
    echo "=================================="
    echo ""
    log_info "Installation directory: $PROJECT_ROOT"
    log_info "Next steps:"
    echo "1. Edit .env file to configure API keys and settings:"
    echo "   nano $PROJECT_ROOT/.env"
    echo "2. Start services:"
    echo "   $PROJECT_ROOT/scripts/start_services.sh"
    echo "3. Access the application at: http://localhost:3000"
    echo ""
    log_info "For more information, see: $PROJECT_ROOT/README.md"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi