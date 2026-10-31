param([Parameter(Mandatory = $true)][string]$Config)
$ErrorActionPreference = 'Stop'
try {
    $service = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
    $Host.UI.RawUI.WindowTitle = "Strawberry - $($service.name)"
    Set-Location -LiteralPath $service.cwd
    Write-Host "Running $($service.name) in this window. Close this window to stop it."
    $exe = $service.exe
    $arguments = @($service.arguments)
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "$($service.name) exited with code $LASTEXITCODE" }
} catch {
    Write-Host $_ -ForegroundColor Red
    Read-Host 'Service failed. Press Enter to close'
    exit 1
}
