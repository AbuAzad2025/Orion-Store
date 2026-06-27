# Azadexa local development helpers (Windows PowerShell)
param(
    [ValidateSet(
        "setup-local", "test", "run", "seed", "migrate",
        "docker-up", "docker-down", "docker-test-up", "docker-test-down",
        "docker-staging-up", "docker-staging-down", "docker-prod-up", "docker-prod-down",
        "backup-db", "launch-verify", "start-redis"
    )]
    [string]$Action = "test"
)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONPATH = "02-CORE;03-MODELS;04-SERVICES;05-API;06-STOREFRONT;07-ADMIN"
$env:FLASK_APP = "orion.wsgi:app"

function Import-DotEnv {
    if (-not (Test-Path ".env")) { return }
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $val = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $val, "Process")
        }
    }
}

function Get-TestDatabaseUrl {
    # Docker test DB on 5433; native PostgreSQL uses 5432 + azadexa_test
    $dockerTest = "postgresql://azadexa:azadexa_test@localhost:5433/azadexa_test"
    $nativeTest = "postgresql://azadexa:azadexa_dev@localhost:5432/azadexa_test"
    try {
        python -c "import psycopg2; psycopg2.connect('$dockerTest').close()" 2>$null
        if ($LASTEXITCODE -eq 0) { return $dockerTest }
    } catch { }
    return $nativeTest
}

Import-DotEnv

switch ($Action) {
    "setup-local" {
        & "$PSScriptRoot\setup_local.ps1" @args
    }
    "start-redis" {
        & "$PSScriptRoot\start_redis.ps1" @args
    }
    "seed" {
        $env:FLASK_ENV = "development"
        Import-DotEnv
        python scripts/seed_platform.py
        python scripts/seed_beta.py
    }
    "test" {
        $env:FLASK_ENV = "testing"
        if (-not $env:DATABASE_URL) {
            $env:DATABASE_URL = Get-TestDatabaseUrl
        }
        if (-not $env:ENCRYPTION_KEY) {
            $env:ENCRYPTION_KEY = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        }
        python -m pytest -v -m "not external" --cov --cov-fail-under=85 --cov-report=term-missing --cov-report=json:coverage.json
        if ($LASTEXITCODE -eq 0) {
            python scripts/check_coverage.py --coverage-json coverage.json
        }
    }
    "run" {
        $env:FLASK_ENV = "development"
        Import-DotEnv
        if (-not $env:SECRET_KEY) {
            Write-Error ".env missing — run: .\scripts\dev.ps1 setup-local"
        }
        & "$PSScriptRoot\start_redis.ps1"
        flask run --host 127.0.0.1 --port 5000
    }
    "docker-up" {
        docker compose -f 01-FOUNDATION/infrastructure/docker-compose.dev.yml up -d
    }
    "docker-down" {
        docker compose -f 01-FOUNDATION/infrastructure/docker-compose.dev.yml down
    }
    "docker-test-up" {
        docker compose -f 01-FOUNDATION/infrastructure/docker-compose.test.yml up -d
    }
    "docker-test-down" {
        docker compose -f 01-FOUNDATION/infrastructure/docker-compose.test.yml down
    }
    "docker-staging-up" {
        if (-not (Test-Path ".env.staging")) {
            Copy-Item ".env.staging.example" ".env.staging"
            Write-Host "Created .env.staging — set SECRET_KEY and ENCRYPTION_KEY before production use."
        }
        docker compose --env-file .env.staging -f 01-FOUNDATION/infrastructure/docker-compose.staging.yml up -d --build
    }
    "docker-staging-down" {
        docker compose --env-file .env.staging -f 01-FOUNDATION/infrastructure/docker-compose.staging.yml down
    }
    "docker-prod-up" {
        if (-not (Test-Path ".env.production")) {
            Copy-Item ".env.production.example" ".env.production"
            Write-Host "Created .env.production — set all secrets before go-live."
        }
        docker compose --env-file .env.production -f 01-FOUNDATION/infrastructure/docker-compose.prod.yml up -d --build
    }
    "docker-prod-down" {
        docker compose --env-file .env.production -f 01-FOUNDATION/infrastructure/docker-compose.prod.yml down
    }
    "backup-db" {
        & "$PSScriptRoot\backup_db.ps1"
    }
    "launch-verify" {
        Import-DotEnv
        python scripts/launch_verify.py
    }
    "migrate" {
        $env:FLASK_ENV = "development"
        Import-DotEnv
        flask db upgrade
    }
}
