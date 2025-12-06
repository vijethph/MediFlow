#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
K8S_DIR="${REPO_ROOT}/kubernetes"
INFRA_DIR="${REPO_ROOT}/kubernetes/infrastructure"
NAMESPACE="healthcare"

# Service list
SERVICES=("patient-service" "appointment-service" "prescription-service" "billing-service")

case "${1:-}" in
    infra)
        echo "Deploying infrastructure (Kong, Prometheus, Grafana)..."

        kubectl apply -f "${INFRA_DIR}/kong.yaml"
        kubectl apply -f "${INFRA_DIR}/prometheus.yaml"
        kubectl apply -f "${INFRA_DIR}/grafana.yaml"

        echo "Waiting for infrastructure to be ready..."
        kubectl wait --for=condition=ready pod -l app=kong -n kong --timeout=180s || true
        kubectl wait --for=condition=ready pod -l app=prometheus -n monitoring --timeout=180s || true
        kubectl wait --for=condition=ready pod -l app=grafana -n monitoring --timeout=180s || true

        echo ""
        echo "Infrastructure deployed!"
        echo ""
        echo "Access UIs:"
        echo "  Kong Admin:    kubectl port-forward -n kong svc/kong-admin 8445:8001"
        echo "  Kong Proxy:    minikube service -n kong kong-proxy"
        echo "  Prometheus:    minikube service -n monitoring prometheus"
        echo "  Grafana:       minikube service -n monitoring grafana (admin/admin)"
        ;;

    build)
        SERVICE="${2:-all}"

        echo "Building Docker images..."
        cd "${REPO_ROOT}"

        if minikube status >/dev/null 2>&1; then
            echo "Using Minikube Docker daemon..."
            eval $(minikube docker-env)
        fi

        if [ "$SERVICE" = "all" ]; then
            echo "Building all services..."
            docker build -t healthcare/patient-service:latest -f services/patient-service/Dockerfile .
            docker build -t healthcare/appointment-service:latest -f services/appointment-service/Dockerfile .
            docker build -t healthcare/prescription-service:latest -f services/prescription-service/Dockerfile .
            docker build -t healthcare/billing-service:latest -f services/billing-service/Dockerfile .
            echo "All images built successfully!"
        else
            echo "Building ${SERVICE}..."
            docker build -t healthcare/${SERVICE}:latest -f services/${SERVICE}/Dockerfile .
            echo "Image built successfully!"
        fi
        ;;

    deploy)
        SERVICE="${2:-all}"

        echo "Deploying services to Kubernetes..."

        echo "Ensuring infrastructure is deployed..."
        kubectl get namespace kong >/dev/null 2>&1 || echo "WARNING: Kong namespace not found. Run './scripts/k8s_manage.sh infra' first"
        kubectl get namespace monitoring >/dev/null 2>&1 || echo "WARNING: Monitoring namespace not found. Run './scripts/k8s_manage.sh infra' first"

        # Create namespace
        kubectl apply -f "${K8S_DIR}/namespace.yaml"

        if [ "$SERVICE" = "all" ]; then
            echo "Deploying all services..."

            # Deploy patient service
            echo ""
            echo "=== Deploying Patient Service ==="
            if [ -d "${K8S_DIR}/patient-service" ]; then
                kubectl apply -f "${K8S_DIR}/patient-service/configmap.yaml"
                kubectl apply -f "${K8S_DIR}/patient-service/secret.yaml"
                kubectl apply -f "${K8S_DIR}/patient-service/postgres-deployment.yaml"
                echo "Waiting for PostgreSQL to be ready..."
                kubectl wait --for=condition=ready pod -l app=patient-postgres -n ${NAMESPACE} --timeout=180s || true
                kubectl apply -f "${K8S_DIR}/patient-service/deployment.yaml"
                kubectl apply -f "${K8S_DIR}/patient-service/service.yaml"
                echo "Waiting for patient-service to be ready..."
                kubectl wait --for=condition=ready pod -l app=patient-service -n ${NAMESPACE} --timeout=180s || true
            else
                echo "WARNING: Patient service kubernetes manifests not found"
            fi

            # Deploy appointment service
            echo ""
            echo "=== Deploying Appointment Service ==="
            if [ -d "${K8S_DIR}/appointment-service" ]; then
                kubectl apply -f "${K8S_DIR}/appointment-service/configmap.yaml"
                kubectl apply -f "${K8S_DIR}/appointment-service/secret.yaml"
                kubectl apply -f "${K8S_DIR}/appointment-service/postgres-deployment.yaml"
                echo "Waiting for PostgreSQL to be ready..."
                kubectl wait --for=condition=ready pod -l app=appointment-postgres -n ${NAMESPACE} --timeout=180s || true
                kubectl apply -f "${K8S_DIR}/appointment-service/deployment.yaml"
                kubectl apply -f "${K8S_DIR}/appointment-service/service.yaml"
                echo "Waiting for appointment-service to be ready..."
                kubectl wait --for=condition=ready pod -l app=appointment-service -n ${NAMESPACE} --timeout=180s || true
            else
                echo "WARNING: Appointment service kubernetes manifests not found"
            fi

            # Deploy prescription service
            echo ""
            echo "=== Deploying Prescription Service ==="
            if [ -d "${K8S_DIR}/prescription-service" ]; then
                kubectl apply -f "${K8S_DIR}/prescription-service/configmap.yaml"
                kubectl apply -f "${K8S_DIR}/prescription-service/secret.yaml"
                kubectl apply -f "${K8S_DIR}/prescription-service/mongo-deployment.yaml"
                echo "Waiting for MongoDB to be ready..."
                kubectl wait --for=condition=ready pod -l app=prescription-mongo -n ${NAMESPACE} --timeout=180s || true
                kubectl apply -f "${K8S_DIR}/prescription-service/deployment.yaml"
                kubectl apply -f "${K8S_DIR}/prescription-service/service.yaml"
                echo "Waiting for prescription-service to be ready..."
                kubectl wait --for=condition=ready pod -l app=prescription-service -n ${NAMESPACE} --timeout=180s || true
            else
                echo "WARNING: Prescription service kubernetes manifests not found"
            fi

            # Deploy billing service
            echo ""
            echo "=== Deploying Billing Service ==="
            kubectl apply -f "${K8S_DIR}/billing-service/configmap.yaml"
            kubectl apply -f "${K8S_DIR}/billing-service/secret.yaml"
            kubectl apply -f "${K8S_DIR}/billing-service/postgres-deployment.yaml"
            echo "Waiting for PostgreSQL to be ready..."
            kubectl wait --for=condition=ready pod -l app=billing-postgres -n ${NAMESPACE} --timeout=180s || true
            kubectl apply -f "${K8S_DIR}/billing-service/deployment.yaml"
            kubectl apply -f "${K8S_DIR}/billing-service/service.yaml"
            echo "Waiting for billing-service to be ready..."
            kubectl wait --for=condition=ready pod -l app=billing-service -n ${NAMESPACE} --timeout=180s || true

        else
            echo "Deploying ${SERVICE}..."
            SERVICE_DIR="${K8S_DIR}/${SERVICE}"

            if [ ! -d "$SERVICE_DIR" ]; then
                echo "ERROR: Service directory not found: $SERVICE_DIR"
                exit 1
            fi

            # Apply all manifests in the service directory
            kubectl apply -f "${SERVICE_DIR}/"

            echo "Waiting for ${SERVICE} to be ready..."
            kubectl wait --for=condition=ready pod -l app=${SERVICE} -n ${NAMESPACE} --timeout=180s || true
        fi

        echo ""
        echo "Deployment complete!"
        kubectl get pods -n ${NAMESPACE}
        ;;

    test)
        SERVICE="${2:-all}"

        echo "Testing services..."

        if [ "$SERVICE" = "all" ]; then
            # Test all services
            for svc in "${SERVICES[@]}"; do
                echo ""
                echo "=== Testing ${svc} ==="

                POD=$(kubectl get pod -n ${NAMESPACE} -l app=${svc} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
                if [ -z "$POD" ]; then
                    echo "WARNING: No ${svc} pods found"
                    continue
                fi

                # Get service port
                case $svc in
                    patient-service) PORT=8001 ;;
                    appointment-service) PORT=8002 ;;
                    prescription-service) PORT=8003 ;;
                    billing-service) PORT=8004 ;;
                esac

                echo "Port-forwarding to localhost:${PORT}..."
                kubectl port-forward -n ${NAMESPACE} svc/${svc} ${PORT}:${PORT} >/dev/null 2>&1 &
                PF_PID=$!
                sleep 3

                echo "Testing health endpoint..."
                if curl -f http://localhost:${PORT}/health 2>/dev/null; then
                    echo "✓ ${svc} is healthy"
                else
                    echo "✗ ${svc} health check failed"
                fi

                kill $PF_PID 2>/dev/null || true
            done

        else
            # Test specific service
            POD=$(kubectl get pod -n ${NAMESPACE} -l app=${SERVICE} -o jsonpath='{.items[0].metadata.name}')
            if [ -z "$POD" ]; then
                echo "ERROR: No ${SERVICE} pods found"
                exit 1
            fi

            # Get service port
            case $SERVICE in
                patient-service) PORT=8001 ;;
                appointment-service) PORT=8002 ;;
                prescription-service) PORT=8003 ;;
                billing-service) PORT=8004 ;;
                *) echo "Unknown service"; exit 1 ;;
            esac

            echo "Port-forwarding to localhost:${PORT}..."
            kubectl port-forward -n ${NAMESPACE} svc/${SERVICE} ${PORT}:${PORT} >/dev/null 2>&1 &
            PF_PID=$!
            sleep 5

            echo "Testing health endpoint..."
            curl -f http://localhost:${PORT}/health || { kill $PF_PID 2>/dev/null; exit 1; }

            echo ""
            echo "Testing root endpoint..."
            curl -f http://localhost:${PORT}/ || { kill $PF_PID 2>/dev/null; exit 1; }

            kill $PF_PID 2>/dev/null
        fi

        echo ""
        echo "All tests completed!"
        ;;

    clean)
        SERVICE="${2:-all}"

        echo "Cleaning up resources..."

        if [ "$SERVICE" = "all" ]; then
            read -p "Delete all services in namespace '${NAMESPACE}'? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Cleanup cancelled"
                exit 0
            fi

            # Delete all services
            for svc in "${SERVICES[@]}"; do
                echo "Deleting ${svc}..."
                kubectl delete -f "${K8S_DIR}/${svc}/" --ignore-not-found=true 2>/dev/null || true
            done

            read -p "Delete namespace '${NAMESPACE}'? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                kubectl delete namespace ${NAMESPACE} --ignore-not-found=true
            fi

            read -p "Delete infrastructure (Kong, Prometheus, Grafana)? (y/N) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                kubectl delete -f "${INFRA_DIR}/grafana.yaml" --ignore-not-found=true
                kubectl delete -f "${INFRA_DIR}/prometheus.yaml" --ignore-not-found=true
                kubectl delete -f "${INFRA_DIR}/kong.yaml" --ignore-not-found=true
            fi
        else
            read -p "Delete ${SERVICE}? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Cleanup cancelled"
                exit 0
            fi

            kubectl delete -f "${K8S_DIR}/${SERVICE}/" --ignore-not-found=true
        fi

        echo "Cleanup complete!"
        ;;

    logs)
        SERVICE="${2:-billing-service}"
        echo "Viewing logs for ${SERVICE}..."
        kubectl logs -f -n ${NAMESPACE} -l app=${SERVICE}
        ;;

    shell)
        SERVICE="${2:-billing-service}"
        POD=$(kubectl get pod -n ${NAMESPACE} -l app=${SERVICE} -o jsonpath='{.items[0].metadata.name}')
        if [ -z "$POD" ]; then
            echo "ERROR: No ${SERVICE} pods found"
            exit 1
        fi
        echo "Opening shell in ${SERVICE} pod..."
        kubectl exec -it -n ${NAMESPACE} ${POD} -- /bin/sh
        ;;

    *)
        echo "Usage: $0 {infra|build|deploy|test|clean|logs|shell} [service-name|all]"
        echo ""
        echo "Commands:"
        echo "  infra          - Deploy infrastructure (Kong, Prometheus, Grafana)"
        echo "  build [svc]    - Build Docker image(s) (all or specific service)"
        echo "  deploy [svc]   - Deploy service(s) to Kubernetes (all or specific)"
        echo "  test [svc]     - Test deployed service(s) (all or specific)"
        echo "  clean [svc]    - Clean up resources (all or specific service)"
        echo "  logs [svc]     - View service logs (default: billing-service)"
        echo "  shell [svc]    - Open shell in service pod (default: billing-service)"
        echo ""
        echo "Services:"
        echo "  - patient-service"
        echo "  - appointment-service"
        echo "  - prescription-service"
        echo "  - billing-service"
        echo ""
        echo "Examples:"
        echo "  ./scripts/k8s_manage.sh build all                    # Build all services"
        echo "  ./scripts/k8s_manage.sh build patient-service        # Build specific service"
        echo "  ./scripts/k8s_manage.sh deploy all                   # Deploy all services"
        echo "  ./scripts/k8s_manage.sh test patient-service         # Test specific service"
        echo "  ./scripts/k8s_manage.sh logs appointment-service     # View logs"
        echo ""
        echo "Typical workflow:"
        echo "  1. ./scripts/k8s_manage.sh infra"
        echo "  2. ./scripts/k8s_manage.sh build all"
        echo "  3. ./scripts/k8s_manage.sh deploy all"
        echo "  4. ./scripts/k8s_manage.sh test all"
        exit 1
        ;;
esac
