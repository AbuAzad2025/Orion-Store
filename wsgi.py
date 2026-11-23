"""Production WSGI entry point.

The application keeps its packages in six sibling source roots. This module
adds them to sys.path so a WSGI server only needs ``wsgi:application``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for part in ("02-CORE", "03-MODELS", "04-SERVICES", "05-API", "06-STOREFRONT", "07-ADMIN"):
    path = str(ROOT / part)
    if path not in sys.path:
        sys.path.insert(0, path)

from orion.app import create_app  # noqa: E402

application = app = create_app()
