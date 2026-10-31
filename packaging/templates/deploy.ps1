$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:PATH = "$PSScriptRoot\runtimes\node;" + $env:PATH
function Check-Exit($stage) { if ($LASTEXITCODE -ne 0) { throw "$stage failed with exit code $LASTEXITCODE" } }
if (-not (Test-Path '.prepared')) {
    & '.\runtimes\python312\python.exe' deploy.py verify
    Check-Exit 'Archive integrity'
}
& '.\runtimes\python312\python.exe' deploy.py prepare
Check-Exit 'Environment reconstruction'
Set-Content -LiteralPath '.prepared' -Value $PSScriptRoot
$ports = @(15432,16379,16333,16334,17687,17474,19000,19333,19340,18888,11883,1883,5050)
if (-not (Test-Path 'backup/restored.json')) {
    foreach ($port in $ports) {
        if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
            throw "Port $port is occupied. Inspect its owner; do not kill unrelated services. Close its window before first deployment."
        }
    }
}
$env:STRAWBERRY_SKIP_WORKER = '1'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\Newsmart-Strawberry\scripts\windows\services.ps1' start
Check-Exit 'Native services'
& '.\Newsmart-Strawberry\backend\.venv\Scripts\python.exe' deploy.py restore
Check-Exit 'Business database restore'
$env:STRAWBERRY_SKIP_WORKER = $null
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\Newsmart-Strawberry\scripts\windows\services.ps1' start
Check-Exit 'Worker startup'
Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k', ('"' + $PSScriptRoot + '\start-api.cmd"')) -WindowStyle Normal
Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k', ('"' + $PSScriptRoot + '\start-web.cmd"')) -WindowStyle Normal
& '.\Newsmart-Strawberry\backend\.venv\Scripts\python.exe' smoke_test.py
Check-Exit 'Smoke tests'
Write-Host 'Automatic checks passed. Agent must finish browser and feature acceptance in AGENT_DEPLOY.md.'
