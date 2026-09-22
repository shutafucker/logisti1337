param(
    [string]$ApiBaseUrl = 'http://127.0.0.1:8000',
    [string]$Message = 'VAN-02 сломалась'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'

if (-not (Test-Path $Python)) {
    Write-Error 'Backend environment is missing. See README.md.'
}
$messageBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Message))
$dashboard = Invoke-RestMethod -Uri "$($ApiBaseUrl.TrimEnd('/'))/dashboard" -Method Get
if (-not $dashboard.route_plan.id -or -not $dashboard.route_plan.routes) {
    Write-Error 'Dashboard did not return a current route plan with routes.'
}
$currentPlanId = 0
if (-not [int]::TryParse([string]$dashboard.route_plan.id, [ref]$currentPlanId) -or $currentPlanId -le 0) {
    Write-Error 'Dashboard route plan ID is invalid.'
}
$currentVehicleIds = @($dashboard.route_plan.routes | ForEach-Object { $_.vehicle_external_id })
if ($currentVehicleIds.Count -eq 0) {
    Write-Error 'Dashboard current plan has no routed vehicle IDs.'
}
$vehicleIdsJson = ConvertTo-Json -Compress -InputObject $currentVehicleIds
$vehicleIdsBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($vehicleIdsJson))
$rootPathBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Root))
$planIdBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string]$currentPlanId))
$command = @"
import base64
import json
from pathlib import Path
from dotenv import load_dotenv
from app.agent.provider import OpenAIResponsesProvider
from app.agent.schemas import AgentContext
from app.agent.service import AgentInterpreter
message = base64.b64decode('$messageBase64').decode('utf-8')
vehicle_ids = tuple(json.loads(base64.b64decode('$vehicleIdsBase64').decode('utf-8')))
root = Path(base64.b64decode('$rootPathBase64').decode('utf-8'))
load_dotenv(root / '.env')
plan_id = int(base64.b64decode('$planIdBase64').decode('utf-8'))
context = AgentContext(base_plan_id=plan_id, vehicle_ids=vehicle_ids)
result = AgentInterpreter(OpenAIResponsesProvider.from_environment()).interpret(message, context)
print(result.model_dump_json())
"@

Push-Location $Backend
try {
    Write-Host "Live AI check at $(Get-Date -Format s) using current plan $currentPlanId and $($currentVehicleIds.Count) routed vehicle IDs."
    & $Python -c $command
} finally {
    Pop-Location
}
