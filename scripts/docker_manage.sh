#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service lists
INFRASTRUCTURE_SERVICES=("rabbitmq" "redis")
DATABASE_SERVICES=("patient-db" "appointment-db" "prescription-db" "billing-db")
MICROSERVICES=("patient-service" "appointment-service" "prescription-service" "billing-service")
GATEWAY_SERVICES=("kong")
MONITORING_SERVICES=("prometheus" "grafana")

ALL_SERVICES=("${INFRASTRUCTURE_SERVICES[@]}" "${DATABASE_SERVICES[@]}" "${MICROSERVICES[@]}" "${GATEWAY_SERVICES[@]}" "${MONITORING_SERVICES[@]}")

# Helper functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

print_section() {
    echo ""
    echo -e "${BLUE}=========================================="
    echo -e "$1"
    echo -e "==========================================${NC}"
    echo ""
}

check_service_health() {
    local service=$1
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker compose ps "$service" 2>/dev/null | grep -q "healthy\|Up"; then
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    return 1
}

test_endpoint() {
    local url=$1
    local description=$2

    if curl -f -s "$url" >/dev/null 2>&1; then
        print_success "$description: $url"
        return 0
    else
        print_error "$description failed: $url"
        return 1
    fi
}

# Check if .env file exists
check_env_file() {
    if [ ! -f "${REPO_ROOT}/.env" ]; then
        print_info "Creating .env file..."
        if [ -f "${REPO_ROOT}/.env.example" ]; then
            cp "${REPO_ROOT}/.env.example" "${REPO_ROOT}/.env"
            print_success ".env file created from .env.example"
        else
            print_info ".env.example not found, using defaults"
        fi
    else
        print_success ".env file exists"
    fi
}

# Validate docker-compose.yml
validate_compose() {
    print_info "Validating docker-compose.yml syntax..."
    cd "${REPO_ROOT}"
    if docker compose config > /dev/null 2>&1; then
        print_success "docker-compose.yml is valid"
        return 0
    else
        print_error "docker-compose.yml has syntax errors"
        return 1
    fi
}

# Commands
cmd_validate() {
    print_section "Validating Docker Compose Configuration"
    check_env_file
    validate_compose
}

cmd_build() {
    local service="${1:-all}"

    print_section "Building Docker Images"
    cd "${REPO_ROOT}"
    check_env_file

    if [ "$service" = "all" ]; then
        print_info "Building all microservices..."
        docker compose build "${MICROSERVICES[@]}"
        print_success "All service images built successfully"
    else
        if [[ " ${MICROSERVICES[@]} " =~ " ${service} " ]]; then
            print_info "Building ${service}..."
            docker compose build "$service"
            print_success "${service} image built successfully"
        else
            print_error "Invalid service: ${service}"
            print_info "Available services: ${MICROSERVICES[*]}"
            exit 1
        fi
    fi
}

cmd_start() {
    local component="${1:-all}"

    cd "${REPO_ROOT}"
    check_env_file

    case "$component" in
        infra|infrastructure)
            print_section "Starting Infrastructure Services"
            print_info "Starting RabbitMQ, Redis..."
            docker compose up -d "${INFRASTRUCTURE_SERVICES[@]}"
            sleep 5
            for svc in "${INFRASTRUCTURE_SERVICES[@]}"; do
                if check_service_health "$svc"; then
                    print_success "$svc is healthy"
                else
                    print_error "$svc failed to start"
                fi
            done
            ;;

        db|databases)
            print_section "Starting Database Services"
            print_info "Starting all databases..."
            docker compose up -d "${DATABASE_SERVICES[@]}"
            sleep 10
            for svc in "${DATABASE_SERVICES[@]}"; do
                if check_service_health "$svc"; then
                    print_success "$svc is healthy"
                else
                    print_error "$svc failed to start"
                fi
            done
            ;;

        services)
            print_section "Starting Microservices"
            print_info "Starting all microservices..."
            docker compose up -d "${MICROSERVICES[@]}"
            sleep 15
            for svc in "${MICROSERVICES[@]}"; do
                if check_service_health "$svc"; then
                    print_success "$svc is healthy"
                else
                    print_error "$svc failed to start"
                    docker compose logs "$svc" | tail -20
                fi
            done
            ;;

        gateway|kong)
            print_section "Starting API Gateway (Kong)"
            docker compose up -d kong
            sleep 10

            if check_service_health kong; then
                print_success "Kong gateway is healthy"
            else
                print_error "Kong gateway failed to start"
            fi
            ;;

        monitoring|monitor)
            print_section "Starting Monitoring Services"
            print_info "Starting Prometheus and Grafana..."
            docker compose up -d "${MONITORING_SERVICES[@]}"
            sleep 10
            for svc in "${MONITORING_SERVICES[@]}"; do
                if check_service_health "$svc"; then
                    print_success "$svc is healthy"
                else
                    print_error "$svc failed to start"
                fi
            done
            ;;

        all)
            print_section "Starting All Services"

            # Start in order: infrastructure -> databases -> services -> gateway -> monitoring
            cmd_start infra
            cmd_start db
            cmd_start services
            cmd_start gateway
            cmd_start monitoring

            print_success "All services started"
            ;;

        *)
            # Start specific service
            if [[ " ${ALL_SERVICES[@]} " =~ " ${component} " ]]; then
                print_info "Starting ${component}..."
                docker compose up -d "$component"
                sleep 5
                if check_service_health "$component"; then
                    print_success "${component} is healthy"
                else
                    print_error "${component} failed to start"
                fi
            else
                print_error "Unknown component: ${component}"
                print_info "Available: infra, db, services, gateway, monitoring, all, or specific service name"
                exit 1
            fi
            ;;
    esac
}

cmd_stop() {
    local component="${1:-all}"

    cd "${REPO_ROOT}"

    print_section "Stopping Services"

    if [ "$component" = "all" ]; then
        print_info "Stopping all services..."
        docker compose stop
        print_success "All services stopped"
    else
        print_info "Stopping ${component}..."
        docker compose stop "$component"
        print_success "${component} stopped"
    fi
}

cmd_restart() {
    local component="${1:-all}"

    print_section "Restarting Services"
    cmd_stop "$component"
    sleep 2
    cmd_start "$component"
}

cmd_test() {
    local component="${1:-all}"

    cd "${REPO_ROOT}"

    print_section "Testing Service Endpoints"

    FAILED_TESTS=0

    case "$component" in
        services|all)
            sleep 5

            # Test microservices
            print_info "Testing microservices health endpoints..."
            test_endpoint "http://localhost:8001/health" "Patient Service" || ((FAILED_TESTS++))
            test_endpoint "http://localhost:8002/health" "Appointment Service" || ((FAILED_TESTS++))
            test_endpoint "http://localhost:8003/health" "Prescription Service" || ((FAILED_TESTS++))
            test_endpoint "http://localhost:8004/health" "Billing Service" || ((FAILED_TESTS++))

            if [ "$component" = "services" ]; then
                [ $FAILED_TESTS -eq 0 ] && print_success "All microservices healthy" || print_error "$FAILED_TESTS microservice(s) failed"
                return $FAILED_TESTS
            fi
            ;;&

        gateway|all)
            # Test Kong
            print_info "Testing Kong API Gateway..."
            if docker compose ps kong 2>/dev/null | grep -q "Up"; then
                test_endpoint "http://localhost:8000" "Kong Proxy" || ((FAILED_TESTS++))
                test_endpoint "http://localhost:8445" "Kong Admin API" || ((FAILED_TESTS++))
            else
                print_info "Kong not running, skipping"
            fi

            if [ "$component" = "gateway" ]; then
                [ $FAILED_TESTS -eq 0 ] && print_success "Kong gateway healthy" || print_error "Kong gateway failed"
                return $FAILED_TESTS
            fi
            ;;&

        monitoring|all)
            # Test monitoring services
            print_info "Testing monitoring services..."
            if docker compose ps prometheus 2>/dev/null | grep -q "Up"; then
                test_endpoint "http://localhost:9090/-/healthy" "Prometheus" || ((FAILED_TESTS++))
            else
                print_info "Prometheus not running, skipping"
            fi

            if docker compose ps grafana 2>/dev/null | grep -q "Up"; then
                test_endpoint "http://localhost:3000/api/health" "Grafana" || ((FAILED_TESTS++))
            else
                print_info "Grafana not running, skipping"
            fi

            if [ "$component" = "monitoring" ]; then
                [ $FAILED_TESTS -eq 0 ] && print_success "Monitoring services healthy" || print_error "Monitoring services failed"
                return $FAILED_TESTS
            fi
            ;;
    esac

    echo ""
    if [ $FAILED_TESTS -eq 0 ]; then
        print_success "All tests passed!"
    else
        print_error "$FAILED_TESTS test(s) failed"
    fi

    return $FAILED_TESTS
}

cmd_logs() {
    local service="${1:-}"

    cd "${REPO_ROOT}"

    if [ -z "$service" ]; then
        print_info "Showing logs for all services..."
        docker compose logs -f
    else
        print_info "Showing logs for ${service}..."
        docker compose logs -f "$service"
    fi
}

cmd_status() {
    cd "${REPO_ROOT}"

    print_section "Service Status"
    docker compose ps

    echo ""
    print_info "Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker compose ps -q 2>/dev/null) 2>/dev/null || echo "No running containers"
}

cmd_shell() {
    local service="${1:-billing-service}"

    cd "${REPO_ROOT}"

    print_info "Opening shell in ${service}..."
    docker compose exec "$service" /bin/sh || docker compose exec "$service" /bin/bash
}

cmd_down() {
    local remove_volumes="${1:-false}"

    cd "${REPO_ROOT}"

    print_section "Stopping and Removing Containers"

    if [ "$remove_volumes" = "volumes" ] || [ "$remove_volumes" = "-v" ]; then
        read -p "This will remove all volumes and data. Continue? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Stopping containers and removing volumes..."
            docker compose down -v
            print_success "Containers and volumes removed"
        else
            print_info "Cancelled"
            exit 0
        fi
    else
        print_info "Stopping containers..."
        docker compose down
        print_success "Containers removed"
    fi
}

cmd_clean() {
    cd "${REPO_ROOT}"

    print_section "Cleanup Healthcare System Resources"

    echo "This will clean up Docker resources for the healthcare system:"
    echo "  - Stop and remove all containers"
    echo "  - Remove all volumes (databases will be deleted)"
    echo "  - Remove all images built for this project"
    echo "  - Remove healthcare network"
    echo ""
    read -p "Are you sure? (y/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cleanup cancelled"
        exit 0
    fi

    # Stop and remove containers with volumes
    print_info "Stopping and removing containers..."
    docker compose down -v 2>/dev/null || true
    print_success "Containers and volumes removed"

    # Remove images
    print_info "Removing healthcare service images..."
    for service in "${MICROSERVICES[@]}"; do
        docker rmi "healthcare-patient-management-system-${service}" 2>/dev/null || true
        docker rmi "healthcare/${service}:latest" 2>/dev/null || true
    done
    print_success "Service images removed"

    # Remove network
    print_info "Removing healthcare network..."
    docker network rm healthcare-network 2>/dev/null || true
    print_success "Network removed"

    # Prune dangling images and volumes related to the project
    print_info "Pruning dangling resources..."
    docker image prune -f --filter "label=com.docker.compose.project=healthcare-patient-management-system" 2>/dev/null || true
    docker volume prune -f --filter "label=com.docker.compose.project=healthcare-patient-management-system" 2>/dev/null || true

    print_success "Cleanup complete!"
}

cmd_info() {
    print_section "Healthcare System Connection Information"

    echo "Microservices:"
    echo "  Patient Service:       http://localhost:8001 (docs: /docs)"
    echo "  Appointment Service:   http://localhost:8002 (docs: /docs)"
    echo "  Prescription Service:  http://localhost:8003 (docs: /docs)"
    echo "  Billing Service:       http://localhost:8004 (docs: /docs)"
    echo ""
    echo "Databases:"
    echo "  Patient DB (PostgreSQL):      localhost:5433 (user: postgres)"
    echo "  Appointment DB (PostgreSQL):  localhost:5434 (user: postgres)"
    echo "  Prescription DB (MongoDB):    localhost:27017 (user: admin)"
    echo "  Billing DB (PostgreSQL):      localhost:5432 (user: postgres)"
    echo ""
    echo "API Gateway:"
    echo "  Kong Proxy:            http://localhost:8000"
    echo "  Kong Admin API:        http://localhost:8445"
    echo ""
    echo "Infrastructure:"
    echo "  RabbitMQ Management:   http://localhost:15672 (admin/rabbitmq_secure_password)"
    echo "  Redis:                 localhost:6379"
    echo ""
    echo "Monitoring:"
    echo "  Prometheus:            http://localhost:9090"
    echo "  Grafana:               http://localhost:3000 (admin/admin)"
    echo ""
    echo "Database Access Examples:"
    echo "  docker compose exec patient-db psql -U postgres -d patient_db"
    echo "  docker compose exec appointment-db psql -U postgres -d appointment_db"
    echo "  docker compose exec prescription-db mongosh -u admin -p mongo_secure_password"
    echo "  docker compose exec billing-db psql -U postgres -d billing_db"
}

# Main command dispatcher
case "${1:-}" in
    validate)
        cmd_validate
        ;;

    build)
        cmd_build "${2:-all}"
        ;;

    start|up)
        cmd_start "${2:-all}"
        ;;

    stop)
        cmd_stop "${2:-all}"
        ;;

    restart)
        cmd_restart "${2:-all}"
        ;;

    test)
        cmd_test "${2:-all}"
        ;;

    logs)
        cmd_logs "${2:-}"
        ;;

    status|ps)
        cmd_status
        ;;

    shell|exec)
        cmd_shell "${2:-billing-service}"
        ;;

    down)
        cmd_down "${2:-}"
        ;;

    clean|cleanup)
        cmd_clean
        ;;

    info)
        cmd_info
        ;;

    *)
        echo "Usage: $0 {command} [options]"
        echo ""
        echo "Commands:"
        echo "  validate              - Validate docker-compose.yml and check .env file"
        echo "  build [service|all]   - Build service images (default: all)"
        echo "  start [component]     - Start services"
        echo "  stop [component]      - Stop services"
        echo "  restart [component]   - Restart services"
        echo "  test [component]      - Test service endpoints"
        echo "  logs [service]        - View service logs (default: all)"
        echo "  status                - Show service status and resource usage"
        echo "  shell [service]       - Open shell in service container"
        echo "  down [volumes]        - Stop and remove containers (add 'volumes' to remove data)"
        echo "  clean                 - Complete cleanup (containers, volumes, images, networks)"
        echo "  info                  - Show connection information"
        echo ""
        echo "Components for start/stop/restart:"
        echo "  all                   - All services (default)"
        echo "  infra                 - Infrastructure (RabbitMQ, Redis)"
        echo "  db                    - All databases"
        echo "  services              - All microservices"
        echo "  gateway               - Kong API Gateway"
        echo "  monitoring            - Prometheus and Grafana"
        echo "  <service-name>        - Specific service"
        echo ""
        echo "Test components:"
        echo "  all                   - Test all endpoints (default)"
        echo "  services              - Test microservices only"
        echo "  gateway               - Test Kong gateway only"
        echo "  monitoring            - Test monitoring services only"
        echo ""
        echo "Examples:"
        echo "  $0 validate                           # Check configuration"
        echo "  $0 build all                          # Build all service images"
        echo "  $0 start infra                        # Start infrastructure only"
        echo "  $0 start all                          # Start everything"
        echo "  $0 test services                      # Test microservices"
        echo "  $0 test all                           # Test everything"
        echo "  $0 logs patient-service               # View specific logs"
        echo "  $0 shell billing-service              # Shell into service"
        echo "  $0 restart appointment-service        # Restart specific service"
        echo "  $0 down volumes                       # Remove everything including data"
        echo "  $0 clean                              # Complete cleanup"
        echo ""
        echo "Typical Workflow:"
        echo "  1. $0 validate           # Validate configuration"
        echo "  2. $0 build all          # Build images"
        echo "  3. $0 start all          # Start all services"
        echo "  4. $0 test all           # Test endpoints"
        echo "  5. $0 status             # Check status"
        echo "  6. $0 logs               # View logs"
        echo ""
        echo "Cleanup:"
        echo "  $0 down                  # Stop services (keep data)"
        echo "  $0 down volumes          # Stop and remove data"
        echo "  $0 clean                 # Complete cleanup"
        exit 1
        ;;
esac
