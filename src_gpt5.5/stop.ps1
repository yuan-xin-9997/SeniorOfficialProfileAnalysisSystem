param(
    [string]$AppDir = "",
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

if (-not (Test-Path $PidFile)) { Write-Host "Application is not running."; exit 0 }
$ProcessId = [int](Get-Content $PidFile -Raw)
$Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
if ($Process) {
    Stop-Process -Id $ProcessId -Force
    $Process.WaitForExit(15000) | Out-Null
}
Remove-Item $PidFile, $PortFile -Force -ErrorAction SilentlyContinue
Write-Host "Application stopped."
