#!/bin/sh
set -e

# Migrations need DDL rights and run as the schema-owner/admin role.
# The app itself must keep using the non-superuser DATABASE_URL so RLS applies.
MIGRATION_URL="${MIGRATION_DATABASE_URL:-$DATABASE_URL}"
DATABASE_URL="$MIGRATION_URL" flask db upgrade
unset MIGRATION_URL

exec gunicorn -b 0.0.0.0:5000 -w 2 --timeout 60 orion.wsgi:app
