#!/bin/sh
set -e

# Only the API container runs migrations. Workers and beat must neither race
# on alembic_version nor attempt DDL with the non-superuser runtime role.
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  MIGRATION_URL="${MIGRATION_DATABASE_URL:-$DATABASE_URL}"
  DATABASE_URL="$MIGRATION_URL" flask db upgrade
  unset MIGRATION_URL
fi

# Honour an explicit command (celery worker/beat, shell, one-off jobs).
# Without one, start the web server as before.
if [ "$#" -gt 0 ]; then
  exec "$@"
fi
exec gunicorn -b 0.0.0.0:5000 -w 2 --timeout 60 orion.wsgi:app
