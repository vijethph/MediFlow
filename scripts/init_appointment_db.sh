#!/bin/bash

set -e

echo "Initializing Appointment Service Database..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV_FILE="${SCRIPT_DIR}/appointment_data.csv"

if [ "${SEED_DATA}" = "true" ]; then
    echo "Seeding appointment data from CSV..."

    if [ ! -f "$CSV_FILE" ]; then
        echo "Error: $CSV_FILE not found!"
        exit 1
    fi

    psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-appointment_db}" <<-EOSQL
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        CREATE TEMP TABLE appointment_temp (
            appointment_id VARCHAR(100),
            patient_id VARCHAR(100),
            practitioner_name VARCHAR(255),
            practitioner_id VARCHAR(100),
            status VARCHAR(50),
            specialty VARCHAR(100),
            service_category VARCHAR(100),
            start_datetime TIMESTAMP,
            duration_minutes INTEGER,
            location VARCHAR(255),
            appointment_type VARCHAR(50),
            reason VARCHAR(255),
            notes TEXT,
            cancellation_reason VARCHAR(255)
        );

        \COPY appointment_temp FROM '${CSV_FILE}' WITH (FORMAT csv, HEADER true, NULL '', DELIMITER ',', QUOTE '"');

        INSERT INTO appointments (
            id,
            resource_type,
            identifier,
            status,
            service_category,
            specialty,
            appointment_type,
            reason_code,
            description,
            start,
            "end",
            minute_duration,
            participant,
            location,
            comment,
            meta,
            created_at,
            updated_at
        )
        SELECT
            uuid_generate_v4(),
            'Appointment',
            jsonb_build_object(
                'system', 'appointment',
                'value', appointment_id
            ),
            status,
            NULLIF(service_category, ''),
            NULLIF(specialty, ''),
            NULLIF(appointment_type, ''),
            NULLIF(reason, ''),
            NULLIF(notes, ''),
            start_datetime,
            start_datetime + (duration_minutes || ' minutes')::INTERVAL,
            duration_minutes,
            jsonb_build_array(
                jsonb_build_object(
                    'type', 'patient',
                    'actor', jsonb_build_object(
                        'reference', 'Patient/' || patient_id,
                        'display', patient_id
                    ),
                    'status', 'accepted'
                ),
                jsonb_build_object(
                    'type', 'practitioner',
                    'actor', jsonb_build_object(
                        'reference', 'Practitioner/' || practitioner_id,
                        'display', practitioner_name
                    ),
                    'status', 'accepted'
                )
            ),
            jsonb_build_object(
                'name', NULLIF(location, ''),
                'type', appointment_type
            ),
            NULLIF(notes, ''),
            jsonb_build_object(
                'cancellationReason', NULLIF(cancellation_reason, '')
            ),
            NOW(),
            NOW()
        FROM appointment_temp
        ON CONFLICT DO NOTHING;

        DROP TABLE appointment_temp;

        SELECT COUNT(*) || ' appointments inserted' FROM appointments;
EOSQL

    echo "Appointment data seeding complete."
fi

echo "Appointment Service database initialization complete!"
