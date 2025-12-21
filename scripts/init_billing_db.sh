#!/bin/bash

set -e

echo "Initializing Billing Service Database..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVOICE_CSV="${SCRIPT_DIR}/invoice_data.csv"
LINE_ITEM_CSV="${SCRIPT_DIR}/invoice_line_item_data.csv"
PAYMENT_CSV="${SCRIPT_DIR}/payment_record_data.csv"
CLAIM_CSV="${SCRIPT_DIR}/insurance_claim_data.csv"

if [ "${SEED_DATA}" = "true" ]; then
    echo "Seeding billing data from CSV files..."

    for file in "$INVOICE_CSV" "$LINE_ITEM_CSV" "$PAYMENT_CSV" "$CLAIM_CSV"; do
        if [ ! -f "$file" ]; then
            echo "Error: $file not found!"
            exit 1
        fi
    done

    psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-billing_db}" <<-EOSQL
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        CREATE TEMP TABLE invoice_temp (
            invoice_id VARCHAR(100),
            patient_id VARCHAR(100),
            appointment_id VARCHAR(100),
            date DATE,
            status VARCHAR(50),
            total_net DECIMAL(10,2),
            total_gross DECIMAL(10,2),
            account_status VARCHAR(50),
            payment_terms VARCHAR(50),
            notes TEXT
        );

        \COPY invoice_temp FROM '${INVOICE_CSV}' WITH (FORMAT csv, HEADER true, NULL '', DELIMITER ',', QUOTE '"');

        INSERT INTO invoices (
            id,
            resource_type,
            identifier,
            status,
            subject,
            date,
            participant,
            issuer,
            account,
            total_net_value,
            total_net_currency,
            total_gross_value,
            total_gross_currency,
            payment_terms,
            note,
            meta,
            created_at,
            updated_at
        )
        SELECT
            uuid_generate_v4(),
            'Invoice',
            jsonb_build_object(
                'system', 'invoice',
                'value', invoice_id
            ),
            status,
            patient_id,
            date,
            jsonb_build_object(
                'role', 'appointment',
                'reference', 'Appointment/' || appointment_id
            ),
            jsonb_build_object(
                'identifier', 'Healthcare Provider'
            ),
            jsonb_build_object(
                'status', account_status
            ),
            total_net,
            'USD',
            total_gross,
            'USD',
            NULLIF(payment_terms, ''),
            NULLIF(notes, ''),
            jsonb_build_object(
                'appointmentId', appointment_id
            ),
            NOW(),
            NOW()
        FROM invoice_temp;

        DROP TABLE invoice_temp;

        SELECT COUNT(*) || ' invoices inserted' FROM invoices;

        CREATE TEMP TABLE line_item_temp (
            line_item_id INTEGER,
            invoice_id VARCHAR(100),
            sequence INTEGER,
            code VARCHAR(50),
            description VARCHAR(255),
            quantity INTEGER,
            unit_price DECIMAL(10,2),
            net_amount DECIMAL(10,2),
            tax_rate DECIMAL(5,2),
            gross_amount DECIMAL(10,2)
        );

        \COPY line_item_temp FROM '${LINE_ITEM_CSV}' WITH (FORMAT csv, HEADER true, NULL '', DELIMITER ',', QUOTE '"');

        INSERT INTO invoice_line_items (
            id,
            invoice_id,
            sequence,
            charge_item_code,
            charge_item_display,
            price_component_type,
            price_component_code,
            price_component_factor,
            price_component_amount_value,
            price_component_amount_currency,
            created_at,
            updated_at
        )
        SELECT
            uuid_generate_v4(),
            i.id,
            sequence,
            code,
            description,
            'base',
            code,
            quantity,
            unit_price,
            'USD',
            NOW(),
            NOW()
        FROM line_item_temp lt
        INNER JOIN invoices i ON i.identifier->>'value' = lt.invoice_id;

        DROP TABLE line_item_temp;

        SELECT COUNT(*) || ' line items inserted' FROM invoice_line_items;

        CREATE TEMP TABLE payment_temp (
            payment_id VARCHAR(100),
            invoice_id VARCHAR(100),
            amount DECIMAL(10,2),
            payment_method VARCHAR(50),
            payment_date DATE,
            status VARCHAR(50),
            transaction_id VARCHAR(100),
            notes TEXT
        );

        \COPY payment_temp FROM '${PAYMENT_CSV}' WITH (FORMAT csv, HEADER true, NULL '', DELIMITER ',', QUOTE '"');

        INSERT INTO payment_records (
            id,
            invoice_id,
            payment_method,
            payment_date,
            amount_value,
            amount_currency,
            status,
            transaction_id,
            reference,
            note,
            created_at,
            updated_at
        )
        SELECT
            uuid_generate_v4(),
            i.id,
            payment_method,
            payment_date,
            amount,
            'USD',
            status,
            transaction_id,
            payment_id,
            NULLIF(notes, ''),
            NOW(),
            NOW()
        FROM payment_temp pt
        INNER JOIN invoices i ON i.identifier->>'value' = pt.invoice_id;

        DROP TABLE payment_temp;

        SELECT COUNT(*) || ' payment records inserted' FROM payment_records;

        CREATE TEMP TABLE claim_temp (
            claim_id INTEGER,
            claim_number VARCHAR(100),
            patient_id VARCHAR(100),
            invoice_id VARCHAR(100),
            status VARCHAR(50),
            claim_amount DECIMAL(10,2),
            approved_amount DECIMAL(10,2),
            submitted_date DATE,
            processed_date DATE,
            insurance_provider VARCHAR(255),
            policy_number VARCHAR(100),
            denial_reason TEXT
        );

        \COPY claim_temp FROM '${CLAIM_CSV}' WITH (FORMAT csv, HEADER true, NULL '', DELIMITER ',', QUOTE '"');

        INSERT INTO insurance_claims (
            id,
            claim_number,
            patient_id,
            invoice_id,
            status,
            type,
            use_code,
            insurance_provider,
            insurance_policy_number,
            total_value,
            total_currency,
            payment_amount_value,
            payment_amount_currency,
            created_date,
            processed_date,
            adjudication_reason,
            created_at,
            updated_at
        )
        SELECT
            uuid_generate_v4(),
            claim_number,
            patient_id,
            i.id,
            status,
            'institutional',
            'claim',
            insurance_provider,
            policy_number,
            claim_amount,
            'USD',
            NULLIF(approved_amount, 0),
            CASE WHEN approved_amount > 0 THEN 'USD' ELSE NULL END,
            submitted_date,
            NULLIF(processed_date::TEXT, '')::DATE,
            NULLIF(denial_reason, ''),
            NOW(),
            NOW()
        FROM claim_temp ct
        INNER JOIN invoices i ON i.identifier->>'value' = ct.invoice_id;

        DROP TABLE claim_temp;

        SELECT COUNT(*) || ' insurance claims inserted' FROM insurance_claims;
EOSQL

    echo "Billing data seeding complete."
fi

echo "Billing Service database initialization complete!"
