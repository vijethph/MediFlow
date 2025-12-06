#!/bin/bash
set -e

echo "=========================================="
echo "Healthcare System - Kubernetes Test Suite"
echo "=========================================="
echo ""

NAMESPACE_HEALTHCARE="healthcare"
NAMESPACE_KONG="kong"
NAMESPACE_MONITORING="monitoring"

# Service list
SERVICES=("patient-service" "appointment-service" "prescription-service" "billing-service")

check_namespace() {
    local ns=$1
    if kubectl get namespace "$ns" >/dev/null 2>&1; then
        echo "✅ Namespace $ns exists"
        return 0
    else
        echo "❌ Namespace $ns not found"
        return 1
    fi
}

check_pods() {
    local ns=$1
    local label=$2
    local expected=$3

    local count=$(kubectl get pods -n "$ns" -l "$label" --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
    if [ "$count" -ge "$expected" ]; then
        echo "✅ $ns: Found $count running pods with label $label"
        return 0
    else
        echo "❌ $ns: Expected at least $expected running pods, found $count"
        return 1
    fi
}

check_service() {
    local ns=$1
    local svc=$2

    if kubectl get service -n "$ns" "$svc" >/dev/null 2>&1; then
        echo "✅ Service $ns/$svc exists"
        return 0
    else
        echo "❌ Service $ns/$svc not found"
        return 1
    fi
}

test_endpoint() {
    local url=$1
    local description=$2

    if curl -f -s "$url" >/dev/null 2>&1; then
        echo "✅ $description: $url"
        return 0
    else
        echo "❌ $description failed: $url"
        return 1
    fi
}

echo "Step 1: Checking Namespaces"
echo "----------------------------"
check_namespace "$NAMESPACE_HEALTHCARE" || exit 1
check_namespace "$NAMESPACE_KONG" || exit 1
check_namespace "$NAMESPACE_MONITORING" || exit 1
echo ""

echo "Step 2: Checking Infrastructure Pods"
echo "-------------------------------------"
check_pods "$NAMESPACE_KONG" "app=kong" 1 || exit 1
check_pods "$NAMESPACE_MONITORING" "app=prometheus" 1 || exit 1
check_pods "$NAMESPACE_MONITORING" "app=grafana" 1 || exit 1
echo ""

echo "Step 3: Checking Service Pods"
echo "------------------------------"

# Check if any services are deployed
DEPLOYED_SERVICES=()
for svc in "${SERVICES[@]}"; do
    if kubectl get deployment -n "$NAMESPACE_HEALTHCARE" "$svc" >/dev/null 2>&1; then
        DEPLOYED_SERVICES+=("$svc")
        check_pods "$NAMESPACE_HEALTHCARE" "app=$svc" 1 || echo "Warning: $svc pods not ready"
    else
        echo "⚠️  $svc not deployed (skipping)"
    fi
done

# Check databases for deployed services
if [[ " ${DEPLOYED_SERVICES[@]} " =~ " billing-service " ]]; then
    check_pods "$NAMESPACE_HEALTHCARE" "app=billing-postgres" 1 || echo "Warning: billing-postgres not ready"
fi

if [[ " ${DEPLOYED_SERVICES[@]} " =~ " prescription-service " ]]; then
    check_pods "$NAMESPACE_HEALTHCARE" "app=prescription-mongo" 1 || echo "Warning: prescription-mongo not ready"
fi

echo ""

echo "Step 4: Checking Services"
echo "-------------------------"
check_service "$NAMESPACE_KONG" "kong-proxy" || exit 1
check_service "$NAMESPACE_KONG" "kong-admin" || exit 1
check_service "$NAMESPACE_MONITORING" "prometheus" || exit 1
check_service "$NAMESPACE_MONITORING" "grafana" || exit 1

# Check services for deployed microservices
for svc in "${DEPLOYED_SERVICES[@]}"; do
    check_service "$NAMESPACE_HEALTHCARE" "$svc" || echo "Warning: $svc service not found"
done

# Check database services
if [[ " ${DEPLOYED_SERVICES[@]} " =~ " billing-service " ]]; then
    check_service "$NAMESPACE_HEALTHCARE" "billing-postgres" || echo "Warning: billing-postgres service not found"
fi

if [[ " ${DEPLOYED_SERVICES[@]} " =~ " prescription-service " ]]; then
    check_service "$NAMESPACE_HEALTHCARE" "prescription-mongo" || echo "Warning: prescription-mongo service not found"
fi

echo ""

echo "Step 5: Testing Endpoints (requires port-forward)"
echo "--------------------------------------------------"

if [ ${#DEPLOYED_SERVICES[@]} -eq 0 ]; then
    echo "No services deployed to test"
    exit 0
fi

echo "Starting port-forwards for deployed services..."

# Port forward deployed services
PF_PIDS=()

for svc in "${DEPLOYED_SERVICES[@]}"; do
    case $svc in
        patient-service)
            kubectl port-forward -n "$NAMESPACE_HEALTHCARE" svc/patient-service 8001:8001 >/dev/null 2>&1 &
            PF_PIDS+=($!)
            ;;
        appointment-service)
            kubectl port-forward -n "$NAMESPACE_HEALTHCARE" svc/appointment-service 8002:8002 >/dev/null 2>&1 &
            PF_PIDS+=($!)
            ;;
        prescription-service)
            kubectl port-forward -n "$NAMESPACE_HEALTHCARE" svc/prescription-service 8003:8003 >/dev/null 2>&1 &
            PF_PIDS+=($!)
            ;;
        billing-service)
            kubectl port-forward -n "$NAMESPACE_HEALTHCARE" svc/billing-service 8004:8004 >/dev/null 2>&1 &
            PF_PIDS+=($!)
            ;;
    esac
done

sleep 5

echo "Testing service health endpoints..."

FAILED_TESTS=0

for svc in "${DEPLOYED_SERVICES[@]}"; do
    case $svc in
        patient-service)
            test_endpoint "http://localhost:8001/health" "Patient Service Health" || ((FAILED_TESTS++))
            ;;
        appointment-service)
            test_endpoint "http://localhost:8002/health" "Appointment Service Health" || ((FAILED_TESTS++))
            ;;
        prescription-service)
            test_endpoint "http://localhost:8003/health" "Prescription Service Health" || ((FAILED_TESTS++))
            ;;
        billing-service)
            test_endpoint "http://localhost:8004/health" "Billing Service Health" || ((FAILED_TESTS++))
            ;;
    esac
done

echo ""
echo "Cleaning up port-forwards..."
for pid in "${PF_PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
done

echo ""
echo "Step 6: Resource Utilization"
echo "----------------------------"
echo "Healthcare namespace:"
kubectl top pods -n "$NAMESPACE_HEALTHCARE" 2>/dev/null || echo "⚠️  Metrics server not available"
echo ""

echo "=========================================="
if [ $FAILED_TESTS -eq 0 ]; then
    echo "✅ All Tests Passed!"
else
    echo "⚠️  $FAILED_TESTS Test(s) Failed"
fi
echo "=========================================="
echo ""
echo "Summary:"
echo "  Deployed services: ${#DEPLOYED_SERVICES[@]}"
echo "  Services: ${DEPLOYED_SERVICES[*]}"
echo ""
echo "Access services:"
echo "  Kong Proxy:      minikube service -n kong kong-proxy"
echo "  Prometheus:      minikube service -n monitoring prometheus"
echo "  Grafana:         minikube service -n monitoring grafana (admin/admin)"
echo ""
echo "Useful commands:"
echo "  View logs:    ./scripts/k8s_manage.sh logs <service-name>"
echo "  Open shell:   ./scripts/k8s_manage.sh shell <service-name>"
echo "  View pods:    kubectl get pods -n $NAMESPACE_HEALTHCARE"

exit $FAILED_TESTS
