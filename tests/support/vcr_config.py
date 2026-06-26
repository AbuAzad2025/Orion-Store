"""VCR.py configuration for wave 4+ payment / webhook tests.

Usage (future):
    @pytest.mark.external
    @pytest.mark.vcr()
    def test_stripe_connect_oauth(...):
        ...

Re-record cassettes only in a controlled sandbox with ``VCR_RECORD=1``.
"""

from __future__ import annotations

import os
from pathlib import Path

import vcr as vcr_lib

CASSETTE_DIR = Path(__file__).resolve().parents[1] / "cassettes"

# Never commit live secrets — scrub before writing YAML cassettes.
VCR_FILTER_HEADERS = ["authorization", "x-api-key", "stripe-signature"]
VCR_FILTER_QUERY = ["api_key", "client_secret"]


def vcr_config() -> vcr_lib.VCR:
    record_mode = "once" if os.environ.get("VCR_RECORD") else "none"
    return vcr_lib.VCR(
        cassette_library_dir=str(CASSETTE_DIR),
        record_mode=record_mode,
        filter_headers=VCR_FILTER_HEADERS,
        filter_query_parameters=VCR_FILTER_QUERY,
        match_on=["method", "scheme", "host", "port", "path", "query", "body"],
        decode_compressed_response=True,
    )
