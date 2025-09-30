#!/bin/bash
set -e

# SDC Services Stop Script for Air-gap Environment
# Stops all SDC services gracefully

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Determine project root - use current directory if it contains docker-compose.yml
if [ -f "$(pwd)/docker-compose.yml" ]; then
    PROJECT_ROOT="$(pwd)"
elif [ -f "$DEFAULT_PROJECT_ROOT/docker-compose.yml" ]; then
    PROJECT_ROOT="$DEFAULT_PROJECT_ROOT"
else
    # Try to find docker-compose.yml in parent directories
    current_dir="$(pwd)"
    while [ "$current_dir" != "/" ]; do
        if [ -f "$current_dir/docker-compose.yml" ]; then
            PROJECT_ROOT="$current_dir"
            break
        fi
        current_dir="$(dirname "$current_dir")"
    done
    
    if [ -z "$PROJECT_ROOT" ]; then
        PROJECT_ROOT="$DEFAULT_PROJECT_ROOT"
    fi
fi

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

# Determine compose command
get_compose_command() {
    if command -v podman-compose &> /dev/null; then
        echo "podman-compose"
    elif command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        log_error "Neither podman-compose nor docker-compose is available"
        exit 1
    fi
}

# Stop services gracefully
stop_services() {
    local compose_cmd=$(get_compose_command)
    
    log_info "Using $compose_cmd to stop services"
    
    cd "$PROJECT_ROOT"
    
    log_info "Stopping all SDC services..."
    
    # Stop services in reverse order (graceful shutdown)
    log_info "Stopping Nginx reverse proxy..."
    $compose_cmd stop nginx || log_warning "Nginx was not running"
    
    log_info "Stopping monitoring services..."
    $compose_cmd stop prometheus grafana node-exporter cadvisor || log_warning "Some monitoring services were not running"
    
    log_info "Stopping application services..."
    $compose_cmd stop frontend backend || log_warning "Some application services were not running"
    
    log_info "Stopping RAG microservices..."
    $compose_cmd stop korean-rag graph-rag keyword-rag text-to-sql-rag || log_warning "Some microservices were not running"
    
    log_info "Stopping support services..."
    $compose_cmd stop docling searxng || log_warning "Some support services were not running"
    
    log_info "Stopping database services..."
    $compose_cmd stop postgres redis milvus elasticsearch || log_warning "Some database services were not running"
    
    log_success "All services stopped"
}

# Remove containers (optional)
remove_containers() {
    local compose_cmd=$(get_compose_command)
    
    cd "$PROJECT_ROOT"
    
    if [ "$1" == "--remove" ] || [ "$1" == "-r" ]; then
        log_info "Removing stopped containers..."
        $compose_cmd rm -f
        log_success "Containers removed"
    fi
}

# Clean up volumes (optional)
cleanup_volumes() {
    if [ "$1" == "--clean" ] || [ "$1" == "-c" ]; then
        log_warning "This will remove all data volumes. Are you sure? (y/N)"
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            local compose_cmd=$(get_compose_command)
            
            cd "$PROJECT_ROOT"
            
            log_info "Removing volumes..."
            $compose_cmd down -v
            log_warning "All data volumes have been removed"
        else
            log_info "Volume cleanup cancelled"
        fi
    fi
}

# Show running services
show_status() {
    local compose_cmd=$(get_compose_command)
    
    cd "$PROJECT_ROOT"
    
    log_info "Current service status:"
    $compose_cmd ps
}

# Display usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -r, --remove    Remove stopped containers"
    echo "  -c, --clean     Remove all data volumes (WARNING: This will delete all data!)"
    echo "  -s, --status    Show current service status"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Stop all services"
    echo "  $0 --remove           # Stop services and remove containers"
    echo "  $0 --clean            # Stop services and remove all data"
    echo "  $0 --status           # Show current status"
}

# Main function
main() {
    case "${1:-}" in
        -h|--help)
            show_usage
            exit 0
            ;;
        -s|--status)
            show_status
            exit 0
            ;;
        -c|--clean)
            echo "=================================="
            echo "Stopping SDC Services (with cleanup)"
            echo "=================================="
            stop_services
            remove_containers "--remove"
            cleanup_volumes "--clean"
            ;;
        -r|--remove)
            echo "=================================="
            echo "Stopping SDC Services (removing containers)"
            echo "=================================="
            stop_services
            remove_containers "--remove"
            ;;
        "")
            echo "=================================="
            echo "Stopping SDC Services"
            echo "=================================="
            stop_services
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
    
    if [ "$1" != "-s" ] && [ "$1" != "--status" ]; then
        echo ""
        log_success "SDC services have been stopped successfully"
        echo ""
        log_info "To start services again, run:"
        echo "  $PROJECT_ROOT/scripts/start_services.sh"
        echo ""
        log_info "To check status, run:"
        echo "  $0 --status"
    fi
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi