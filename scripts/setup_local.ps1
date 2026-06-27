# Azadexa - one-shot local development setup (Windows)
# Provisions PostgreSQL (native or Docker), Redis, .env, migrations, and seed data.
param(
    [switch]$SkipSeed,
    [switch]$SkipMigrate,
    [string]$PostgresHost = "localhost",
    [int]$PostgresPort = 5432,
    [string]$PostgresSuperuser = "postgres"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONPATH = "02-CORE;03-MODELS;04-SERVICES;05-API;06-STOREFRONT;07-ADMIN"
$env:FLASK_APP = "orion.wsgi:app"

function Find-Psql {
    $cmd = Get-Command psql -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "C:\Program Files\PostgreSQL\18\bin\psql.exe",
        "C:\Program Files\PostgreSQL\17\bin\psql.exe",
        "C:\Program Files\PostgreSQL\16\bin\psql.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    return $null
}

function New-Secret {
    param([int]$Bytes = 32)
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $buf = New-Object byte[] $Bytes
    $rng.GetBytes($buf)
    return ([BitConverter]::ToString($buf) -replace "-", "").ToLower()
}

Write-Host "=== Azadexa local setup ==="

# 1. PostgreSQL role + databases
Write-Host "Provisioning PostgreSQL user and databases..."
$psql = Find-Psql
if (-not $psql) {
    throw "psql not found. Install PostgreSQL 16+ or run: .\scripts\dev.ps1 docker-up"
}
$sqlFile = Join-Path $PSScriptRoot "provision_postgres.sql"
& $psql -U $PostgresSuperuser -h $PostgresHost -p $PostgresPort -v ON_ERROR_STOP=1 -f $sqlFile

# 2. .env
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    $encKey = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    $secret = New-Secret
    $jwt = New-Secret
    $content = Get-Content ".env" -Raw
    $content = $content -replace "SECRET_KEY=.*", "SECRET_KEY=$secret"
    $content = $content -replace "JWT_SECRET_KEY=.*", "JWT_SECRET_KEY=$jwt"
    $content = $content -replace "ENCRYPTION_KEY=.*", "ENCRYPTION_KEY=$encKey"
    $content = $content -replace "DATABASE_URL=.*", "DATABASE_URL=postgresql://azadexa:azadexa_dev@localhost:5432/azadexa_dev"
    $content = $content -replace "REDIS_URL=.*", "REDIS_URL=redis://localhost:6379/0"
    if ($content -notmatch "CELERY_TASK_ALWAYS_EAGER") {
        $content += "`nCELERY_TASK_ALWAYS_EAGER=true`n"
    }
    Set-Content ".env" $content -NoNewline
    Write-Host ".env created with generated secrets."
} else {
    Write-Host ".env already exists - skipping."
}

# Load .env into process
Get-Content ".env" | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $val = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($name, $val, "Process")
    }
}

# 3. Python deps
Write-Host "Installing Python dependencies..."
pip install -r requirements.txt -q 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "pip install had warnings - checking core imports..."
    python -c "import flask, psycopg2, redis, celery" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Missing Python dependencies" }
}
pip install pytest pytest-cov black isort flake8 -q 2>$null

# 4. Redis
& "$PSScriptRoot\start_redis.ps1"

# 5. Migrations
if (-not $SkipMigrate) {
    Write-Host "Running database migrations..."
    $env:FLASK_ENV = "development"
    flask db upgrade
    if ($LASTEXITCODE -ne 0) { throw "flask db upgrade failed" }
}

# 6. Seed
if (-not $SkipSeed) {
    Write-Host "Seeding platform settings..."
    python scripts/seed_platform.py
    Write-Host "Seeding beta tenants..."
    python scripts/seed_beta.py
}

Write-Host ""
Write-Host "=== Local setup complete ==="
Write-Host "  Dev DB:  postgresql://azadexa:azadexa_dev@localhost:5432/azadexa_dev"
Write-Host "  Test DB: postgresql://azadexa:azadexa_dev@localhost:5432/azadexa_test"
Write-Host "  Run API: .\scripts\dev.ps1 run"
Write-Host "  Tests:   .\scripts\dev.ps1 test"
Write-Host "  Verify:  .\scripts\dev.ps1 launch-verify"
