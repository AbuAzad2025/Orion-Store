# Backup PostgreSQL (staging/prod) as a custom-format archive for pg_restore.
param(
    [string]$ComposeFile = "01-FOUNDATION/infrastructure/docker-compose.staging.yml",
    [string]$EnvFile = ".env.staging",
    [string]$OutDir = "backups",
    [string]$DbName = "",
    [string]$DbUser = "orion_admin"
)

# DbName resolution: -DbName > $env:POSTGRES_DB > POSTGRES_DB in EnvFile > env default.
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = Join-Path $OutDir "orion-pg-$stamp.dump"

if (-not $DbName) { $DbName = $env:POSTGRES_DB }
if (-not $DbName -and (Test-Path $EnvFile)) {
    foreach ($line in Get-Content $EnvFile) {
        if ($line -match '^\s*POSTGRES_DB\s*=\s*([^\s#]+)') { $DbName = $matches[1]; break }
    }
}
if (-not $DbName) {
    $DbName = if ($EnvFile -match "production") { "orionstore_db" } else { "azadexa_staging" }
}

docker compose --env-file $EnvFile -f $ComposeFile exec -T postgres `
    pg_dump -Fc -U $DbUser -d $DbName > $out
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }

Write-Host "Backup written to $out (custom format — use pg_restore)"
