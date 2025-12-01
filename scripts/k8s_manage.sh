#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
K8S_DIR="${REPO_ROOT}/kubernetes/billing-service"
INFRA_DIR="${REPO_ROOT}/kubernetes/infrastructure"
NAMESPACE="healthcare"

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
        echo "  Kong Admin:    kubectl port-forward -n kong svc/kong-admin 8001:8001"
        echo "  Kong Proxy:    minikube service -n kong kong-proxy"
        echo "  Prometheus:    minikube service -n monitoring prometheus"
        echo "  Grafana:       minikube service -n monitoring grafana (admin/admin)"
        ;;

    build)
        echo "Building Docker image for billing-service..."
        cd "${REPO_ROOT}"

        if minikube status >/dev/null 2>&1; then
            echo "Using Minikube Docker daemon..."
            eval $(minikube docker-env)
        fi

        docker build -t healthcare/billing-service:latest -f services/billing-service/Dockerfile .
        echo "Image built successfully!"
        ;;

    deploy)
        echo "Deploying billing-service to Kubernetes..."

        echo "Ensuring infrastructure is deployed..."
        kubectl get namespace kong >/dev/null 2>&1 || echo "WARNING: Kong namespace not found. Run './scripts/k8s_manage.sh infra' first"
        kubectl get namespace monitoring >/dev/null 2>&1 || echo "WARNING: Monitoring namespace not found. Run './scripts/k8s_manage.sh infra' first"

        kubectl apply -f "${K8S_DIR}/namespace.yaml"
        kubectl apply -f "${K8S_DIR}/configmap.yaml"
        kubectl apply -f "${K8S_DIR}/secret.yaml"
        kubectl apply -f "${K8S_DIR}/postgres-deployment.yaml"

        echo "Waiting for PostgreSQL to be ready..."
        kubectl wait --for=condition=ready pod -l app=billing-postgres -n ${NAMESPACE} --timeout=180s || true

        kubectl apply -f "${K8S_DIR}/deployment.yaml"
        kubectl apply -f "${K8S_DIR}/service.yaml"

        echo "Waiting for billing-service to be ready..."
        kubectl wait --for=condition=ready pod -l app=billing-service -n ${NAMESPACE} --timeout=180s || true

        echo ""
        echo "Deployment complete!"
        kubectl get pods -n ${NAMESPACE}
        ;;

    test)
        echo "Testing billing-service..."

        POD=$(kubectl get pod -n ${NAMESPACE} -l app=billing-service -o jsonpath='{.items[0].metadata.name}')
        if [ -z "$POD" ]; then
            echo "ERROR: No billing-service pods found"
            exit 1
        fi

        echo "Port-forwarding to localhost:8004..."
        kubectl port-forward -n ${NAMESPACE} svc/billing-service 8004:8004 >/dev/null 2>&1 &
        PF_PID=$!
        sleep 5

        echo "Testing health endpoint..."
        curl -f http://localhost:8004/health || { kill $PF_PID 2>/dev/null; exit 1; }

        echo ""
        echo "Testing root endpoint..."
        curl -f http://localhost:8004/ || { kill $PF_PID 2>/dev/null; exit 1; }

        kill $PF_PID 2>/dev/null
        echo ""
        echo "All tests passed!"
        ;;

    clean)
        echo "Cleaning up billing-service resources..."

        read -p "Delete all resources in namespace '${NAMESPACE}'? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cleanup cancelled"
            exit 0
        fi

        kubectl delete -f "${K8S_DIR}/service.yaml" --ignore-not-found=true
        kubectl delete -f "${K8S_DIR}/deployment.yaml" --ignore-not-found=true
        kubectl delete -f "${K8S_DIR}/postgres-deployment.yaml" --ignore-not-found=true
        kubectl delete -f "${K8S_DIR}/configmap.yaml" --ignore-not-found=true
        kubectl delete -f "${K8S_DIR}/secret.yaml" --ignore-not-found=true

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

        echo "Cleanup complete!"
        ;;

    logs)
        kubectl logs -f -n ${NAMESPACE} -l app=billing-service
        ;;

    shell)
        POD=$(kubectl get pod -n ${NAMESPACE} -l app=billing-service -o jsonpath='{.items[0].metadata.name}')
        kubectl exec -it -n ${NAMESPACE} ${POD} -- /bin/bash
        ;;

    *)
        echo "Usage: $0 {infra|build|deploy|test|clean|logs|shell}"
        echo ""
        echo "Commands:"
        echo "  infra   - Deploy infrastructure (Kong, Prometheus, Grafana)"
        echo "  build   - Build Docker image for billing-service"
        echo "  deploy  - Deploy billing-service to Kubernetes"
        echo "  test    - Test deployed service"
        echo "  clean   - Clean up all resources"
        echo "  logs    - View service logs"
        echo "  shell   - Open shell in billing-service pod"
        echo ""
        echo "Typical workflow:"
        echo "  1. ./scripts/k8s_manage.sh infra"
        echo "  2. ./scripts/k8s_manage.sh build"
        echo "  3. ./scripts/k8s_manage.sh deploy"
        echo "  4. ./scripts/k8s_manage.sh test"
        exit 1
        ;;
esac
