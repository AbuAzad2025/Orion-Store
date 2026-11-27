#!/bin/bash
# Activate an Orion release ONLY after its own migrations were applied.
# Generic /srv/scripts/activate.sh is left untouched (other apps use it).
# Usage: /srv/scripts/activate_orionstore.sh <release-name>
set -euo pipefail
REL="${1:-}"
ROOT=/srv/apps/orionstore
SVC=orionstore.service
TARGET="$ROOT/releases/$REL"
if [ -z "$REL" ] || [ ! -d "$TARGET" ]; then
  echo "Usage: $0 <existing-release-name>"; exit 1
fi

# Non-root runtime setup (idempotent) — the service user owns only data dirs.
id orion >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin orion
chown -R orion:orion "$ROOT/shared/product-images" 2>/dev/null || true
chown orion:orion "$ROOT/shared/run" "$ROOT/shared/uploads" \
      "$ROOT/shared/invoices" "$ROOT/shared/logs" "$ROOT/shared/db" 2>/dev/null || true
if [ -f "$ROOT/shared/.env" ]; then
  chgrp orion "$ROOT/shared/.env" 2>/dev/null || true
  chmod 640 "$ROOT/shared/.env" 2>/dev/null || true
fi

set -a
[ -f "$ROOT/shared/.env" ] && . "$ROOT/shared/.env"
set +a
export FLASK_ENV=production
export FLASK_APP=wsgi.py
cd "$TARGET"

echo "MIGRATING $REL"
# The production boot guard is skipped only for this in-process migration run.
ORION_SKIP_RLS_CHECK=1 "$ROOT/venv/bin/flask" db upgrade
echo "ALEMBIC $("$ROOT/venv/bin/python" - <<'PY'
import os
from sqlalchemy import create_engine, text
e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    print(",".join(r[0] for r in c.execute(text("SELECT version_num FROM alembic_version"))))
PY
)"
echo "RLS_FORCED $("$ROOT/venv/bin/python" - <<'PY'
import os
from sqlalchemy import create_engine, text
e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    print(bool(c.execute(text("SELECT relforcerowsecurity FROM pg_class WHERE relname='users' AND relkind='r'")).scalar()))
PY
)"

/srv/scripts/activate.sh orionstore "$SVC" "$REL"

for _ in 1 2 3 4 5; do
  body="$(curl -fsS --max-time 5 https://orion.azadexa.com/health || true)"
  if printf '%s' "$body" | grep -q '"status":"ok"'; then
    echo "HEALTH_OK $body"
    exit 0
  fi
  sleep 2
done
echo "HEALTH_FAILED $body"
exit 1
