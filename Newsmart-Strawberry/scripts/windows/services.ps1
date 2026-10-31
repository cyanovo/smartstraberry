param([ValidateSet('start', 'stop', 'check', 'restart-mqtt')][string]$Action = 'start')
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runtime = Join-Path $root '.runtime'
$logs = Join-Path $runtime 'logs'
$data = Join-Path $runtime 'data'
$pg = Join-Path $runtime 'pgsql/bin'
$python = Join-Path $root 'backend/.venv/Scripts/python.exe'
function Assert-Exit($label) { if ($LASTEXITCODE -ne 0) { throw "$label failed ($LASTEXITCODE)" } }
function Test-Port([int]$port) {
    $client = New-Object Net.Sockets.TcpClient
    try { $task = $client.ConnectAsync('127.0.0.1', $port); return ($task.Wait(500) -and $client.Connected) }
    catch { return $false } finally { $client.Dispose() }
}
function Start-Owned($name, $exe, $arguments, $cwd, $port = 0) {
    $record = Join-Path $runtime "$name.process.json"
    if (Test-Path -LiteralPath $record) {
        $saved = Get-Content -LiteralPath $record -Raw | ConvertFrom-Json
        $process = Get-Process -Id $saved.id -ErrorAction SilentlyContinue
        if ($process -and $process.StartTime.ToUniversalTime().Ticks.ToString() -eq $saved.started -and $process.Path -eq $saved.exe) {
            Write-Host "$name already running"
            return
        }
    }
    $config = Join-Path $runtime "$name.console.json"
    $existing = Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object {
        $_.CommandLine -and $_.CommandLine.Contains('run-service.ps1') -and $_.CommandLine.Contains($config)
    }
    if ($existing) { Write-Host "$name window already open"; return }
    if ($port -and (Test-Port $port)) { throw "Port $port belongs to another service. Close its window before retrying." }
    $plainArguments = @($arguments | ForEach-Object { $_.Replace('"', '') })
    @{ name = $name; exe = $exe; arguments = $plainArguments; cwd = $cwd } |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $config -Encoding UTF8
    Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        ('"' + (Join-Path $PSScriptRoot 'run-service.ps1') + '"'), '-Config', ('"' + $config + '"')
    ) -WorkingDirectory $cwd -WindowStyle Normal | Out-Null
    Write-Host "$name opened in its own console"
}
function Stop-Owned($name, $redisCli = '') {
    $record = Join-Path $runtime "$name.process.json"
    if (-not (Test-Path -LiteralPath $record)) { return }
    $saved = Get-Content -LiteralPath $record -Raw | ConvertFrom-Json
    $process = Get-Process -Id $saved.id -ErrorAction SilentlyContinue
    if ($process -and $process.StartTime.ToUniversalTime().Ticks.ToString() -eq $saved.started -and $process.Path -eq $saved.exe) {
        if ($redisCli) {
            & $redisCli -h 127.0.0.1 -p 16379 shutdown save
            Assert-Exit 'Redis shutdown'
        } else {
            Get-CimInstance Win32_Process -Filter "ParentProcessId = $($process.Id)" | ForEach-Object {
                if ($_.ExecutablePath -and $_.Name -eq 'python.exe') { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
            }
            Stop-Process -Id $process.Id
        }
    }
    Remove-Item -LiteralPath $record
}
if ($Action -eq 'restart-mqtt') {
    Stop-Owned 'mqtt'
    if ((Test-Port 11883) -or (Test-Port 1883)) { throw 'Close the Strawberry - mqtt console first, then retry restart-mqtt.' }
    New-Item -ItemType Directory -Force -Path $logs | Out-Null
    Start-Owned 'mqtt' (Join-Path $PSScriptRoot '.venv/Scripts/python.exe') @('"' + (Join-Path $PSScriptRoot 'mqtt_broker.py') + '"') $root 11883
    for ($i = 0; $i -lt 40; $i++) {
        if ((Test-Port 11883) -and (Test-Port 1883)) { break }
        Start-Sleep -Seconds 1
    }
    if (-not (Test-Port 11883) -or -not (Test-Port 1883)) { throw 'MQTT listeners failed. Check the Strawberry - mqtt console.' }
    Write-Host 'MQTT restarted: backend 11883, local-subnet hardware 1883 (credentials ignored).'
    exit 0
}
if ($Action -eq 'stop') {
    Stop-Owned 'worker'
    Stop-Owned 'embedding'
    Stop-Owned 'neo4j'
    Stop-Owned 'qdrant'
    Stop-Owned 'mqtt'
    Stop-Owned 'storage'
    $redisCli = Get-ChildItem "$runtime/redis" -Recurse -Filter redis-cli.exe | Select-Object -First 1
    if ($redisCli) { Stop-Owned 'redis' $redisCli.FullName }
    if (Test-Path "$data/postgres/postmaster.pid") {
        & "$pg/pg_ctl.exe" -D "$data/postgres" stop -m fast -w
        Assert-Exit 'PostgreSQL shutdown'
    }
    Write-Host 'Legacy background services stopped. Close the individual Strawberry service consoles to stop foreground services.'
    exit 0
}
if ($Action -eq 'start') {
    foreach ($dir in @($logs, $data, "$data/redis", "$data/storage")) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    if (-not (Test-Path "$pg/initdb.exe")) { throw 'Run setup-services.cmd first' }
    if (-not (Test-Path $python)) { throw 'Create backend/.venv with Python 3.12 first' }
    if (-not (Test-Path "$runtime/local.env")) {
        $secret = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
        $password = [guid]::NewGuid().ToString('N')
        @"
LOCAL_WINDOWS_MODE=true
RUNNING_IN_DOCKER=false
CLASSROOM_MODE=false
GREENHOUSE_ENV=development
GREENHOUSE_INSTANCE_ID=windows-local
JWT_SECRET_KEY=$secret
POSTGRES_URL=postgresql+asyncpg://postgres:$password@127.0.0.1:15432/strawberry
REDIS_URL=redis://127.0.0.1:16379/0
RUN_QUEUE_NAME=arq:queue:windows-local
LITE_MODE=true
LANGGRAPH_CHECKPOINTER_BACKEND=postgres
TRACE_DATABASE_BACKEND=postgres
TRACE_DATABASE_SCHEMA_MODE=migrate
DATABASE_SCHEMA_MODE=migrate
MINIO_URI=http://127.0.0.1:19000
MINIO_PUBLIC_ENDPOINT=127.0.0.1:19000
MINIO_ACCESS_KEY=localadmin
MINIO_SECRET_KEY=$secret
MQTT_ENABLED=true
MQTT_PROTOCOL=strawberry
MQTT_BROKER_URL=127.0.0.1
MQTT_BROKER_PORT=11883
MQTT_BROKER_USERNAME=
MQTT_BROKER_PASSWORD=
MQTT_TOPIC_ROOT=tomato_hnsw0001
CAMERA_ENABLED=false
PYTHONUTF8=1
"@ | Set-Content -LiteralPath "$runtime/local.env" -Encoding ASCII
    }
    $settings = @{}
    foreach ($line in Get-Content "$runtime/local.env") {
        if ($line -match '^([^#=]+)=(.*)$') { $settings[$matches[1]] = $matches[2] }
    }
    foreach ($pair in @(@('QDRANT_URL', 'http://127.0.0.1:16333'), @('NEO4J_URI', 'bolt://127.0.0.1:17687'), @('NEO4J_USERNAME', 'neo4j'), @('NEO4J_PASSWORD', [guid]::NewGuid().ToString('N')))) {
        if (-not $settings.ContainsKey($pair[0])) {
            $settings[$pair[0]] = $pair[1]
            Add-Content -LiteralPath "$runtime/local.env" -Value "$($pair[0])=$($pair[1])" -Encoding ASCII
        }
    }
    $env:PGPASSWORD = ([uri]$settings.POSTGRES_URL.Replace('postgresql+asyncpg', 'postgresql')).UserInfo.Split(':', 2)[1]
    if (-not (Test-Path "$data/postgres/PG_VERSION")) {
        $pwfile = Join-Path $runtime 'pg-init-password.tmp'
        try {
            $env:PGPASSWORD | Set-Content -LiteralPath $pwfile -Encoding ASCII
            & "$pg/initdb.exe" -D "$data/postgres" -U postgres -A scram-sha-256 --encoding=UTF8 --locale=C "--pwfile=$pwfile"
            Assert-Exit 'PostgreSQL initialization'
        } finally { if (Test-Path -LiteralPath $pwfile) { Remove-Item -LiteralPath $pwfile } }
    }
    & "$pg/pg_ctl.exe" -D "$data/postgres" status *> $null
    if ($LASTEXITCODE -ne 0) {
        if (Test-Port 15432) { throw 'PostgreSQL port 15432 is occupied by another service' }
        Start-Owned 'postgres' "$pg/postgres.exe" @('-D', "`"$data/postgres`"", '-h', '127.0.0.1', '-p', '15432') $runtime 15432
        for ($i = 0; $i -lt 60; $i++) {
            & "$pg/pg_isready.exe" -h 127.0.0.1 -p 15432 -U postgres *> $null
            if ($LASTEXITCODE -eq 0) { break }
            Start-Sleep -Seconds 1
        }
        Assert-Exit 'PostgreSQL readiness (check its console)'
    }
    $exists = & "$pg/psql.exe" -h 127.0.0.1 -p 15432 -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='strawberry'"
    Assert-Exit 'PostgreSQL connection'
    if ($exists -ne '1') { & "$pg/createdb.exe" -h 127.0.0.1 -p 15432 -U postgres strawberry; Assert-Exit 'Database creation' }
    $env:PGPASSWORD = $null
    if (-not (Test-Path "$runtime/qdrant/qdrant.exe")) { throw 'Run setup-services.cmd to install Qdrant' }
    @"
storage:
  storage_path: '$data/qdrant'
  snapshots_path: '$data/qdrant-snapshots'
service:
  host: 127.0.0.1
  http_port: 16333
  grpc_port: 16334
  enable_cors: false
telemetry_disabled: true
"@ | Set-Content "$runtime/qdrant-local.yaml" -Encoding ASCII
    Start-Owned 'qdrant' "$runtime/qdrant/qdrant.exe" @('--config-path', "`"$runtime/qdrant-local.yaml`"") $runtime 16333
    $java = Join-Path $runtime 'java/jdk-21.0.12.1+1-jre/bin/java.exe'
    $neo = Join-Path $runtime 'neo4j'
    if (-not (Test-Path "$neo/lib/neo4j-5.26.0.jar")) { throw 'Run setup-services.cmd to install Neo4j' }
    New-Item -ItemType Directory -Force -Path "$neo/conf" | Out-Null
    @"
server.default_listen_address=127.0.0.1
server.default_advertised_address=127.0.0.1
server.bolt.enabled=true
server.bolt.listen_address=:17687
server.bolt.advertised_address=:17687
server.http.enabled=true
server.http.listen_address=:17474
server.http.advertised_address=:17474
server.https.enabled=false
server.memory.pagecache.size=256m
dbms.security.auth_enabled=true
"@ | Set-Content "$neo/conf/neo4j.conf" -Encoding ASCII
    if (-not (Test-Path "$neo/data/dbms/auth.ini") -and -not (Test-Path "$neo/data/databases/system")) {
        $env:NEO4J_HOME = $neo
        $env:NEO4J_CONF = "$neo/conf"
        & $java -cp "$neo/lib/*" org.neo4j.cli.AdminTool dbms set-initial-password $settings.NEO4J_PASSWORD *> "$logs/neo4j-auth.log"
        Assert-Exit 'Neo4j initial authentication'
    }
    Start-Owned 'neo4j' $java @('-Xms128m', '-Xmx512m', '--add-opens=java.base/java.nio=ALL-UNNAMED', '--add-opens=java.base/java.io=ALL-UNNAMED', '-cp', "`"$neo/lib/*`"", 'org.neo4j.server.CommunityEntryPoint', "--home-dir=`"$neo`"", "--config-dir=`"$neo/conf`"") $neo 17687
    $redis = Get-ChildItem "$runtime/redis" -Recurse -Filter redis-server.exe | Select-Object -First 1
    if (-not $redis) { throw 'Redis binary not installed' }
    Start-Owned 'redis' $redis.FullName @('--bind', '127.0.0.1', '--port', '16379', '--appendonly', 'yes', '--dir', "`"$data/redis`"") $redis.DirectoryName 16379
    $env:AWS_ACCESS_KEY_ID = $settings.MINIO_ACCESS_KEY
    $env:AWS_SECRET_ACCESS_KEY = $settings.MINIO_SECRET_KEY
    $storageConfig = @{ identities = @(@{ name = 'localadmin'; credentials = @(@{ accessKey = $settings.MINIO_ACCESS_KEY; secretKey = $settings.MINIO_SECRET_KEY }); actions = @('Admin', 'Read', 'Write', 'List', 'Tagging') }) }
    $storageConfig | ConvertTo-Json -Depth 6 | Set-Content "$runtime/s3.json" -Encoding ASCII
    Start-Owned 'storage' "$runtime/seaweedfs/weed.exe" @('mini', '-dir', "`"$data/storage`"", '-ip=127.0.0.1', '-ip.bind=127.0.0.1', '-s3.port=19000', '-s3.config', "`"$runtime/s3.json`"", '-master.port=19333', '-volume.port=19340', '-filer.port=18888', '-admin.ui=false', '-webdav=false', '-s3.port.iceberg=0', '-s3.port.lance=0', '-master.telemetry=false') $runtime 19000
    $env:AWS_ACCESS_KEY_ID = $null
    $env:AWS_SECRET_ACCESS_KEY = $null
    $brokerPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path $brokerPython)) { throw 'Run uv sync --project scripts/windows --python 3.12 first' }
    Start-Owned 'mqtt' $brokerPython @('"' + (Join-Path $PSScriptRoot 'mqtt_broker.py') + '"') $root 11883
    Write-Host 'Hardware MQTT: this computer LAN IPv4, port 1883. Local subnets only; username/password ignored.'
    Write-Host 'For LAN firewall access run setup-mqtt-lan.cmd as administrator once.'
    Start-Owned 'worker' $python @((Join-Path $root 'backend/run_local.py'), '--worker') (Join-Path $root 'backend')
    for ($i = 0; $i -lt 30; $i++) {
        if ((Test-Port 17687) -and (Test-Port 16333) -and (Test-Port 16379) -and (Test-Port 19000) -and (Test-Port 11883) -and (Test-Port 1883)) { break }
        Start-Sleep -Seconds 1
    }
    Write-Host 'Dependencies started. Start backend/run_local.py in PyCharm.'
    Write-Host 'Services run in separate foreground consoles. Close a service console to stop that service.'
}
$failed = $false
foreach ($entry in @(@('PostgreSQL',15432), @('Qdrant',16333), @('Neo4j',17687), @('Redis',16379), @('S3',19000), @('MQTT',11883), @('MQTT-LAN',1883), @('FastAPI',5050))) {
    $ok = Test-Port $entry[1]
    Write-Host ("{0,-12} {1,-6} {2}" -f $entry[0], $entry[1], $(if ($ok) {'LISTENING'} else {'NOT RUNNING'}))
    if (-not $ok -and $entry[0] -ne 'FastAPI') { $failed = $true }
}
if ($failed) { exit 1 }
