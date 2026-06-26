-- RLS template (§4.0.6) — apply per tenant-scoped table in migrations
-- Middleware sets: SELECT set_config('app.tenant_id', '<id>', true);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON users;
CREATE POLICY tenant_isolation ON users
  USING (
    tenant_id IS NULL
    OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
  );
