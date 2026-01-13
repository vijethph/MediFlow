#!/bin/bash

set -e

echo "Initializing Patient Service Database..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV_FILE="${SCRIPT_DIR}/patient_data.csv"

if [ "${SEED_DATA}" = "true" ]; then
    echo "Seeding patient data from CSV..."

    if [ ! -f "$CSV_FILE" ]; then
        echo "Error: $CSV_FILE not found!"
        exit 1
    fi

    psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-patient_db}" <<-EOSQL
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        CREATE TEMP TABLE patient_temp (
            patient_id VARCHAR(100),
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(50),
            gender VARCHAR(20),
            birth_date DATE,
            active BOOLEAN,
            marital_status VARCHAR(50),
            address_line1 VARCHAR(255),
            address_line2 VARCHAR(255),
            city VARCHAR(100),
            state VARCHAR(100),
            postal_code VARCHAR(20),
            country VARCHAR(10),
            blood_type VARCHAR(10),
            allergies TEXT,
            chronic_conditions TEXT,
            emergency_contact_name VARCHAR(255),
            emergency_contact_phone VARCHAR(50),
            insurance_provider VARCHAR(255),
            insurance_policy_number VARCHAR(100)
        );

        \COPY patient_temp FROM '${CSV_FILE}' WITH (FORMAT csv, HEADER true, NULL '', DELIMITER ',', QUOTE '"');

        INSERT INTO patients (
            id,
            resource_type,
            patient_id,
            active,
            name,
            telecom,
            gender,
            birth_date,
            address,
            marital_status,
            meta,
            created_at,
            updated_at
        )
        SELECT
            uuid_generate_v4(),
            'Patient',
            patient_id,
            active,
            jsonb_build_object(
                'family', last_name,
                'given', jsonb_build_array(first_name),
                'text', first_name || ' ' || last_name
            ),
            jsonb_build_array(
                jsonb_build_object(
                    'system', 'email',
                    'value', email,
                    'use', 'home'
                ),
                jsonb_build_object(
                    'system', 'phone',
                    'value', phone,
                    'use', 'home'
                )
            ),
            NULLIF(gender, ''),
            birth_date,
            jsonb_build_object(
                'line', jsonb_build_array(
                    address_line1,
                    NULLIF(address_line2, '')
                ) - 'null',
                'city', NULLIF(city, ''),
                'state', NULLIF(state, ''),
                'postalCode', NULLIF(postal_code, ''),
                'country', NULLIF(country, '')
            ),
            NULLIF(marital_status, ''),
            jsonb_build_object(
                'bloodType', NULLIF(blood_type, ''),
                'allergies', NULLIF(allergies, ''),
                'chronicConditions', NULLIF(chronic_conditions, ''),
                'emergencyContact', jsonb_build_object(
                    'name', emergency_contact_name,
                    'phone', emergency_contact_phone
                ),
                'insurance', CASE
                    WHEN insurance_provider IS NOT NULL AND insurance_provider != ''
                    THEN jsonb_build_object(
                        'provider', insurance_provider,
                        'policyNumber', NULLIF(insurance_policy_number, '')
                    )
                    ELSE NULL
                END
            ),
            NOW(),
            NOW()
        FROM patient_temp
        ON CONFLICT (patient_id) DO NOTHING;

        DROP TABLE patient_temp;

        SELECT COUNT(*) || ' patients inserted' FROM patients;
EOSQL

    echo "Patient data seeding complete."
fi

echo "Patient Service database initialization complete!"
