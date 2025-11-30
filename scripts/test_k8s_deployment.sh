#!/bin/bash
set -e

echo "=========================================="
echo "Healthcare System - Kubernetes Test Suite"
echo "=========================================="
echo ""

NAMESPACE_HEALTHCARE="healthcare"
NAMESPACE_KONG="kong"
NAMESPACE_MONITORING="monitoring"

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
check_pods "$NAMESPACE_HEALTHCARE" "app=billing-postgres" 1 || exit 1
check_pods "$NAMESPACE_HEALTHCARE" "app=billing-service" 2 || exit 1
echo ""

echo "Step 4: Checking Services"
echo "-------------------------"
check_service "$NAMESPACE_KONG" "kong-proxy" || exit 1
check_service "$NAMESPACE_KONG" "kong-admin" || exit 1
check_service "$NAMESPACE_MONITORING" "prometheus" || exit 1
check_service "$NAMESPACE_MONITORING" "grafana" || exit 1
check_service "$NAMESPACE_HEALTHCARE" "billing-service" || exit 1
check_service "$NAMESPACE_HEALTHCARE" "billing-postgres" || exit 1
echo ""

echo "Step 5: Testing Endpoints (requires port-forward)"
echo "--------------------------------------------------"

echo "Starting port-forwards..."
kubectl port-forward -n "$NAMESPACE_HEALTHCARE" svc/billing-service 8004:8004 >/dev/null 2>&1 &
PF_BILLING=$!
kubectl port-forward -n "$NAMESPACE_KONG" svc/kong-admin 8001:8001 >/dev/null 2>&1 &
PF_KONG=$!

sleep 3

test_endpoint "http://localhost:8004/health" "Billing Service Health" || BILLING_FAILED=1
test_endpoint "http://localhost:8004/metrics" "Billing Service Metrics" || METRICS_FAILED=1
test_endpoint "http://localhost:8001/status" "Kong Admin API" || KONG_FAILED=1

kill $PF_BILLING $PF_KONG 2>/dev/null
echo ""

echo "Step 6: Resource Utilization"
echo "----------------------------"
echo "Healthcare namespace:"
kubectl top pods -n "$NAMESPACE_HEALTHCARE" 2>/dev/null || echo "⚠️  Metrics server not available"
echo ""
echo "Infrastructure:"
kubectl top pods -n "$NAMESPACE_KONG" 2>/dev/null || true
kubectl top pods -n "$NAMESPACE_MONITORING" 2>/dev/null || true
echo ""

echo "=========================================="
echo "Test Summary"
echo "=========================================="

if [ -z "$BILLING_FAILED" ] && [ -z "$METRICS_FAILED" ] && [ -z "$KONG_FAILED" ]; then
    echo "✅ All tests passed!"
    echo ""
    echo "Access services:"
    echo "  Billing Service: kubectl port-forward -n healthcare svc/billing-service 8004:8004"
    echo "  Kong Proxy:      minikube service -n kong kong-proxy"
    echo "  Prometheus:      minikube service -n monitoring prometheus"
    echo "  Grafana:         minikube service -n monitoring grafana (admin/admin)"
    exit 0
else
    echo "❌ Some tests failed"
    echo ""
    echo "Troubleshooting:"
    echo "  View pods:    kubectl get pods -A"
    echo "  View logs:    kubectl logs -n <namespace> <pod-name>"
    echo "  Describe pod: kubectl describe pod -n <namespace> <pod-name>"
    exit 1
fi
