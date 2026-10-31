$ErrorActionPreference = 'Stop'
$pairs = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'pending-links.json') -Raw | ConvertFrom-Json
foreach ($pair in $pairs) {
    if (-not (Test-Path -LiteralPath $pair[0])) {
        New-Item -ItemType Junction -Path $pair[0] -Target $pair[1] | Out-Null
    }
}
