#!/bin/bash

set -e

echo "=========================================="
echo "Docker Compose Billing Service Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_info "Creating .env file from .env.example..."
    cp .env.example .env
    print_success ".env file created"
else
    print_success ".env file exists"
fi

# Validate docker-compose.yml
print_info "Validating docker-compose.yml syntax..."
if docker compose config > /dev/null 2>&1; then
    print_success "docker-compose.yml is valid"
else
    print_error "docker-compose.yml has syntax errors"
    exit 1
fi

# Clean up any existing containers
print_info "Cleaning up existing containers..."
docker compose down -v > /dev/null 2>&1 || true
print_success "Cleanup complete"

echo ""
echo "=========================================="
echo "Starting Infrastructure Services"
echo "=========================================="
echo ""

# Start infrastructure services
print_info "Starting PostgreSQL database..."
docker compose up -d billing-db

print_info "Starting RabbitMQ..."
docker compose up -d rabbitmq

print_info "Starting Redis..."
docker compose up -d redis

echo ""
print_info "Waiting for services to be healthy (this may take 30-60 seconds)..."
sleep 10

# Check health of each service
check_service_health() {
    local service=$1
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker compose ps $service | grep -q "healthy"; then
            print_success "$service is healthy"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    print_error "$service failed to become healthy"
    return 1
}

echo ""
print_info "Checking billing-db health..."
check_service_health billing-db || exit 1

print_info "Checking rabbitmq health..."
check_service_health rabbitmq || exit 1

print_info "Checking redis health..."
check_service_health redis || exit 1

echo ""
echo "=========================================="
echo "Building and Starting Billing Service"
echo "=========================================="
echo ""

print_info "Building billing service image..."
if docker compose build billing-service; then
    print_success "Billing service image built successfully"
else
    print_error "Failed to build billing service image"
    exit 1
fi

print_info "Starting billing service..."
docker compose up -d billing-service

print_info "Waiting for billing service to be healthy..."
sleep 15

# Check billing service health
if check_service_health billing-service; then
    print_success "Billing service started successfully"
else
    print_error "Billing service failed to start"
    echo ""
    print_info "Showing billing service logs:"
    docker compose logs billing-service
    exit 1
fi

echo ""
echo "=========================================="
echo "Testing Billing Service Endpoints"
echo "=========================================="
echo ""

# Test health endpoint
print_info "Testing /health endpoint..."
sleep 5
if curl -f http://localhost:8004/health > /dev/null 2>&1; then
    print_success "Health endpoint is accessible"
    echo ""
    echo "Health check response:"
    curl -s http://localhost:8004/health | python3 -m json.tool
else
    print_error "Health endpoint is not accessible"
    docker compose logs billing-service
    exit 1
fi

echo ""
echo ""

# Test OpenAPI docs
print_info "Testing /docs endpoint..."
if curl -f http://localhost:8004/docs > /dev/null 2>&1; then
    print_success "API documentation is accessible at http://localhost:8004/docs"
else
    print_error "API documentation is not accessible"
fi

echo ""
echo "=========================================="
echo "Service Status"
echo "=========================================="
echo ""

docker compose ps

echo ""
echo "=========================================="
echo "Connection Information"
echo "=========================================="
echo ""

echo "✓ Billing Service API: http://localhost:8004"
echo "✓ API Documentation: http://localhost:8004/docs"
echo "✓ Health Check: http://localhost:8004/health"
echo "✓ PostgreSQL: localhost:5432 (billing_db)"
echo "✓ RabbitMQ Management: http://localhost:15672 (admin/rabbitmq_secure_password)"
echo "✓ Redis: localhost:6379"

echo ""
echo "=========================================="
echo "Useful Commands"
echo "=========================================="
echo ""

echo "View logs:"
echo "  docker compose logs -f billing-service"
echo ""
echo "Access database:"
echo "  docker compose exec billing-db psql -U postgres -d billing_db"
echo ""
echo "Stop all services:"
echo "  docker compose down"
echo ""
echo "Stop and remove volumes:"
echo "  docker compose down -v"
echo ""

echo "=========================================="
echo "All Tests Passed! ✓"
echo "=========================================="
