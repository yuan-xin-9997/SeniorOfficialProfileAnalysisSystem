param(
    [string]$AppDir = "",
    [ValidateRange(0, 65535)][int]$Port = 0,
    [string]$DataDir = "",
    [string]$PythonExecutable = ""
)

$ErrorActionPreference = "Stop"
if (-not $AppDir) { $AppDir = if ($env:APP_DIR) { $env:APP_DIR } else { $PSScriptRoot } }
$AppDir = [IO.Path]::GetFullPath($AppDir)
if (-not $PythonExecutable) {
    $PythonExecutable = if ($env:PYTHON_EXECUTABLE) { $env:PYTHON_EXECUTABLE } else {
        Join-Path $AppDir ".venv\Scripts\python.exe"
    }
}
if (-not $DataDir) {
    if ($env:DATA_DIR) {
        $DataDir = $env:DATA_DIR
    } elseif (Test-Path $PythonExecutable) {
        $env:PYTHONPATH = Join-Path $AppDir "backend"
        Push-Location $AppDir
        try { $DataDir = (& $PythonExecutable -c "from app.core.config import settings; print(settings.DATA_DIR)").Trim() }
        finally { Pop-Location }
    } else {
        $DataDir = "data"
    }
}
if (-not [IO.Path]::IsPathRooted($DataDir)) { $DataDir = Join-Path $AppDir $DataDir }
$PidFile = Join-Path $DataDir "app.pid"
$PortFile = Join-Path $DataDir "app.port"
if ($Port -eq 0) {
    if (Test-Path $PortFile) {
        $Port = [int](Get-Content $PortFile -Raw)
    } elseif ($env:APP_PORT) {
        $Port = [int]$env:APP_PORT
    } elseif (Test-Path $PythonExecutable) {
        $env:PYTHONPATH = Join-Path $AppDir "backend"
        Push-Location $AppDir
        try { $Port = [int](& $PythonExecutable -c "from app.core.config import settings; print(settings.APP_PORT)").Trim() }
        finally { Pop-Location }
    } else {
        throw "Cannot determine application port. Pass -Port or set APP_PORT."
    }
}

if (-not (Test-Path $PidFile)) { Write-Host "Application is not running."; exit 1 }
$ProcessId = [int](Get-Content $PidFile -Raw)
if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
    Write-Host "Application is not running; PID file is stale."
    exit 1
}
try {
    $Health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
    $Health | ConvertTo-Json -Compress
    Write-Host "Application is running on port $Port (PID $ProcessId)."
    exit 0
} catch {
    Write-Host "Process $ProcessId exists, but health check on port $Port failed."
    exit 1
}
