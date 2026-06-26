# Azadexa local development helpers (Windows PowerShell)
param(
    [ValidateSet("test", "run", "docker-up", "docker-down", "migrate")]
    [string]$Action = "test"
)

$env:PYTHONPATH = "02-CORE;03-MODELS;04-SERVICES;05-API"
$env:FLASK_APP = "orion.wsgi:app"

switch ($Action) {
    "test" {
        $env:FLASK_ENV = "testing"
        if (-not $env:ENCRYPTION_KEY) {
            $env:ENCRYPTION_KEY = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        }
        python -m pytest -v
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
    "migrate" {
        flask db upgrade
    }
}
