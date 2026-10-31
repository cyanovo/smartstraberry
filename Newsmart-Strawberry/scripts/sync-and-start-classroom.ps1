$ErrorActionPreference = "Stop"

. (Join-Path (Get-Location) "classroom-settings.ps1")

$localSettings = Join-Path (Get-Location) "classroom-settings.local.ps1"
if (Test-Path $localSettings) {
    . $localSettings
}

$hostInput = Read-Host "Enter classroom node host, or press Enter for $TeacherHost"
if (-not [string]::IsNullOrWhiteSpace($hostInput)) {
    $TeacherHost = $hostInput.Trim()
    $ClassroomGitRepo = "http://$TeacherHost`:3080/admin/tomatosmart.git"
    $ClassroomDockerRegistry = "$TeacherHost`:5000"

    @"
`$TeacherHost = "$TeacherHost"
`$ClassroomGitRepo = "http://`$TeacherHost`:3080/admin/tomatosmart.git"
`$ClassroomDockerRegistry = "`$TeacherHost`:5000"
`$ClassroomBranch = "$ClassroomBranch"
"@ | Set-Content -Path $localSettings -Encoding UTF8
}

Write-Host "Classroom Git repo: $ClassroomGitRepo"
Write-Host "Classroom Docker registry: $ClassroomDockerRegistry"
Write-Host ""

if (-not (Test-Path ".git")) {
    throw "This folder is not a Git repository. Clone from $ClassroomGitRepo first."
}

Write-Host "Syncing latest source code..."
$remoteNames = git remote
if ($remoteNames -contains "classroom") {
    git remote set-url classroom $ClassroomGitRepo
}
else {
    git remote add classroom $ClassroomGitRepo
}

git fetch classroom
git reset --hard "classroom/$ClassroomBranch"

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.template") {
        Copy-Item ".env.template" ".env"
    }
    else {
        throw ".env or .env.template was not found."
    }
}

$env:LOCAL_DOCKER_REGISTRY = $ClassroomDockerRegistry

Write-Host "Pulling images from classroom registry..."
docker compose -f docker-compose.yml -f docker-compose.registry.yml pull

Write-Host "Starting services with --no-build..."
docker compose -f docker-compose.yml -f docker-compose.registry.yml up -d --no-build

Write-Host ""
Write-Host "Done."
Write-Host "Web: http://localhost:5173"
Write-Host "API health: http://localhost:5050/api/system/health"
