param(
    [string]$AppDir = "",
    [ValidateRange(0, 65535)][int]$Port = 0,
    [string]$DataDir = "",
    [string]$LogDir = "",
    [string]$FrontendDistDir = "",
    [string]$PythonExecutable = ""
)

$ErrorActionPreference = "Stop"
if (-not $AppDir) { $AppDir = if ($env:APP_DIR) { $env:APP_DIR } else { $PSScriptRoot } }
$AppDir = [IO.Path]::GetFullPath($AppDir)
if (-not $PythonExecutable) {
    $PythonExecutable = if ($env:PYTHON_EXECUTABLE) {
        $env:PYTHON_EXECUTABLE
    } else {
        Join-Path $AppDir ".venv\Scripts\python.exe"
    }
}
if (-not (Test-Path $PythonExecutable)) { throw "Python environment not found: $PythonExecutable" }

$PreviousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = Join-Path $AppDir "backend"
function Get-AppSetting([string]$Name) {
    Push-Location $AppDir
    try { (& $PythonExecutable -c "from app.core.config import settings; print(settings.$Name)").Trim() }
    finally { Pop-Location }
}
function Resolve-AppPath([string]$PathValue) {
    if ([IO.Path]::IsPathRooted($PathValue)) { return [IO.Path]::GetFullPath($PathValue) }
    return [IO.Path]::GetFullPath((Join-Path $AppDir $PathValue))
}

if ($Port -eq 0) { $Port = [int](Get-AppSetting "APP_PORT") }
if (-not $DataDir) { $DataDir = if ($env:DATA_DIR) { $env:DATA_DIR } else { Get-AppSetting "DATA_DIR" } }
if (-not $LogDir) { $LogDir = if ($env:LOG_DIR) { $env:LOG_DIR } else { Get-AppSetting "LOG_DIR" } }
if (-not $FrontendDistDir) {
    $FrontendDistDir = if ($env:FRONTEND_DIST_DIR) {
        $env:FRONTEND_DIST_DIR
    } else {
        Get-AppSetting "FRONTEND_DIST_DIR"
    }
}
$DataDir = Resolve-AppPath $DataDir
$LogDir = Resolve-AppPath $LogDir
$FrontendDistDir = Resolve-AppPath $FrontendDistDir
$PidFile = Join-Path $DataDir "app.pid"
$PortFile = Join-Path $DataDir "app.port"

New-Item -ItemType Directory -Path $DataDir, $LogDir -Force | Out-Null
if (Test-Path $PidFile) {
    $ExistingPid = [int](Get-Content $PidFile -Raw)
    if (Get-Process -Id $ExistingPid -ErrorAction SilentlyContinue) {
        Write-Host "Application is already running (PID $ExistingPid)."
        exit 0
    }
    Remove-Item $PidFile -Force
}

$FrontendIndex = Join-Path $FrontendDistDir "index.html"
if (-not (Test-Path $FrontendIndex)) {
    throw "Vue build not found: $FrontendIndex. Run npm run build in frontend first."
}

$ExistingListener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($ExistingListener) { throw "Port $Port is already in use by PID $($ExistingListener.OwningProcess)." }

$env:APP_PORT = [string]$Port
$env:DATA_DIR = $DataDir
$env:LOG_DIR = $LogDir
$env:FRONTEND_DIST_DIR = $FrontendDistDir
$RunScript = Join-Path $AppDir "backend\run.py"
$Process = Start-Process `
    -FilePath $PythonExecutable `
    -ArgumentList "`"$RunScript`"" `
    -WorkingDirectory $AppDir `
    -WindowStyle Hidden `
    -PassThru

$Process.Id | Set-Content -Path $PidFile -NoNewline
$Port | Set-Content -Path $PortFile -NoNewline
for ($Attempt = 1; $Attempt -le 30; $Attempt++) {
    try {
        $Health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2
        if ($Health.status -eq "ok") {
            $Listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($Listener) { $Listener.OwningProcess | Set-Content -Path $PidFile -NoNewline }
            Write-Host "Application started on port $Port (PID $(Get-Content $PidFile -Raw))."
            $env:PYTHONPATH = $PreviousPythonPath
            exit 0
        }
    } catch { Start-Sleep -Seconds 1 }
}

Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
Remove-Item $PidFile, $PortFile -Force -ErrorAction SilentlyContinue
$env:PYTHONPATH = $PreviousPythonPath
Write-Error "Application did not become healthy. Check $LogDir\app.log."
exit 1
