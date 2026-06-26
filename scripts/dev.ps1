# Azadexa local development helpers (Windows PowerShell)
param(
    [ValidateSet("test", "run", "docker-up", "docker-down", "docker-test-up", "docker-test-down", "migrate")]
    [string]$Action = "test"
)

$env:PYTHONPATH = "02-CORE;03-MODELS;04-SERVICES;05-API"
$env:FLASK_APP = "orion.wsgi:app"
$DefaultTestDb = "postgresql://azadexa:azadexa_test@localhost:5433/azadexa_test"

switch ($Action) {
    "test" {
        $env:FLASK_ENV = "testing"
        if (-not $env:DATABASE_URL) {
            $env:DATABASE_URL = $DefaultTestDb
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
        flask run
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
    "migrate" {
        flask db upgrade
    }
}
