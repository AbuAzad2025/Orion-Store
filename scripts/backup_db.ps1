# Backup PostgreSQL volume (staging/prod) — run on host with docker
param(
    [string]$ComposeFile = "01-FOUNDATION/infrastructure/docker-compose.staging.yml",
    [string]$EnvFile = ".env.staging",
    [string]$OutDir = "backups"
)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = Join-Path $OutDir "orion-pg-$stamp.sql"

docker compose --env-file $EnvFile -f $ComposeFile exec -T postgres `
    pg_dump -U azadexa -d azadexa_staging > $out

Write-Host "Backup written to $out"
