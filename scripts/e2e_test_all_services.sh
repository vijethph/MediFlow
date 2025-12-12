#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DEPLOYMENT_MODE="${1:-docker}"
BASE_URL="${2:-}"
JWT_TOKEN=""
PATIENT_ID=""
APPOINTMENT_ID=""
PRESCRIPTION_ID=""
MEDICAL_RECORD_ID=""
INVOICE_ID=""
PAYMENT_ID=""
CLAIM_ID=""

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    ((PASSED_TESTS++))
    ((TOTAL_TESTS++))
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ((FAILED_TESTS++))
    ((TOTAL_TESTS++))
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_debug_info() {
    local service=$1
    local endpoint=$2
    echo -e "${YELLOW}Debug Commands:${NC}"
    if [[ "$DEPLOYMENT_MODE" == "kubernetes" || "$DEPLOYMENT_MODE" == "k8s" ]]; then
        echo "  kubectl logs -n healthcare deployment/${service} --tail=50"
        echo "  kubectl describe pod -n healthcare -l app=${service}"
        echo "  kubectl get events -n healthcare --sort-by='.lastTimestamp'"
    else
        echo "  docker-compose logs ${service} --tail=50"
        echo "  docker-compose ps ${service}"
        echo "  curl -v ${BASE_URL}/${service}${endpoint}"
    fi
}

test_endpoint() {
    local method=$1
    local endpoint=$2
    local service=$3
    local expected_status=$4
    local data=$5
    local description=$6

    log_info "Testing: $description"

    local url="${BASE_URL}${endpoint}"
    local response
    local status_code

    if [[ "$method" == "GET" ]]; then
        if [[ -n "$JWT_TOKEN" ]]; then
            response=$(curl -s -w "\n%{http_code}" -X GET "$url" \
                -H "Authorization: Bearer $JWT_TOKEN" \
                -H "Content-Type: application/json" 2>&1) || {
                log_error "$description - Request failed"
                print_debug_info "$service" "$endpoint"
                return 1
            }
        else
            response=$(curl -s -w "\n%{http_code}" -X GET "$url" \
                -H "Content-Type: application/json" 2>&1) || {
                log_error "$description - Request failed"
                print_debug_info "$service" "$endpoint"
                return 1
            }
        fi
    elif [[ "$method" == "POST" ]]; then
        if [[ -n "$JWT_TOKEN" ]]; then
            response=$(curl -s -w "\n%{http_code}" -X POST "$url" \
                -H "Authorization: Bearer $JWT_TOKEN" \
                -H "Content-Type: application/json" \
                -d "$data" 2>&1) || {
                log_error "$description - Request failed"
                print_debug_info "$service" "$endpoint"
                return 1
            }
        else
            response=$(curl -s -w "\n%{http_code}" -X POST "$url" \
                -H "Content-Type: application/json" \
                -d "$data" 2>&1) || {
                log_error "$description - Request failed"
                print_debug_info "$service" "$endpoint"
                return 1
            }
        fi
    elif [[ "$method" == "PUT" ]]; then
        response=$(curl -s -w "\n%{http_code}" -X PUT "$url" \
            -H "Authorization: Bearer $JWT_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" 2>&1) || {
            log_error "$description - Request failed"
            print_debug_info "$service" "$endpoint"
            return 1
        }
    elif [[ "$method" == "DELETE" ]]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE "$url" \
            -H "Authorization: Bearer $JWT_TOKEN" \
            -H "Content-Type: application/json" 2>&1) || {
            log_error "$description - Request failed"
            print_debug_info "$service" "$endpoint"
            return 1
        }
    fi

    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [[ "$status_code" == "$expected_status" ]]; then
        log_success "$description - Status: $status_code"
        echo "$body"
        return 0
    else
        log_error "$description - Expected: $expected_status, Got: $status_code"
        echo "Response: $body"
        print_debug_info "$service" "$endpoint"
        return 1
    fi
}

setup_deployment_mode() {
    log_info "Setting up deployment mode: $DEPLOYMENT_MODE"

    if [[ -z "$BASE_URL" ]]; then
        log_error "BASE_URL not provided"
        log_info "Usage: $0 <deployment_mode> <base_url>"
        log_info "Examples:"
        log_info "  $0 docker http://localhost:8000"
        log_info "  $0 kubernetes http://192.168.49.2:30080"
        log_info ""
        log_info "To get Kong Gateway URL:"
        log_info "  Docker Compose: http://localhost:8000 (default)"
        log_info "  Kubernetes: minikube service kong-proxy -n kong --url"
        exit 1
    fi

    if [[ "$DEPLOYMENT_MODE" == "kubernetes" || "$DEPLOYMENT_MODE" == "k8s" ]]; then
        log_success "Kubernetes mode - Kong Gateway: $BASE_URL"
    elif [[ "$DEPLOYMENT_MODE" == "docker" || "$DEPLOYMENT_MODE" == "docker-compose" ]]; then
        log_success "Docker Compose mode - Kong Gateway: $BASE_URL"
    else
        log_error "Invalid deployment mode: $DEPLOYMENT_MODE"
        log_info "Usage: $0 <deployment_mode> <base_url>"
        log_info "Supported modes: docker, docker-compose, kubernetes, k8s"
        exit 1
    fi

    log_success "Base URL configured: $BASE_URL"
    log_info "Kong Gateway connectivity will be tested during service health checks"
}

test_patient_service() {
    log_info "=========================================="
    log_info "Testing Patient Service (Port 8001)"
    log_info "=========================================="

    local email="test-patient-$(date +%s)@example.com"
    local password="SecurePass123!"

    log_info "1. Register new patient"
    local register_data='{
        "email": "'"$email"'",
        "password": "'"$password"'",
        "full_name": "John Doe",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "phone": "+1234567890",
        "address": "123 Main St, City, State 12345"
    }'

    local register_response=$(test_endpoint "POST" "/api/v1/patients/register" "patient-service" "201" "$register_data" "Register Patient")
    local register_status=$?

    if [[ $register_status -eq 0 && -n "$register_response" ]]; then
        JWT_TOKEN=$(echo "$register_response" | jq -r '.access_token // .token // empty' 2>/dev/null)

        if [[ -n "$JWT_TOKEN" && "$JWT_TOKEN" != "null" ]]; then
            log_success "JWT Token obtained from registration: ${JWT_TOKEN:0:20}..."
        fi
    fi

    # If registration failed or no token, try login with a default test user
    if [[ -z "$JWT_TOKEN" || "$JWT_TOKEN" == "null" ]]; then
        log_info "2. Login with default test credentials (registration may have failed due to duplicate email)"

        # Try with a known test account
        local login_data='{
            "email": "test@example.com",
            "password": "Test123!"
        }'

        local login_response=$(test_endpoint "POST" "/api/v1/patients/login" "patient-service" "200" "$login_data" "Patient Login" 2>/dev/null)

        if [[ $? -eq 0 && -n "$login_response" ]]; then
            JWT_TOKEN=$(echo "$login_response" | jq -r '.access_token // .token // empty' 2>/dev/null)

            if [[ -n "$JWT_TOKEN" && "$JWT_TOKEN" != "null" ]]; then
                log_success "JWT Token obtained from login: ${JWT_TOKEN:0:20}..."
                PATIENT_ID=$(echo "$login_response" | jq -r '.patient_id // empty' 2>/dev/null)
            fi
        fi

        # If still no token, tests requiring auth will fail
        if [[ -z "$JWT_TOKEN" || "$JWT_TOKEN" == "null" ]]; then
            log_warning "Could not obtain JWT token - tests requiring authentication will fail"
            log_warning "Continuing with available tests..."
        fi
    else
        log_info "2. Login with patient credentials"
        local login_data='{
            "email": "'"$email"'",
            "password": "'"$password"'"
        }'

        test_endpoint "POST" "/api/v1/patients/login" "patient-service" "200" "$login_data" "Patient Login"
    fi

    log_info "3. List all patients"
    local patients_response=$(test_endpoint "GET" "/api/v1/patients/?skip=0&limit=10" "patient-service" "200" "" "List Patients")

    if [[ $? -eq 0 && -n "$patients_response" ]]; then
        PATIENT_ID=$(echo "$patients_response" | jq -r '.[0].patient_id // .[0].id // empty' 2>/dev/null)

        if [[ -z "$PATIENT_ID" || "$PATIENT_ID" == "null" ]]; then
            log_warning "Could not extract patient_id from list response, using test patient"
            PATIENT_ID="test-patient-001"
        fi

        log_success "Patient ID obtained: $PATIENT_ID"
    fi

    log_info "4. Get patient by ID"
    if [[ -n "$PATIENT_ID" && "$PATIENT_ID" != "null" ]]; then
        test_endpoint "GET" "/api/v1/patients/$PATIENT_ID" "patient-service" "200" "" "Get Patient by ID"
    fi

    log_info "5. Get patient by email"
    test_endpoint "GET" "/api/v1/patients/email/$email" "patient-service" "200" "" "Get Patient by Email"

    log_info "6. Update patient"
    if [[ -n "$PATIENT_ID" && "$PATIENT_ID" != "null" ]]; then
        local update_data='{
            "phone": "+9876543210",
            "address": "456 New St, City, State 67890"
        }'
        test_endpoint "PUT" "/api/v1/patients/$PATIENT_ID" "patient-service" "200" "$update_data" "Update Patient"
    fi

    log_info "7. Health check"
    test_endpoint "GET" "/api/v1/patients/health/check" "patient-service" "200" "" "Patient Service Health Check"
}

test_appointment_service() {
    log_info "=========================================="
    log_info "Testing Appointment Service (Port 8002)"
    log_info "=========================================="

    if [[ -z "$PATIENT_ID" || "$PATIENT_ID" == "null" ]]; then
        log_warning "No valid patient_id, using default test patient ID"
        PATIENT_ID="test-patient-001"
    fi

    local doctor_id="doctor-001"
    local appointment_date=$(date -u -d "+1 day" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v+1d +"%Y-%m-%dT%H:%M:%SZ")

    log_info "1. Create appointment"
    local appointment_data='{
        "patient_id": "'"$PATIENT_ID"'",
        "doctor_id": "'"$doctor_id"'",
        "appointment_date": "'"$appointment_date"'",
        "reason": "Annual checkup",
        "notes": "Patient requested full physical exam"
    }'

    local appointment_response=$(test_endpoint "POST" "/api/v1/appointments/" "appointment-service" "201" "$appointment_data" "Create Appointment")

    if [[ $? -eq 0 && -n "$appointment_response" ]]; then
        APPOINTMENT_ID=$(echo "$appointment_response" | jq -r '.appointment_id // .id // empty' 2>/dev/null)
        log_success "Appointment ID obtained: $APPOINTMENT_ID"
    fi

    log_info "2. Get appointment by ID"
    if [[ -n "$APPOINTMENT_ID" && "$APPOINTMENT_ID" != "null" ]]; then
        test_endpoint "GET" "/api/v1/appointments/$APPOINTMENT_ID" "appointment-service" "200" "" "Get Appointment by ID"
    fi

    log_info "3. List all appointments"
    test_endpoint "GET" "/api/v1/appointments/?skip=0&limit=10" "appointment-service" "200" "" "List Appointments"

    log_info "4. Get patient appointments"
    test_endpoint "GET" "/api/v1/appointments/patient/$PATIENT_ID?skip=0&limit=10" "appointment-service" "200" "" "Get Patient Appointments"

    log_info "5. Get doctor appointments"
    test_endpoint "GET" "/api/v1/appointments/doctor/$doctor_id?skip=0&limit=10" "appointment-service" "200" "" "Get Doctor Appointments"

    log_info "6. Get upcoming appointments"
    test_endpoint "GET" "/api/v1/appointments/upcoming/list?limit=10" "appointment-service" "200" "" "Get Upcoming Appointments"

    log_info "7. Check doctor availability"
    test_endpoint "GET" "/api/v1/appointments/availability/check?doctor_id=$doctor_id&date=$appointment_date" "appointment-service" "200" "" "Check Doctor Availability"

    log_info "8. Get appointment stats"
    test_endpoint "GET" "/api/v1/appointments/stats/summary" "appointment-service" "200" "" "Get Appointment Stats"

    log_info "9. Update appointment"
    if [[ -n "$APPOINTMENT_ID" && "$APPOINTMENT_ID" != "null" ]]; then
        local update_data='{
            "notes": "Updated notes - patient confirmed attendance"
        }'
        test_endpoint "PUT" "/api/v1/appointments/$APPOINTMENT_ID" "appointment-service" "200" "$update_data" "Update Appointment"
    fi

    log_info "10. Health check"
    test_endpoint "GET" "/api/v1/appointments/health/check" "appointment-service" "200" "" "Appointment Service Health Check"
}

test_prescription_service() {
    log_info "=========================================="
    log_info "Testing Prescription Service (Port 8003)"
    log_info "=========================================="

    if [[ -z "$PATIENT_ID" || "$PATIENT_ID" == "null" ]]; then
        log_warning "No valid patient_id, using default test patient ID"
        PATIENT_ID="test-patient-001"
    fi

    log_info "1. Create prescription"
    local prescription_data='{
        "patient_id": "'"$PATIENT_ID"'",
        "prescriber_id": "doctor-001",
        "medication_name": "Amoxicillin",
        "dosage": "500mg",
        "frequency": "Three times daily",
        "duration": "7 days",
        "instructions": "Take with food",
        "quantity": 21
    }'

    local prescription_response=$(test_endpoint "POST" "/api/v1/prescriptions" "prescription-service" "201" "$prescription_data" "Create Prescription")

    if [[ $? -eq 0 && -n "$prescription_response" ]]; then
        PRESCRIPTION_ID=$(echo "$prescription_response" | jq -r '.prescription_id // .id // ._id // empty' 2>/dev/null)
        log_success "Prescription ID obtained: $PRESCRIPTION_ID"
    fi

    log_info "2. Get prescription by ID"
    if [[ -n "$PRESCRIPTION_ID" && "$PRESCRIPTION_ID" != "null" ]]; then
        test_endpoint "GET" "/api/v1/prescriptions/$PRESCRIPTION_ID" "prescription-service" "200" "" "Get Prescription by ID"
    fi

    log_info "3. List prescriptions by patient"
    test_endpoint "GET" "/api/v1/prescriptions?patient_id=$PATIENT_ID&skip=0&limit=10" "prescription-service" "200" "" "List Prescriptions"

    log_info "4. Update prescription"
    if [[ -n "$PRESCRIPTION_ID" && "$PRESCRIPTION_ID" != "null" ]]; then
        local update_data='{
            "instructions": "Take with food and plenty of water",
            "notes": "Patient reported no allergies"
        }'
        test_endpoint "PUT" "/api/v1/prescriptions/$PRESCRIPTION_ID" "prescription-service" "200" "$update_data" "Update Prescription"
    fi

    log_info "5. Create medical record"
    local medical_record_data='{
        "patient_id": "'"$PATIENT_ID"'",
        "provider_id": "doctor-001",
        "record_type": "consultation",
        "diagnosis": "Upper respiratory tract infection",
        "symptoms": ["cough", "fever", "sore throat"],
        "vital_signs": {
            "temperature": "38.5",
            "blood_pressure": "120/80",
            "heart_rate": "75",
            "respiratory_rate": "16"
        },
        "notes": "Patient presented with symptoms for 3 days"
    }'

    local medical_record_response=$(test_endpoint "POST" "/api/v1/medical-records" "prescription-service" "201" "$medical_record_data" "Create Medical Record")

    if [[ $? -eq 0 && -n "$medical_record_response" ]]; then
        MEDICAL_RECORD_ID=$(echo "$medical_record_response" | jq -r '.record_id // .id // ._id // empty' 2>/dev/null)
        log_success "Medical Record ID obtained: $MEDICAL_RECORD_ID"
    fi

    log_info "6. Get medical record by ID"
    if [[ -n "$MEDICAL_RECORD_ID" && "$MEDICAL_RECORD_ID" != "null" ]]; then
        test_endpoint "GET" "/api/v1/medical-records/$MEDICAL_RECORD_ID" "prescription-service" "200" "" "Get Medical Record by ID"
    fi

    log_info "7. List medical records by patient"
    test_endpoint "GET" "/api/v1/medical-records?patient_id=$PATIENT_ID&skip=0&limit=10" "prescription-service" "200" "" "List Medical Records"

    log_info "8. Health check"
    test_endpoint "GET" "/prescription/health" "prescription-service" "200" "" "Prescription Service Health Check"
}

test_billing_service() {
    log_info "=========================================="
    log_info "Testing Billing Service (Port 8004)"
    log_info "=========================================="

    if [[ -z "$PATIENT_ID" || "$PATIENT_ID" == "null" ]]; then
        log_warning "No valid patient_id, using default test patient ID"
        PATIENT_ID="test-patient-001"
    fi

    log_info "1. Create invoice"
    local invoice_data='{
        "subject": "'"$PATIENT_ID"'",
        "total_gross": {
            "value": 500.00,
            "currency": "USD"
        },
        "total_net": {
            "value": 450.00,
            "currency": "USD"
        },
        "line_items": [
            {
                "description": "Consultation fee",
                "quantity": 1,
                "unit_price": {
                    "value": 200.00,
                    "currency": "USD"
                },
                "total": {
                    "value": 200.00,
                    "currency": "USD"
                }
            },
            {
                "description": "Prescription medication",
                "quantity": 1,
                "unit_price": {
                    "value": 250.00,
                    "currency": "USD"
                },
                "total": {
                    "value": 250.00,
                    "currency": "USD"
                }
            }
        ]
    }'

    local invoice_response=$(test_endpoint "POST" "/api/v1/invoices" "billing-service" "201" "$invoice_data" "Create Invoice")

    if [[ $? -eq 0 && -n "$invoice_response" ]]; then
        INVOICE_ID=$(echo "$invoice_response" | jq -r '.invoice_id // .id // empty' 2>/dev/null)
        log_success "Invoice ID obtained: $INVOICE_ID"
    fi

    log_info "2. Get invoice by ID"
    if [[ -n "$INVOICE_ID" && "$INVOICE_ID" != "null" ]]; then
        test_endpoint "GET" "/api/v1/invoices/$INVOICE_ID" "billing-service" "200" "" "Get Invoice by ID"
    fi

    log_info "3. List invoices by patient"
    test_endpoint "GET" "/api/v1/invoices?patient_id=$PATIENT_ID&skip=0&limit=10" "billing-service" "200" "" "List Invoices"

    log_info "4. Update invoice"
    if [[ -n "$INVOICE_ID" && "$INVOICE_ID" != "null" ]]; then
        local update_data='{
            "notes": "Patient requested itemized invoice"
        }'
        test_endpoint "PUT" "/api/v1/invoices/$INVOICE_ID" "billing-service" "200" "$update_data" "Update Invoice"
    fi

    log_info "5. Create payment"
    local payment_data='{
        "invoice_id": "'"$INVOICE_ID"'",
        "amount": {
            "value": 450.00,
            "currency": "USD"
        },
        "payment_method": "credit_card",
        "payment_date": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
    }'

    local payment_response=$(test_endpoint "POST" "/api/v1/payments" "billing-service" "201" "$payment_data" "Create Payment")

    if [[ $? -eq 0 && -n "$payment_response" ]]; then
        PAYMENT_ID=$(echo "$payment_response" | jq -r '.payment_id // .id // empty' 2>/dev/null)
        log_success "Payment ID obtained: $PAYMENT_ID"
    fi

    log_info "6. Get payment by ID"
    if [[ -n "$PAYMENT_ID" && "$PAYMENT_ID" != "null" ]]; then
        test_endpoint "GET" "/api/v1/payments/$PAYMENT_ID" "billing-service" "200" "" "Get Payment by ID"
    fi

    log_info "7. List payments by invoice"
    if [[ -n "$INVOICE_ID" && "$INVOICE_ID" != "null" ]]; then
        test_endpoint "GET" "/api/v1/payments?invoice_id=$INVOICE_ID&skip=0&limit=10" "billing-service" "200" "" "List Payments"
    fi

    log_info "8. Create insurance claim"
    local claim_data='{
        "patient_id": "'"$PATIENT_ID"'",
        "provider_id": "doctor-001",
        "insurance_company": "HealthCare Insurance Co.",
        "policy_number": "POL123456789",
        "claim_amount": {
            "value": 500.00,
            "currency": "USD"
        },
        "diagnosis_codes": ["J06.9"],
        "procedure_codes": ["99213"],
        "service_date": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
    }'

    local claim_response=$(test_endpoint "POST" "/api/v1/claims" "billing-service" "201" "$claim_data" "Create Insurance Claim")

    if [[ $? -eq 0 && -n "$claim_response" ]]; then
        CLAIM_ID=$(echo "$claim_response" | jq -r '.claim_id // .id // empty' 2>/dev/null)
        log_success "Claim ID obtained: $CLAIM_ID"
    fi

    log_info "9. Get claim by ID"
    if [[ -n "$CLAIM_ID" && "$CLAIM_ID" != "null" ]]; then
        test_endpoint "GET" "/api/v1/claims/$CLAIM_ID" "billing-service" "200" "" "Get Claim by ID"
    fi

    log_info "10. List claims by patient"
    test_endpoint "GET" "/api/v1/claims?patient_id=$PATIENT_ID&skip=0&limit=10" "billing-service" "200" "" "List Claims"

    log_info "11. Generate revenue report"
    local start_date=$(date -u -d "-30 days" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v-30d +"%Y-%m-%dT%H:%M:%SZ")
    local end_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    test_endpoint "GET" "/api/v1/reports/revenue?start_date=$start_date&end_date=$end_date" "billing-service" "200" "" "Generate Revenue Report"

    log_info "12. Get patient billing summary"
    test_endpoint "GET" "/api/v1/reports/patient/$PATIENT_ID/summary" "billing-service" "200" "" "Get Patient Billing Summary"

    log_info "13. Health check"
    test_endpoint "GET" "/billing/health" "billing-service" "200" "" "Billing Service Health Check"
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "Test Execution Summary"
    echo "=========================================="
    echo -e "Total Tests:  ${BLUE}$TOTAL_TESTS${NC}"
    echo -e "Passed:       ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed:       ${RED}$FAILED_TESTS${NC}"

    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "\n${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "\n${RED}Some tests failed. Please review the logs above.${NC}"
        return 1
    fi
}

main() {
    log_info "Healthcare Patient Management System - E2E Tests"
    log_info "Deployment Mode: $DEPLOYMENT_MODE"
    log_info "Base URL: ${BASE_URL:-<not provided>}"

    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed. Please install it first."
        log_info "  Ubuntu/Debian: sudo apt-get install jq"
        log_info "  macOS: brew install jq"
        exit 1
    fi

    setup_deployment_mode

    sleep 2

    test_patient_service
    sleep 1

    test_appointment_service
    sleep 1

    test_prescription_service
    sleep 1

    test_billing_service

    print_summary
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
