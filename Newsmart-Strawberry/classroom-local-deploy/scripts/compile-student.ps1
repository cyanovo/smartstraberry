$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

& py -3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.12 x64 is required." }

$nodeMajor = [int]((& node --version).TrimStart("v").Split(".")[0])
if ($nodeMajor -lt 24) { throw "Node.js 24 or newer is required." }

& py -3.12 -m pip install --user "uv==0.7.2"
if ($LASTEXITCODE -ne 0) { throw "Failed to install uv." }

Push-Location (Join-Path $repoRoot "backend")
try {
    & py -3.12 -m uv sync --frozen
    if ($LASTEXITCODE -ne 0) { throw "Failed to install backend dependencies." }
} finally {
    Pop-Location
}

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    & npm install --global "pnpm@10.11.0"
    if ($LASTEXITCODE -ne 0) { throw "Failed to install pnpm." }
}

Push-Location (Join-Path $repoRoot "web")
try {
    & pnpm install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw "Failed to install frontend dependencies." }
    & pnpm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
} finally {
    Pop-Location
}

Write-Host "Backend dependencies and frontend production build are ready." -ForegroundColor Green
