param(
  [string]$EnvFile = ".env.production",
  [string]$ComposeFile = "01-FOUNDATION/infrastructure/docker-compose.prod.yml"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Fail($msg) { Write-Error "NO-GO: $msg"; exit 1 }

Write-Host "== Orion deployment preflight ==" -ForegroundColor Cyan

if (-not (Test-Path $EnvFile)) { Fail "missing $EnvFile (copy .env.production.example)" }

$envValues = @{}
foreach ($line in Get-Content $EnvFile) {
  if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
  $parts = $line -split '=', 2
  $envValues[$parts[0].Trim()] = $parts[1].Trim().Trim('"')
}

$required = @(
  "POSTGRES_PASSWORD", "POSTGRES_APP_PASSWORD", "SECRET_KEY",
  "JWT_SECRET_KEY", "ENCRYPTION_KEY"
)
foreach ($key in $required) {
  $value = $envValues[$key]
  if (-not $value -or $value -like "CHANGE_ME*") { Fail "$key is missing or placeholder" }
}
Write-Host "OK  secrets are set" -ForegroundColor Green

$certDir = "01-FOUNDATION/infrastructure/certs"
foreach ($cert in @("fullchain.pem", "privkey.pem")) {
  if (-not (Test-Path (Join-Path $certDir $cert))) { Fail "TLS certificate missing: $certDir/$cert" }
}
Write-Host "OK  TLS certificate files present" -ForegroundColor Green

if (-not (Test-Path $ComposeFile)) { Fail "missing $ComposeFile" }
Write-Host "OK  production compose file present" -ForegroundColor Green

Write-Host "-> pre-commit gates" -ForegroundColor Cyan
python -m pre_commit run --all-files
if ($LASTEXITCODE -ne 0) { Fail "pre-commit failed" }

Write-Host "-> migration/model check" -ForegroundColor Cyan
python scripts/check_migrations.py
if ($LASTEXITCODE -ne 0) { Fail "migration/model drift" }

Write-Host "-> CSS build reproducibility" -ForegroundColor Cyan
npm run build:css | Out-Null
git diff --exit-code -- 06-STOREFRONT/themes/default/static/css 07-ADMIN/static/css
if ($LASTEXITCODE -ne 0) { Fail "committed CSS is stale; commit npm run build:css output" }

Write-Host "`nGO: static preflight passed." -ForegroundColor Green
Write-Host "Next: docker compose --env-file $EnvFile -f $ComposeFile up -d --build"
Write-Host "Then: python scripts/verify_deployment_rls.py --check  (must report 0 issues)"
