#!/bin/bash

# Database Initialization Script for Billing Service
# Reusable for local development, Docker, and Kubernetes environments

set -e

echo "Initializing Billing Service Database..."

# For docker-entrypoint-initdb.d, PostgreSQL is not yet ready
# The database creation happens automatically via POSTGRES_DB env var
# This script only needs to run additional setup if needed

# Optional: Seed data for development
if [ "${SEED_DATA}" = "true" ]; then
    echo "Seeding development data..."

    psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-billing_db}" <<-EOSQL
        -- Sample seed data can be added here
        -- Example: INSERT INTO invoices VALUES (...);

        SELECT 'Seed data inserted successfully';
EOSQL

    echo "Seed data inserted."
fi

echo "Billing Service database initialization complete!"
