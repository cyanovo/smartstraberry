$ErrorActionPreference = "Stop"

. (Join-Path (Get-Location) "classroom-settings.ps1")

$localSettings = Join-Path (Get-Location) "classroom-settings.local.ps1"
if (Test-Path $localSettings) {
    . $localSettings
}

$hostInput = Read-Host "Enter registry host, or press Enter for $TeacherHost"
if (-not [string]::IsNullOrWhiteSpace($hostInput)) {
    $TeacherHost = $hostInput.Trim()
    $ClassroomDockerRegistry = "$TeacherHost`:5000"

    @"
`$TeacherHost = "$TeacherHost"
`$ClassroomGitRepo = "http://`$TeacherHost`:3080/admin/tomatosmart.git"
`$ClassroomDockerRegistry = "`$TeacherHost`:5000"
`$ClassroomBranch = "$ClassroomBranch"
"@ | Set-Content -Path $localSettings -Encoding UTF8
}

$registry = $ClassroomDockerRegistry

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.template") {
        Copy-Item ".env.template" ".env"
        Write-Host "Created .env from .env.template."
    }
    else {
        throw ".env or .env.template was not found."
    }
}

$env:LOCAL_DOCKER_REGISTRY = $registry

Write-Host "Using registry: $registry"
Write-Host "Pulling project images..."
docker compose -f docker-compose.yml -f docker-compose.registry.yml pull

Write-Host "Starting services with --no-build..."
docker compose -f docker-compose.yml -f docker-compose.registry.yml up -d --no-build

Write-Host ""
Write-Host "Done."
Write-Host "Web: http://localhost:5173"
Write-Host "API health: http://localhost:5050/api/system/health"
