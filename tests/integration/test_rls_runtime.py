"""RLS must hold for a non-superuser database role (real SQL-level isolation).

The default test connection is a superuser (which PostgreSQL exempts from RLS),
so this test creates a temporary limited role and verifies the policy directly.
"""

from __future__ import annotations

import re

import psycopg2
import pytest
from catalog_svc.product_service import ProductService
from tenant_svc.tenant_service import TenantService

from orion.extensions import db

pytestmark = pytest.mark.integration

ROLE = "orion_rls_probe"
PASSWORD = "orion_rls_probe_pwd"

def _drop_probe_role(cur) -> None:
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,))
    if not cur.fetchone():
        return
    cur.execute(f"REVOKE ALL ON SCHEMA public FROM {ROLE}")
    cur.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {ROLE}")
    cur.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {ROLE}")
    cur.execute(f"DROP ROLE IF EXISTS {ROLE}")


POLICY_SQL = """
current_setting('app.is_platform_admin', true) = 'true'
OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
"""


def test_rls_blocks_cross_tenant_writes_and_reads(app):
    admin_url = app.config["SQLALCHEMY_DATABASE_URI"]
    with app.app_context():
        tenant_a = TenantService().create_tenant(
            name="RLS A", slug="rls-a", email="rls-a@test.com"
        )
        tenant_b = TenantService().create_tenant(
            name="RLS B", slug="rls-b", email="rls-b@test.com"
        )
        product_a = ProductService().create(
            tenant_id=tenant_a.id, name="RLS Prod A", slug="rls-prod-a", price="10.00"
        )
        product_b = ProductService().create(
            tenant_id=tenant_b.id, name="RLS Prod B", slug="rls-prod-b", price="20.00"
        )
        tenant_a_id = tenant_a.id
        tenant_b_id = tenant_b.id
        product_a_id = product_a.id
        product_b_id = product_b.id

        # Release the test session's read lock before altering the table policy.
        db.session.remove()

        admin = psycopg2.connect(admin_url)
        admin.autocommit = True
        cur = admin.cursor()
        try:
            _drop_probe_role(cur)
            cur.execute(f"CREATE ROLE {ROLE} LOGIN PASSWORD '{PASSWORD}'")
            cur.execute(f"GRANT USAGE ON SCHEMA public TO {ROLE}")
            cur.execute(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ROLE}"
            )
            cur.execute(
                f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {ROLE}"
            )
            cur.execute("ALTER TABLE products ENABLE ROW LEVEL SECURITY")
            cur.execute("DROP POLICY IF EXISTS tenant_isolation ON products")
            cur.execute(
                f"CREATE POLICY tenant_isolation ON products "
                f"USING ({POLICY_SQL}) WITH CHECK ({POLICY_SQL})"
            )

            probe_url = re.sub(
                r"^(postgresql(?:\+psycopg2)?://)[^@]+@",
                rf"\1{ROLE}:{PASSWORD}@",
                admin_url,
            )
            probe = psycopg2.connect(probe_url)
            probe_cur = probe.cursor()
            try:
                probe_cur.execute(f"SET ROLE {ROLE}")
                probe_cur.execute("SET app.tenant_id = %s", (str(tenant_a_id),))
                probe_cur.execute("SET app.is_platform_admin = 'false'")
                probe_cur.execute("SELECT id FROM products ORDER BY id")
                visible = [row[0] for row in probe_cur.fetchall()]
                assert visible == [product_a_id]

                probe.rollback()
                probe_cur.execute(f"SET ROLE {ROLE}")
                probe_cur.execute("SET app.tenant_id = %s", (str(tenant_a_id),))
                probe_cur.execute("SET app.is_platform_admin = 'false'")
                with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                    probe_cur.execute(
                        "INSERT INTO products "
                        "(public_id,name,slug,tenant_id,price,quantity,"
                        "is_published,is_featured,is_active,version) "
                        "VALUES (gen_random_uuid(),'Hack','hack',%s,'1.00',1,"
                        "true,false,true,1)",
                        (tenant_b_id,),
                    )

                probe.rollback()
                probe_cur.execute(f"SET ROLE {ROLE}")
                probe_cur.execute("SET app.tenant_id = %s", (str(tenant_a_id),))
                probe_cur.execute("SET app.is_platform_admin = 'true'")
                probe_cur.execute("SELECT id FROM products ORDER BY id")
                assert {row[0] for row in probe_cur.fetchall()} == {
                    product_a_id,
                    product_b_id,
                }
            finally:
                probe.close()
        finally:
            cur.execute("DROP POLICY IF EXISTS tenant_isolation ON products")
            cur.execute("ALTER TABLE products DISABLE ROW LEVEL SECURITY")
            _drop_probe_role(cur)
            admin.close()
