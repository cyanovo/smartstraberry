$ErrorActionPreference = "Continue"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$classroomEnv = Join-Path $repoRoot "backend\classroom.env"
$nodeHost = ""

foreach ($line in Get-Content -LiteralPath $classroomEnv) {
    $trimmed = $line.Trim()
    if ($trimmed.StartsWith("CLASSROOM_NODE_HOST=")) {
        $nodeHost = $trimmed.Substring("CLASSROOM_NODE_HOST=".Length).Trim()
        break
    }
}
if (-not $nodeHost -or $nodeHost -eq "CHANGE_ME") {
    Write-Host "[FAIL] Edit CLASSROOM_NODE_HOST in: $classroomEnv" -ForegroundColor Red
    exit 1
}

$failed = $false
foreach ($service in @(
    @{ Name = "PostgreSQL"; Port = 5432 },
    @{ Name = "Redis"; Port = 6379 },
    @{ Name = "MinIO"; Port = 9000 },
    @{ Name = "Milvus"; Port = 19530 },
    @{ Name = "Neo4j"; Port = 7687 },
    @{ Name = "Sandbox"; Port = 8002 }
)) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connected = $client.ConnectAsync($nodeHost, $service.Port).Wait(1500) -and $client.Connected
    } catch {
        $connected = $false
    } finally {
        $client.Dispose()
    }
    if ($connected) {
        Write-Host "[OK]   $($service.Name) - $nodeHost`:$($service.Port)" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $($service.Name) - $nodeHost`:$($service.Port)" -ForegroundColor Red
        $failed = $true
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $repoRoot "backend\.venv\Scripts\python.exe"))) {
    Write-Host "[FAIL] Backend is not ready. Run student-compile.cmd." -ForegroundColor Red
    $failed = $true
}
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot "web\node_modules"))) {
    Write-Host "[FAIL] Frontend is not ready. Run student-compile.cmd." -ForegroundColor Red
    $failed = $true
}

if ($failed) { exit 1 }
Write-Host "Student environment check passed." -ForegroundColor Green
