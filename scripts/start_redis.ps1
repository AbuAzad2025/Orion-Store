# Start Redis-compatible server locally (portable or Windows service).
param(
    [int]$Port = 6379
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$LocalRedis = Join-Path $Root ".local\redis"
$RedisExe = Join-Path $LocalRedis "redis-server.exe"
$PidFile = Join-Path $LocalRedis "redis.pid"

function Test-RedisPort {
    $cli = Join-Path $LocalRedis "redis-cli.exe"
    if (Test-Path $cli) {
        $out = & $cli -p $Port ping 2>$null
        return $out -eq "PONG"
    }
    try {
        python -c "import redis; r=redis.from_url('redis://127.0.0.1:$Port/0', socket_connect_timeout=1); r.ping()" 2>$null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}

if (Test-RedisPort) {
    Write-Host "Redis already running on port $Port"
    exit 0
}

foreach ($svcName in @("Memurai", "redis")) {
    $svc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq "Stopped") {
        Start-Service $svcName
        Start-Sleep -Seconds 2
        if (Test-RedisPort) { exit 0 }
    }
}

if (-not (Test-Path $RedisExe)) {
    Write-Host "Downloading portable Redis for Windows..."
    New-Item -ItemType Directory -Force -Path $LocalRedis | Out-Null
    $zipUrl = "https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip"
    $zipPath = Join-Path $env:TEMP "redis-portable.zip"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $LocalRedis -Force
    Remove-Item $zipPath -Force
}

if (-not (Test-Path $RedisExe)) {
    Write-Error "redis-server.exe not found. Install Memurai or run as Administrator: choco install redis-64 -y"
}

$conf = Join-Path $LocalRedis "redis.custom.conf"
@"
port $Port
bind 127.0.0.1
save ""
appendonly no
"@ | Set-Content $conf -Encoding ASCII

Start-Process -FilePath $RedisExe -ArgumentList $conf -WorkingDirectory $LocalRedis -WindowStyle Hidden
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 1
    if (Test-RedisPort) {
        Write-Host "Redis started on 127.0.0.1:$Port"
        exit 0
    }
}
Write-Error "Failed to start Redis on port $Port"
