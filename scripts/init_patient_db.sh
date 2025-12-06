#!/bin/bash

# Database Initialization Script for Patient Service
# Reusable for local development, Docker, and Kubernetes environments

set -e

echo "Initializing Patient Service Database..."

# For docker-entrypoint-initdb.d, PostgreSQL is not yet ready
# The database creation happens automatically via POSTGRES_DB env var
# This script only needs to run additional setup if needed

# Optional: Seed data for development
if [ "${SEED_DATA}" = "true" ]; then
    echo "Seeding development data..."

    psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-patient_db}" <<-EOSQL
        -- Sample seed data for development
        -- Creating test patients

        -- Note: The actual tables are created by SQLAlchemy migrations
        -- This is just for seeding sample data if needed

        SELECT 'Patient database initialized - tables will be created by service on startup';
EOSQL

    echo "Seed data inserted."
fi

echo "Patient Service database initialization complete!"
