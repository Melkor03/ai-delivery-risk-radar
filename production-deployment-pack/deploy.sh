#!/bin/bash
# ============================================
# Risk Radar - Production Deployment Script
# ============================================
# Usage: ./deploy.sh [setup|start|stop|restart|logs|status|backup]
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
COMPOSE_FILE="docker-compose.prod.yml"
PROJECT_NAME="riskradar"
BACKUP_DIR="./backups"

# Functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    log_success "Prerequisites met!"
}

# Setup production environment
setup() {
    log_info "Setting up production environment..."
    
    # Check for .env file
    if [ ! -f .env ]; then
        if [ -f .env.production.template ]; then
            log_warning ".env file not found. Creating from template..."
            cp .env.production.template .env
            log_warning "Please edit .env file with your production values!"
            log_warning "Run: nano .env"
            exit 1
        else
            log_error ".env.production.template not found!"
            exit 1
        fi
    fi
    
    # Create necessary directories
    mkdir -p nginx/ssl
    mkdir -p nginx/logs
    mkdir -p $BACKUP_DIR
    
    # Generate SSL certificates (self-signed for testing)
    if [ ! -f nginx/ssl/server.crt ]; then
        log_info "Generating self-signed SSL certificate..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/server.key \
            -out nginx/ssl/server.crt \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" \
            2>/dev/null
        log_warning "Self-signed certificate created. Use Let's Encrypt for production!"
    fi
    
    # Build images
    log_info "Building Docker images..."
    docker-compose -f $COMPOSE_FILE build
    
    log_success "Setup complete! Run './deploy.sh start' to launch."
}

# Start services
start() {
    log_info "Starting Risk Radar services..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d
    
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    # Health check
    if curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
        log_success "Backend is healthy!"
    else
        log_warning "Backend health check failed. Check logs with './deploy.sh logs backend'"
    fi
    
    log_success "Risk Radar is running!"
    log_info "Frontend: http://localhost"
    log_info "Backend API: http://localhost:8001"
}

# Stop services
stop() {
    log_info "Stopping Risk Radar services..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down
    log_success "Services stopped."
}

# Restart services
restart() {
    log_info "Restarting Risk Radar services..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME restart
    log_success "Services restarted."
}

# Show logs
logs() {
    SERVICE=${2:-""}
    if [ -n "$SERVICE" ]; then
        docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f $SERVICE
    else
        docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f
    fi
}

# Show status
status() {
    log_info "Service Status:"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps
    
    echo ""
    log_info "Health Checks:"
    
    # Backend
    if curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
        echo -e "  Backend:  ${GREEN}✓ Healthy${NC}"
    else
        echo -e "  Backend:  ${RED}✗ Unhealthy${NC}"
    fi
    
    # Frontend
    if curl -s http://localhost > /dev/null 2>&1; then
        echo -e "  Frontend: ${GREEN}✓ Healthy${NC}"
    else
        echo -e "  Frontend: ${RED}✗ Unhealthy${NC}"
    fi
    
    # MongoDB
    if docker exec ${PROJECT_NAME}-mongodb mongosh --eval "db.runCommand({ping:1})" > /dev/null 2>&1; then
        echo -e "  MongoDB:  ${GREEN}✓ Healthy${NC}"
    else
        echo -e "  MongoDB:  ${RED}✗ Unhealthy${NC}"
    fi
}

# Backup database
backup() {
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="${BACKUP_DIR}/mongodb_backup_${TIMESTAMP}.gz"
    
    log_info "Creating database backup..."
    
    docker exec ${PROJECT_NAME}-mongodb mongodump --archive --gzip | cat > $BACKUP_FILE
    
    if [ -f "$BACKUP_FILE" ]; then
        log_success "Backup created: $BACKUP_FILE"
        
        # Keep only last 7 backups
        ls -t ${BACKUP_DIR}/mongodb_backup_*.gz | tail -n +8 | xargs -r rm
        log_info "Old backups cleaned up (keeping last 7)"
    else
        log_error "Backup failed!"
        exit 1
    fi
}

# Restore database
restore() {
    BACKUP_FILE=$2
    
    if [ -z "$BACKUP_FILE" ]; then
        log_error "Please specify backup file: ./deploy.sh restore <backup_file>"
        log_info "Available backups:"
        ls -la ${BACKUP_DIR}/mongodb_backup_*.gz 2>/dev/null || echo "  No backups found"
        exit 1
    fi
    
    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
    
    log_warning "This will OVERWRITE the current database!"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log_info "Restore cancelled."
        exit 0
    fi
    
    log_info "Restoring database from $BACKUP_FILE..."
    cat $BACKUP_FILE | docker exec -i ${PROJECT_NAME}-mongodb mongorestore --archive --gzip --drop
    
    log_success "Database restored!"
}

# Update application
update() {
    log_info "Pulling latest images..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME pull
    
    log_info "Recreating containers..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d --force-recreate
    
    log_info "Cleaning up old images..."
    docker image prune -f
    
    log_success "Update complete!"
}

# Generate secrets
generate_secrets() {
    log_info "Generating secure secrets..."
    
    echo ""
    echo "JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n')"
    echo ""
    echo "ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "Install cryptography: pip install cryptography")"
    echo ""
    echo "MONGO_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')"
    echo ""
    echo "REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')"
    echo ""
    
    log_info "Copy these values to your .env file"
}

# Show help
show_help() {
    echo ""
    echo "Risk Radar Deployment Script"
    echo "============================"
    echo ""
    echo "Usage: ./deploy.sh <command>"
    echo ""
    echo "Commands:"
    echo "  setup           - Initial setup (create .env, build images)"
    echo "  start           - Start all services"
    echo "  stop            - Stop all services"
    echo "  restart         - Restart all services"
    echo "  status          - Show service status and health"
    echo "  logs [service]  - Show logs (optionally for specific service)"
    echo "  backup          - Backup MongoDB database"
    echo "  restore <file>  - Restore database from backup"
    echo "  update          - Pull latest images and restart"
    echo "  secrets         - Generate secure secrets for .env"
    echo "  help            - Show this help message"
    echo ""
}

# Main
check_prerequisites

case "$1" in
    setup)
        setup
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs "$@"
        ;;
    status)
        status
        ;;
    backup)
        backup
        ;;
    restore)
        restore "$@"
        ;;
    update)
        update
        ;;
    secrets)
        generate_secrets
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
