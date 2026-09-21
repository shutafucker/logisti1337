param(
    [int]$PlanId = 1,
    [string[]]$VehicleIds = @('VAN-01', 'VAN-02', 'VAN-03', 'VAN-04'),
    [string]$Message = 'VAN-02 сломалась'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'

if (-not (Test-Path $Python)) {
    Write-Error 'Backend environment is missing. See README.md.'
}
if (-not $env:AI_API_KEY -or -not $env:AI_MODEL) {
    Write-Error 'Set AI_API_KEY and AI_MODEL in this PowerShell session or root .env before a live check.'
}

$messageBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Message))
$vehicleIdsJson = ConvertTo-Json -Compress -InputObject $VehicleIds
$vehicleIdsBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($vehicleIdsJson))
$command = @"
import base64
import json
from app.agent.provider import OpenAIResponsesProvider
from app.agent.schemas import AgentContext
from app.agent.service import AgentInterpreter
message = base64.b64decode('$messageBase64').decode('utf-8')
vehicle_ids = tuple(json.loads(base64.b64decode('$vehicleIdsBase64').decode('utf-8')))
context = AgentContext(base_plan_id=$PlanId, vehicle_ids=vehicle_ids)
result = AgentInterpreter(OpenAIResponsesProvider.from_environment()).interpret(message, context)
print(result.model_dump_json())
"@

Push-Location $Backend
try {
    Write-Host "Live AI check at $(Get-Date -Format s) with model $env:AI_MODEL"
    & $Python -c $command
} finally {
    Pop-Location
}
