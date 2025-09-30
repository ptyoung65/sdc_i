#!/bin/bash
set -e

# SDC Services Start Script for Air-gap Environment
# Starts all SDC services using podman-compose

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if podman is available
    if ! command -v podman &> /dev/null; then
        log_error "Podman is not installed or not in PATH"
        exit 1
    fi
    
    # Check if podman-compose is available
    if ! command -v podman-compose &> /dev/null; then
        log_warning "podman-compose not found, trying docker-compose"
        if ! command -v docker-compose &> /dev/null; then
            log_error "Neither podman-compose nor docker-compose is available"
            exit 1
        else
            COMPOSE_CMD="docker-compose"
        fi
    else
        COMPOSE_CMD="podman-compose"
    fi
    
    log_success "Using $COMPOSE_CMD"
    
    # Check if .env file exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error ".env file not found. Please run install_airgap.sh first"
        exit 1
    fi
    
    log_success "Prerequisites check completed"
}

# Start database services first
start_database_services() {
    log_info "Starting database services (PostgreSQL, Redis, Milvus, Elasticsearch)..."
    
    cd "$PROJECT_ROOT"
    
    # Start only database services first
    $COMPOSE_CMD up -d postgres redis milvus elasticsearch
    
    # Wait for databases to be ready
    log_info "Waiting for databases to be ready..."
    sleep 30
    
    # Check health of database services
    local services=("postgres" "redis" "milvus" "elasticsearch")
    for service in "${services[@]}"; do
        if $COMPOSE_CMD ps | grep -q "$service.*Up"; then
            log_success "$service is running"
        else
            log_error "$service failed to start"
            return 1
        fi
    done
    
    log_success "Database services started successfully"
}

# Start support services
start_support_services() {
    log_info "Starting support services (Docling, SearXNG)..."
    
    cd "$PROJECT_ROOT"
    
    # Start support services
    $COMPOSE_CMD up -d docling searxng
    
    # Wait for support services
    log_info "Waiting for support services to be ready..."
    sleep 15
    
    log_success "Support services started"
}

# Start microservices
start_microservices() {
    log_info "Starting RAG microservices..."
    
    cd "$PROJECT_ROOT"
    
    # Start RAG microservices
    $COMPOSE_CMD up -d korean-rag graph-rag keyword-rag text-to-sql-rag
    
    # Wait for microservices
    log_info "Waiting for microservices to be ready..."
    sleep 20
    
    log_success "RAG microservices started"
}

# Start application services
start_application_services() {
    log_info "Starting application services (Backend, Frontend)..."
    
    cd "$PROJECT_ROOT"
    
    # Start backend first
    $COMPOSE_CMD up -d backend
    
    log_info "Waiting for backend to be ready..."
    sleep 15
    
    # Start frontend
    $COMPOSE_CMD up -d frontend
    
    log_info "Waiting for frontend to be ready..."
    sleep 10
    
    log_success "Application services started"
}

# Start monitoring services
start_monitoring_services() {
    log_info "Starting monitoring services (Prometheus, Grafana, Node Exporter)..."
    
    cd "$PROJECT_ROOT"
    
    # Start monitoring services
    $COMPOSE_CMD up -d prometheus node-exporter cadvisor grafana
    
    log_info "Waiting for monitoring services to be ready..."
    sleep 10
    
    log_success "Monitoring services started"
}

# Start nginx reverse proxy
start_nginx() {
    log_info "Starting Nginx reverse proxy..."
    
    cd "$PROJECT_ROOT"
    
    # Start nginx last
    $COMPOSE_CMD up -d nginx
    
    log_info "Waiting for Nginx to be ready..."
    sleep 5
    
    log_success "Nginx reverse proxy started"
}

# Check service health
check_service_health() {
    log_info "Checking service health..."
    
    cd "$PROJECT_ROOT"
    
    # List all running services
    log_info "Running services:"
    $COMPOSE_CMD ps
    
    # Check specific endpoints
    local endpoints=(
        "http://localhost:8000/health:Backend API"
        "http://localhost:3000:Frontend"
        "http://localhost:5432:PostgreSQL (port check)"
        "http://localhost:6379:Redis (port check)"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        local endpoint=$(echo "$endpoint_info" | cut -d':' -f1)
        local name=$(echo "$endpoint_info" | cut -d':' -f2)
        
        if curl -f -s "$endpoint" > /dev/null 2>&1; then
            log_success "$name is healthy"
        else
            log_warning "$name health check failed (this might be normal during startup)"
        fi
    done
}

# Display startup information
show_startup_info() {
    echo ""
    echo "==========================================="
    log_success "SDC Air-gap Services Started Successfully!"
    echo "==========================================="
    echo ""
    log_info "Service URLs:"
    echo "  • Main Application: http://localhost (via Nginx)"
    echo "  • Frontend:         http://localhost:3000"
    echo "  • Backend API:      http://localhost:8000"
    echo "  • API Docs:         http://localhost:8000/docs"
    echo "  • Grafana:          http://localhost:3010 (admin/admin123)"
    echo "  • Prometheus:       http://localhost:9090"
    echo "  • SearXNG:          http://localhost:8080"
    echo ""
    log_info "Database Connections:"
    echo "  • PostgreSQL:       localhost:5432"
    echo "  • Redis:            localhost:6379"
    echo "  • Milvus:           localhost:19530"
    echo "  • Elasticsearch:    localhost:9200"
    echo ""
    log_info "Management Commands:"
    echo "  • View logs:        $COMPOSE_CMD logs -f [service_name]"
    echo "  • Stop services:    $PROJECT_ROOT/scripts/stop_services.sh"
    echo "  • Restart service:  $COMPOSE_CMD restart [service_name]"
    echo ""
    log_warning "Note: It may take a few minutes for all services to be fully ready."
    log_info "Check logs if any service is not responding: $COMPOSE_CMD logs [service_name]"
}

# Main startup function
main() {
    echo "=================================="
    echo "Starting SDC Air-gap Services"
    echo "=================================="
    echo ""
    
    cd "$PROJECT_ROOT"
    
    # Check prerequisites
    check_prerequisites
    
    # Start services in order
    log_info "Starting services in proper order..."
    
    start_database_services
    start_support_services
    start_microservices
    start_application_services
    start_monitoring_services
    start_nginx
    
    # Final health check
    sleep 10
    check_service_health
    
    # Show startup information
    show_startup_info
}

# Handle script interruption
cleanup() {
    log_warning "Script interrupted. Services may be partially started."
    log_info "To stop all services, run: $PROJECT_ROOT/scripts/stop_services.sh"
    exit 1
}

trap cleanup INT TERM

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi