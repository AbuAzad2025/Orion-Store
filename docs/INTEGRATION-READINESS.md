# Integration readiness report — payment adapters + SMTP

This is a configuration-only, fail-closed report. It makes no HTTP calls, no
DB queries and never reads or decrypts credentials.

Run: `python scripts/check_integration_readiness.py` (default: WhatsApp-only).
Use `--strict` for a CI GO/NO-GO gate; `--json` for machine-readable output.

Every missing variable is printed by name (`MISSING <NAME>`). A declared or
forced integration with missing env is `NO-GO` (exit 1). The default empty
environment remains `GO` with `operating_model: whatsapp_only`, because free
`wa.me` deep links require no provider account.

Payment env: PAYMENT_LIVE_CALLS_ENABLED, PAYMENT_STUB_ALLOWED, ENCRYPTION_KEY,
WEBHOOK_SECRET. Optional endpoint overrides: PAYPAL_API_BASE_URL,
PALPAY_API_BASE_URL, BNPL_API_BASE_URL. Gateway credentials are encrypted in the
DB and out of scope. SMTP env: SMTP_HOST, SMTP_PORT, SMTP_FROM; SMTP_USER and
SMTP_PASSWORD must be both set or both unset.
