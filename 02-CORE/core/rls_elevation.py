"""Transaction-local RLS elevation for authentication bootstrap only.

Tenant tables are protected by RLS. The user performing a login cannot be
looked up until we know which tenant (or platform role) they belong to, so the
lookup itself runs with ``app.is_platform_admin=true`` for a few statements.
The previous setting is restored before the view continues.
"""

from __future__ import annotations

from contextlib import contextmanager

from orion.extensions import db


@contextmanager
def platform_read():
    if db.engine.dialect.name != "postgresql":
        yield
        return
    previous = (
        db.session.execute(
            db.text("SELECT current_setting('app.is_platform_admin', true)")
        ).scalar()
        or "false"
    )
    try:
        db.session.execute(
            db.text("SELECT set_config('app.is_platform_admin', 'true', false)")
        )
        yield
    finally:
        # Restore at session level (not transaction-local) so middleware's
        # later bind of the real role is not shadowed by a stale local value.
        db.session.execute(
            db.text("SELECT set_config('app.is_platform_admin', :v, false)"),
            {"v": previous},
        )
