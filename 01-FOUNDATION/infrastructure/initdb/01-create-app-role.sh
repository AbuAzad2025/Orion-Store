#!/bin/sh
# Runs once on a fresh PostgreSQL data directory (official image initdb hook).
# Creates a NON-superuser application role so RLS is actually enforced at runtime.
# The migration role (POSTGRES_USER) stays superuser and owns the schema.
set -e

: "${POSTGRES_APP_PASSWORD:?POSTGRES_APP_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_password="$POSTGRES_APP_PASSWORD" <<-EOSQL
  CREATE ROLE orion_app LOGIN PASSWORD :'app_password';
  GRANT USAGE ON SCHEMA public TO orion_app;

  -- Tables/sequences are created later by the migration role at app startup.
  ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO orion_app;
  ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO orion_app;
EOSQL

echo "orion_app role created (non-superuser, RLS enforced)"
