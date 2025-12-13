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
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
    ((PASSED_TESTS++))
    ((TOTAL_TESTS++))
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    ((FAILED_TESTS++))
    ((TOTAL_TESTS++))
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

print_debug_info() {
    local service=$1
    local endpoint=$2
    echo -e "${YELLOW}Debug Commands:${NC}" >&2
    if [[ "$DEPLOYMENT_MODE" == "kubernetes" || "$DEPLOYMENT_MODE" == "k8s" ]]; then
        echo "  kubectl logs -n healthcare deployment/${service} --tail=50" >&2
        echo "  kubectl describe pod -n healthcare -l app=${service}" >&2
        echo "  kubectl get events -n healthcare --sort-by='.lastTimestamp'" >&2
    else
        echo "  docker-compose logs ${service} --tail=50" >&2
        echo "  docker-compose ps ${service}" >&2
        echo "  curl -v ${BASE_URL}/${service}${endpoint}" >&2
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
        echo "Response: $body" >&2
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

    log_info "1. Register new patient"
    local register_data='{
        "name": [
            {
                "use": "official",
                "family": "Doe",
                "given": ["John"]
            }
        ],
        "birth_date": "1990-01-01",
        "gender": "male",
        "telecom": [
            {
                "system": "phone",
                "value": "+1234567890"
            },
            {
                "system": "email",
                "value": "'"$email"'"
            }
        ],
        "address": [
            {
                "line": ["123 Main St"],
                "city": "City",
                "state": "State",
                "postal_code": "12345",
                "country": "USA"
            }
        ]
    }'

    local register_response=$(test_endpoint "POST" "/api/v1/patients/register" "patient-service" "201" "$register_data" "Register Patient")
    local register_status=$?

    if [[ $register_status -eq 0 && -n "$register_response" ]]; then
        JWT_TOKEN=$(echo "$register_response" | jq -r '.access_token // .token // empty' 2>/dev/null)
        PATIENT_ID=$(echo "$register_response" | jq -r '.patient_id // empty' 2>/dev/null)

        if [[ -n "$JWT_TOKEN" && "$JWT_TOKEN" != "null" ]]; then
            log_success "JWT Token obtained from registration: ${JWT_TOKEN:0:20}..."
        else
            log_warning "Registration succeeded but no JWT token in response"
            echo "Response: $register_response" | head -5 >&2
        fi

        if [[ -n "$PATIENT_ID" && "$PATIENT_ID" != "null" ]]; then
            log_success "Patient ID obtained from registration: $PATIENT_ID"
        else
            log_warning "Registration succeeded but no patient_id in response"
        fi
    else
        log_warning "Patient registration failed or returned no data"
    fi    # If registration failed or no token, try login with a default test user
    if [[ -z "$JWT_TOKEN" || "$JWT_TOKEN" == "null" ]]; then
        log_info "2. Login with default test credentials (registration may have failed due to duplicate email)"

        # Try with a known test account
        local login_data='{
            "email": "test@example.com"
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
            "email": "'"$email"'"
        }'

        test_endpoint "POST" "/api/v1/patients/login" "patient-service" "200" "$login_data" "Patient Login"
    fi

    log_info "3. List all patients"
    local patients_response=$(test_endpoint "GET" "/api/v1/patients/?skip=0&limit=10" "patient-service" "200" "" "List Patients")

    if [[ $? -eq 0 && -n "$patients_response" ]]; then
        # Try to extract patient_id from list response (items array)
        local extracted_id=$(echo "$patients_response" | jq -r '.items[0].id // .items[0].patient_id // empty' 2>/dev/null)

        if [[ -n "$extracted_id" && "$extracted_id" != "null" ]]; then
            PATIENT_ID="$extracted_id"
            log_success "Patient ID obtained from list: $PATIENT_ID"
        elif [[ -z "$PATIENT_ID" || "$PATIENT_ID" == "null" ]]; then
            log_warning "Could not extract patient_id from list response and no patient from registration"
            log_warning "Tests requiring patient_id will be skipped"
        fi
    fi

    log_info "4. Get patient by ID"
    if [[ -n "$PATIENT_ID" && "$PATIENT_ID" != "null" ]]; then
        test_endpoint "GET" "/api/v1/patients/$PATIENT_ID" "patient-service" "200" "" "Get Patient by ID"
    fi

    log_info "5. Update patient"
    if [[ -n "$PATIENT_ID" && "$PATIENT_ID" != "null" ]]; then
        local update_data='{
            "telecom": [
                {
                    "system": "phone",
                    "value": "+9876543210"
                }
            ],
            "address": [
                {
                    "line": ["456 New St"],
                    "city": "New City",
                    "state": "State",
                    "postal_code": "67890",
                    "country": "USA"
                }
            ]
        }'
        test_endpoint "PUT" "/api/v1/patients/$PATIENT_ID" "patient-service" "200" "$update_data" "Update Patient"
    fi

    log_info "6. Delete patient (soft delete)"
    if [[ -n "$PATIENT_ID" && "$PATIENT_ID" != "null" ]]; then
        test_endpoint "DELETE" "/api/v1/patients/$PATIENT_ID" "patient-service" "204" "" "Delete Patient (Soft Delete)"
    fi

    log_info "7. Health check"
    test_endpoint "GET" "/patient/health" "patient-service" "200" "" "Patient Service Health Check"
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
    local start_time=$(date -u -d "+1 day" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v+1d +"%Y-%m-%dT%H:%M:%SZ")
    local end_time=$(date -u -d "+1 day +1 hour" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v+1d -v+1H +"%Y-%m-%dT%H:%M:%SZ")

    log_info "1. Create appointment"
    local appointment_data='{
        "patient_id": "'"$PATIENT_ID"'",
        "practitioner_id": "'"$doctor_id"'",
        "start": "'"$start_time"'",
        "end": "'"$end_time"'",
        "description": "Annual checkup",
        "comment": "Patient requested full physical exam"
    }'

    local appointment_response=$(test_endpoint "POST" "/api/v1/appointments" "appointment-service" "201" "$appointment_data" "Create Appointment")

    if [[ $? -eq 0 && -n "$appointment_response" ]]; then
        APPOINTMENT_ID=$(echo "$appointment_response" | jq -r '.appointment_id // .id // empty' 2>/dev/null)
        log_success "Appointment ID obtained: $APPOINTMENT_ID"
    fi

    log_info "2. Get appointment by ID"
    if [[ -n "$APPOINTMENT_ID" && "$APPOINTMENT_ID" != "null" ]]; then
        test_endpoint "GET" "/api/v1/appointments/$APPOINTMENT_ID" "appointment-service" "200" "" "Get Appointment by ID"
    fi

    log_info "3. List all appointments"
    test_endpoint "GET" "/api/v1/appointments?skip=0&limit=10" "appointment-service" "200" "" "List Appointments"

    log_info "4. Get patient appointments"
    test_endpoint "GET" "/api/v1/appointments?patient_id=$PATIENT_ID&skip=0&limit=10" "appointment-service" "200" "" "Get Patient Appointments"

    log_info "5. Get doctor appointments"
    test_endpoint "GET" "/api/v1/appointments?practitioner_id=$doctor_id&skip=0&limit=10" "appointment-service" "200" "" "Get Doctor Appointments"

    log_info "6. Get upcoming appointments"
    local today=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    test_endpoint "GET" "/api/v1/appointments?start_date=$today&skip=0&limit=10" "appointment-service" "200" "" "Get Upcoming Appointments"

    log_info "7. Get pending appointments"
    test_endpoint "GET" "/api/v1/appointments?appointment_status=pending&skip=0&limit=10" "appointment-service" "200" "" "Get Pending Appointments"

    log_info "8. Update appointment"
    if [[ -n "$APPOINTMENT_ID" && "$APPOINTMENT_ID" != "null" ]]; then
        local update_data='{
            "notes": "Updated notes - patient confirmed attendance",
            "status": "confirmed"
        }'
        test_endpoint "PUT" "/api/v1/appointments/$APPOINTMENT_ID" "appointment-service" "200" "$update_data" "Update Appointment"
    fi

    log_info "9. Cancel appointment"
    if [[ -n "$APPOINTMENT_ID" && "$APPOINTMENT_ID" != "null" ]]; then
        test_endpoint "POST" "/api/v1/appointments/$APPOINTMENT_ID/cancel" "appointment-service" "200" "" "Cancel Appointment"
    fi

    log_info "10. Delete appointment (if needed for cleanup)"
    if [[ -n "$APPOINTMENT_ID" && "$APPOINTMENT_ID" != "null" ]]; then
        test_endpoint "DELETE" "/api/v1/appointments/$APPOINTMENT_ID" "appointment-service" "204" "" "Delete Appointment"
    fi

    log_info "11. Health check"
    test_endpoint "GET" "/appointment/health" "appointment-service" "200" "" "Appointment Service Health Check"
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
        "doctor_name": "Dr. John Smith",
        "doctor_id": "doctor-001",
        "medications": [
            {
                "medication_name": "Amoxicillin",
                "dosage": "500mg",
                "frequency": "three_times_daily",
                "duration_days": 7,
                "instructions": "Take with food",
                "quantity": 21
            }
        ],
        "diagnosis": "Bacterial infection",
        "notes": "Patient requested antibiotic treatment"
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
        "doctor_name": "Dr. John Smith",
        "doctor_id": "doctor-001",
        "record_type": "consultation",
        "title": "Upper Respiratory Tract Infection Consultation",
        "description": "Patient presented with symptoms of upper respiratory tract infection for 3 days",
        "symptoms": ["cough", "fever", "sore throat"],
        "vital_signs": {
            "temperature": 38.5,
            "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80,
            "heart_rate": 75,
            "respiratory_rate": 16
        }
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

    log_info "8. Update medical record"
    if [[ -n "$MEDICAL_RECORD_ID" && "$MEDICAL_RECORD_ID" != "null" ]]; then
        local update_data='{
            "notes": "Updated notes - patient follow-up scheduled"
        }'
        test_endpoint "PUT" "/api/v1/medical-records/$MEDICAL_RECORD_ID" "prescription-service" "200" "$update_data" "Update Medical Record"
    fi

    log_info "9. Create lab result"
    local test_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local result_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local lab_result_data='{
        "patient_id": "'"$PATIENT_ID"'",
        "test_panel_name": "Complete Blood Count (CBC)",
        "test_category": "Hematology",
        "ordering_doctor": "Dr. John Smith",
        "performing_lab": "City General Hospital Lab",
        "test_date": "'"$test_date"'",
        "result_date": "'"$result_date"'",
        "tests": [
            {
                "test_name": "White Blood Cell Count",
                "test_code": "WBC",
                "result_value": "7.5",
                "unit": "K/uL",
                "reference_range": "4.5-11.0",
                "abnormal_flag": "N"
            },
            {
                "test_name": "Red Blood Cell Count",
                "test_code": "RBC",
                "result_value": "4.8",
                "unit": "M/uL",
                "reference_range": "4.5-5.5",
                "abnormal_flag": "N"
            }
        ],
        "interpretation": "All parameters within normal range"
    }'

    local lab_result_response=$(test_endpoint "POST" "/api/v1/lab-results" "prescription-service" "201" "$lab_result_data" "Create Lab Result")

    local LAB_RESULT_ID=""
    if [[ $? -eq 0 && -n "$lab_result_response" ]]; then
        LAB_RESULT_ID=$(echo "$lab_result_response" | jq -r '.result_id // .id // ._id // empty' 2>/dev/null)
        log_success "Lab Result ID obtained: $LAB_RESULT_ID"
    fi

    log_info "10. Get lab result by ID"
    if [[ -n "$LAB_RESULT_ID" && "$LAB_RESULT_ID" != "null" ]]; then
        test_endpoint "GET" "/api/v1/lab-results/$LAB_RESULT_ID" "prescription-service" "200" "" "Get Lab Result by ID"
    fi

    log_info "11. List lab results by patient"
    test_endpoint "GET" "/api/v1/lab-results?patient_id=$PATIENT_ID&skip=0&limit=10" "prescription-service" "200" "" "List Lab Results"

    log_info "12. Health check"
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
        "date": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
        "line_items": [
            {
                "sequence": 1,
                "code": "99213",
                "description": "Consultation fee",
                "quantity": 1,
                "unit_price": {
                    "value": 200.00,
                    "currency": "USD"
                },
                "line_total": {
                    "value": 200.00,
                    "currency": "USD"
                }
            },
            {
                "sequence": 2,
                "code": "MED-001",
                "description": "Prescription medication",
                "quantity": 1,
                "unit_price": {
                    "value": 250.00,
                    "currency": "USD"
                },
                "line_total": {
                    "value": 250.00,
                    "currency": "USD"
                }
            }
        ],
        "payment_terms": "Net 30",
        "notes": "Thank you for your business"
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
        "claim_number": "CLM-'$(date +%s)'",
        "type": "professional",
        "patient_id": "'"$PATIENT_ID"'",
        "provider_id": "doctor-001",
        "insurer_name": "HealthCare Insurance Co.",
        "policy_number": "POL123456789",
        "created_date": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
        "billable_period_start": "'$(date -u -d "-7 days" +"%Y-%m-%d" 2>/dev/null || date -u -v-7d +"%Y-%m-%d")'",
        "billable_period_end": "'$(date -u +"%Y-%m-%d")'",
        "items": [
            {
                "sequence": 1,
                "code": "99213",
                "quantity": 1,
                "unit_price": {
                    "value": 200.00,
                    "currency": "USD"
                },
                "net_amount": {
                    "value": 200.00,
                    "currency": "USD"
                }
            },
            {
                "sequence": 2,
                "code": "J06.9",
                "quantity": 1,
                "unit_price": {
                    "value": 300.00,
                    "currency": "USD"
                },
                "net_amount": {
                    "value": 300.00,
                    "currency": "USD"
                }
            }
        ]
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

    log_info "11. Update claim status"
    if [[ -n "$CLAIM_ID" && "$CLAIM_ID" != "null" ]]; then
        local claim_update_data='{
            "status": "submitted",
            "notes": "Claim submitted to insurance"
        }'
        test_endpoint "PUT" "/api/v1/claims/$CLAIM_ID" "billing-service" "200" "$claim_update_data" "Update Claim"
    fi

    log_info "12. Generate revenue report"
    local start_date=$(date -u -d "-30 days" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v-30d +"%Y-%m-%dT%H:%M:%SZ")
    local end_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    test_endpoint "GET" "/api/v1/reports/revenue?start_date=$start_date&end_date=$end_date" "billing-service" "200" "" "Generate Revenue Report"

    log_info "13. Get patient billing summary"
    test_endpoint "GET" "/api/v1/reports/patient/$PATIENT_ID/summary" "billing-service" "200" "" "Get Patient Billing Summary"

    log_info "14. Health check"
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
