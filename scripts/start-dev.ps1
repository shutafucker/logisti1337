param(
    [int]$ApiPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'

function Test-PortAvailable([int]$Port) {
    return -not (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

if (-not (Test-Path $Python)) {
    Write-Error "Backend environment is missing. Run: cd backend; py -3.14 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e '.[dev]'"
}
if (-not (Test-Path (Join-Path $Frontend 'node_modules'))) {
    Write-Error "Frontend dependencies are missing. Run: cd frontend; npm install"
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    Write-Error 'npm.cmd is not available in PATH.'
}
if (-not (Test-PortAvailable $ApiPort)) {
    Write-Error "API port $ApiPort is already in use. Existing process was not changed."
}
if (-not (Test-PortAvailable $FrontendPort)) {
    Write-Error "Frontend port $FrontendPort is already in use. Existing process was not changed."
}

$api = Start-Process -FilePath $Python -WorkingDirectory $Backend -PassThru -ArgumentList @(
    '-m', 'uvicorn', 'app.main:app', '--reload', '--host', '127.0.0.1', '--port', $ApiPort
)
$web = Start-Process -FilePath 'npm.cmd' -WorkingDirectory $Frontend -PassThru -ArgumentList @(
    'run', 'dev', '--', '--host', '127.0.0.1', '--port', $FrontendPort
)

Write-Host "API:      http://127.0.0.1:$ApiPort"
Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
Write-Host "Started backend PID $($api.Id) and frontend PID $($web.Id)."
Write-Host "To stop only these processes: Stop-Process -Id $($api.Id),$($web.Id)"
Write-Host "Logs and runtime errors appear in the two started process windows."
