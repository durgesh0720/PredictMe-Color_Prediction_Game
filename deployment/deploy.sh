#!/bin/bash

# Production Deployment Script for Color Prediction Game
# This script handles the complete deployment process with safety checks

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="colorprediction"
BACKUP_DIR="/backups"
LOG_FILE="/var/log/deploy.log"
HEALTH_CHECK_URL="http://localhost/health/"
MAX_DEPLOY_TIME=600  # 10 minutes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker is not running"
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
    fi
    
    # Check if .env file exists
    if [[ ! -f .env ]]; then
        error ".env file not found. Please create it with required environment variables"
    fi
    
    # Check required environment variables
    source .env
    required_vars=("SECRET_KEY" "DB_NAME" "DB_USER" "DB_PASSWORD" "ALLOWED_HOSTS")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error "Required environment variable $var is not set"
        fi
    done
    
    success "Prerequisites check passed"
}

# Create backup
create_backup() {
    log "Creating backup..."
    
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="${PROJECT_NAME}_backup_${backup_timestamp}"
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    if docker-compose -f docker-compose.production.yml exec -T db pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_DIR/${backup_name}_db.sql"; then
        success "Database backup created: ${backup_name}_db.sql"
    else
        error "Failed to create database backup"
    fi
    
    # Backup media files
    if docker-compose -f docker-compose.production.yml exec -T web tar -czf - /app/media > "$BACKUP_DIR/${backup_name}_media.tar.gz"; then
        success "Media backup created: ${backup_name}_media.tar.gz"
    else
        warning "Failed to create media backup (may not exist yet)"
    fi
    
    # Keep only last 7 backups
    find "$BACKUP_DIR" -name "${PROJECT_NAME}_backup_*" -type f -mtime +7 -delete
    
    echo "$backup_name" > "$BACKUP_DIR/latest_backup.txt"
}

# Health check function
health_check() {
    local max_attempts=30
    local attempt=1
    
    log "Performing health check..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$HEALTH_CHECK_URL" > /dev/null; then
            success "Health check passed"
            return 0
        fi
        
        log "Health check attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    error "Health check failed after $max_attempts attempts"
}

# Rollback function
rollback() {
    warning "Rolling back deployment..."
    
    # Get latest backup
    if [[ -f "$BACKUP_DIR/latest_backup.txt" ]]; then
        local backup_name=$(cat "$BACKUP_DIR/latest_backup.txt")
        
        # Restore database
        if [[ -f "$BACKUP_DIR/${backup_name}_db.sql" ]]; then
            log "Restoring database from backup..."
            docker-compose -f docker-compose.production.yml exec -T db psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_DIR/${backup_name}_db.sql"
        fi
        
        # Restore media files
        if [[ -f "$BACKUP_DIR/${backup_name}_media.tar.gz" ]]; then
            log "Restoring media files from backup..."
            docker-compose -f docker-compose.production.yml exec -T web tar -xzf - -C / < "$BACKUP_DIR/${backup_name}_media.tar.gz"
        fi
        
        success "Rollback completed"
    else
        error "No backup found for rollback"
    fi
}

# Deploy function
deploy() {
    log "Starting deployment..."
    
    # Pull latest images
    log "Pulling latest Docker images..."
    docker-compose -f docker-compose.production.yml pull
    
    # Build application image
    log "Building application image..."
    docker-compose -f docker-compose.production.yml build --no-cache web
    
    # Stop services gracefully
    log "Stopping services..."
    docker-compose -f docker-compose.production.yml down --timeout 30
    
    # Start database and Redis first
    log "Starting database and Redis..."
    docker-compose -f docker-compose.production.yml up -d db redis
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    sleep 10
    
    # Run database migrations
    log "Running database migrations..."
    docker-compose -f docker-compose.production.yml run --rm web python manage.py migrate --settings=production_settings
    
    # Collect static files
    log "Collecting static files..."
    docker-compose -f docker-compose.production.yml run --rm web python manage.py collectstatic --noinput --settings=production_settings
    
    # Start all services
    log "Starting all services..."
    docker-compose -f docker-compose.production.yml up -d
    
    # Wait for services to start
    sleep 30
    
    success "Deployment completed"
}

# Cleanup function
cleanup() {
    log "Cleaning up..."
    
    # Remove unused Docker images
    docker image prune -f
    
    # Remove unused volumes
    docker volume prune -f
    
    success "Cleanup completed"
}

# Main deployment process
main() {
    log "Starting Color Prediction Game deployment"
    
    # Trap errors and rollback
    trap 'error "Deployment failed, initiating rollback..."; rollback' ERR
    
    check_root
    check_prerequisites
    create_backup
    deploy
    health_check
    cleanup
    
    success "Deployment completed successfully!"
    log "Application is now running at: $HEALTH_CHECK_URL"
}

# Command line options
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        rollback
        ;;
    "backup")
        create_backup
        ;;
    "health")
        health_check
        ;;
    "cleanup")
        cleanup
        ;;
    "logs")
        docker-compose -f docker-compose.production.yml logs -f "${2:-}"
        ;;
    "status")
        docker-compose -f docker-compose.production.yml ps
        ;;
    "stop")
        log "Stopping all services..."
        docker-compose -f docker-compose.production.yml down
        success "All services stopped"
        ;;
    "start")
        log "Starting all services..."
        docker-compose -f docker-compose.production.yml up -d
        success "All services started"
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|backup|health|cleanup|logs|status|stop|start}"
        echo ""
        echo "Commands:"
        echo "  deploy   - Full deployment with backup and health checks"
        echo "  rollback - Rollback to previous backup"
        echo "  backup   - Create backup only"
        echo "  health   - Run health check"
        echo "  cleanup  - Clean up unused Docker resources"
        echo "  logs     - Show logs (optionally specify service)"
        echo "  status   - Show service status"
        echo "  stop     - Stop all services"
        echo "  start    - Start all services"
        exit 1
        ;;
esac
