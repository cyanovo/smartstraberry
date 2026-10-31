# ============================================================
# build-with-fallback.ps1 - 构建前自动检测 + 自愈 + 回退
#
# 三层防护，杜绝"镜像站没配置好/没启动就构建失败"：
#   1. 自愈（docker-doctor 逻辑）：检测 insecure-registry 配置，缺失则自动写入
#      两个 daemon.json 位置（兼容所有 Docker Desktop 版本）并自动重启 Docker Desktop，
#      让 "HTTPS 访问 HTTP registry" 的错误永不复发。
#   2. 镜像站可达 -> 走本地镜像；不可达 -> 自动回退公网
#      （镜像走 Docker Hub / 公共镜像，Python 走 pypi.org，npm 走 npmmirror，apt 不走代理）。
#   3. 本机就是镜像站且配置实在无法修复时，自动改用 localhost:5000
#      （loopback 永不需要 insecure-registry 配置）。
#
# 用法（在项目根目录）：
#   powershell -ExecutionPolicy Bypass -File build-with-fallback.ps1                 # docker compose build
#   powershell -ExecutionPolicy Bypass -File build-with-fallback.ps1 -Up              # docker compose up -d --build
#   powershell -ExecutionPolicy Bypass -File build-with-fallback.ps1 -Up -Services api,web
#   powershell -ExecutionPolicy Bypass -File build-with-fallback.ps1 -DryRun          # 只检测并预览，不构建
#   -MirrorHostIp 192.168.31.83   指定镜像站 IP（默认读项目 .env 的 MIRROR_HOST_IP，读不到用 192.168.31.83）
# ============================================================

param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$MirrorHostIp = "",
    [switch]$Up,
    [string[]]$Services = @(),
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$composePath = Join-Path $ProjectRoot "docker-compose.yml"
if (-not (Test-Path -LiteralPath $composePath)) {
    throw "未找到 docker-compose.yml，请确认 -ProjectRoot 指向项目根目录（含 backend/、web/、docker/ 的目录）"
}

# 从项目 .env 读取 MIRROR_HOST_IP（若未显式指定）
if (-not $MirrorHostIp) {
    $envPath = Join-Path $ProjectRoot ".env"
    if (Test-Path -LiteralPath $envPath) {
        $line = Get-Content -LiteralPath $envPath -Encoding UTF8 | Where-Object { $_ -match '^MIRROR_HOST_IP=' } | Select-Object -First 1
        if ($line) { $MirrorHostIp = ($line -split '=', 2)[1].Trim() }
    }
    if (-not $MirrorHostIp) { $MirrorHostIp = "192.168.31.83" }
}

function Test-Port {
    param([string]$Target, [int]$Port, [int]$TimeoutMs = 1200)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $result = $client.BeginConnect($Target, $Port, $null, $null)
        $ok = $result.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if ($ok -and $client.Connected) { $client.EndConnect($result); return $true }
        return $false
    } catch { return $false } finally { $client.Close() }
}

# ---------- 自愈：insecure-registry 配置 ----------

function Get-InsecureRegistries {
    $info = docker info 2>$null
    $list = @(); $inBlock = $false
    foreach ($line in $info) {
        if ($line -match 'Insecure Registries:') { $inBlock = $true; continue }
        if ($inBlock) {
            if ([string]::IsNullOrWhiteSpace($line)) { break }
            $list += $line.Trim()
        }
    }
    return $list
}

function Write-DaemonConfig {
    param([string]$Ip, [string]$DaemonPath)
    $parent = Split-Path -Parent $DaemonPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $config = [ordered]@{}
    if (Test-Path -LiteralPath $DaemonPath) {
        $raw = Get-Content -Raw -LiteralPath $DaemonPath -Encoding UTF8
        if ($raw.Trim()) {
            try {
                $parsed = $raw | ConvertFrom-Json
                foreach ($property in $parsed.PSObject.Properties) { $config[$property.Name] = $property.Value }
            } catch { Write-Host "  注意: $DaemonPath 不是合法 JSON，将重建" }
        }
    }
    $registries = @()
    if ($config.Contains("insecure-registries") -and $config["insecure-registries"]) { $registries = @($config["insecure-registries"]) }
    $registries += "registry.strawberry.lan:5000"
    $registries += "$Ip`:5000"
    $config["insecure-registries"] = @($registries | Sort-Object -Unique)
    $json = $config | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($DaemonPath, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
}

function Restart-DockerDesktop {
    $exe = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path $exe)) { return $false }
    Stop-Process -Name 'Docker Desktop' -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 6
    Start-Process $exe
    for ($i = 0; $i -lt 24; $i++) {
        docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { return $true }
        Start-Sleep -Seconds 5
    }
    return $false
}

# 返回：'ok'(已生效) / 'fixed'(自愈并重启成功) / 'localhost'(本机是镜像站，可用 localhost 兜底) / 'failed'
function Ensure-RegistryConfig {
    param([string]$Ip)
    docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { return 'failed' }
    $inSec = Get-InsecureRegistries
    if (($inSec -contains "$Ip`:5000") -or ($inSec -contains 'registry.strawberry.lan:5000')) {
        Write-Host "  [自愈] insecure-registry 已生效（无需处理）"
        return 'ok'
    }
    Write-Host "  [自愈] insecure-registry 缺失，正在写入两个 daemon.json 位置并重启 Docker Desktop..."
    Write-DaemonConfig -Ip $Ip -DaemonPath (Join-Path $env:APPDATA "Docker\daemon.json")
    Write-DaemonConfig -Ip $Ip -DaemonPath (Join-Path $env:USERPROFILE ".docker\daemon.json")
    if (Restart-DockerDesktop) {
        $inSec = Get-InsecureRegistries
        if (($inSec -contains "$Ip`:5000") -or ($inSec -contains 'registry.strawberry.lan:5000')) {
            Write-Host "  [自愈] 修复完成（已自动重启 Docker Desktop）"
            return 'fixed'
        }
    }
    if (Test-Port -Target 'localhost' -Port 5000) {
        Write-Host "  [自愈] 配置修复失败，但本机 localhost:5000 可达，将改用 localhost 兜底"
        return 'localhost'
    }
    Write-Host "  [自愈] 配置修复失败，且本机不是镜像站，镜像将回退公网"
    return 'failed'
}

# ---------- 主流程 ----------

Write-Host "== 本地镜像站检测（$MirrorHostIp）=="
$checks = @(
    @{ Name = "PyPI      :8088"; Port = 8088 },
    @{ Name = "npm       :4873"; Port = 4873 },
    @{ Name = "APT       :3142"; Port = 3142 },
    @{ Name = "Registry  :5000"; Port = 5000 }
)
$status = @{}
foreach ($c in $checks) {
    $portUp = Test-Port -Target $MirrorHostIp -Port $c.Port
    $status[$c.Port] = $portUp
    Write-Host ("  {0,-14} {1}" -f $c.Name, $(if ($portUp) { "[可达] 走本地镜像" } else { "[不可达] 回退公网" }))
}

$envOverrides = @{}
$registryMode = 'mirror'
if ($status[5000]) {
    $registryMode = Ensure-RegistryConfig -Ip $MirrorHostIp
}
if ($registryMode -eq 'localhost') {
    $envOverrides["PYTHON_BASE_IMAGE"] = "localhost:5000/library/python:3.12-slim"
    $envOverrides["UV_IMAGE"] = "localhost:5000/ghcr/astral-sh/uv:0.7.2"
    $envOverrides["NODE_SLIM_IMAGE"] = "localhost:5000/library/node:24-slim"
    $envOverrides["NODE_ALPINE_IMAGE"] = "localhost:5000/library/node:24-alpine"
    $envOverrides["NODE_20_ALPINE_IMAGE"] = "localhost:5000/library/node:20-alpine"
    $envOverrides["NGINX_ALPINE_IMAGE"] = "localhost:5000/library/nginx:alpine"
    $envOverrides["POSTGRES_IMAGE"] = "localhost:5000/library/postgres:16"
    $envOverrides["REDIS_IMAGE"] = "localhost:5000/library/redis:7-alpine"
    $envOverrides["NEO4J_IMAGE"] = "localhost:5000/library/neo4j:5.26"
    $envOverrides["ETCD_IMAGE"] = "localhost:5000/quay.io/coreos/etcd:v3.5.5"
    $envOverrides["MINIO_IMAGE"] = "localhost:5000/minio/minio:RELEASE.2023-03-20T20-16-18Z"
    $envOverrides["MILVUS_IMAGE"] = "localhost:5000/milvusdb/milvus:v2.5.6"
    $envOverrides["MOSQUITTO_IMAGE"] = "localhost:5000/library/eclipse-mosquitto:2"
    $envOverrides["MINERU_BASE_IMAGE"] = "localhost:5000/daocloud/vllm-openai:v0.11.2"
    $envOverrides["PADDLEX_BASE_IMAGE"] = "localhost:5000/baidu/paddlex:paddlex3.0.1-paddlepaddle3.0.0-gpu-cuda11.8-cudnn8.9-trt8.6"
    Write-Host "Registry 改用 localhost:5000（loopback 免配置，任何 Docker 版本有效）"
} elseif ($registryMode -eq 'failed' -or -not $status[5000]) {
    $envOverrides["PYTHON_BASE_IMAGE"] = "python:3.12-slim"
    $envOverrides["UV_IMAGE"] = "ghcr.io/astral-sh/uv:0.7.2"
    $envOverrides["NODE_SLIM_IMAGE"] = "node:24-slim"
    $envOverrides["NODE_ALPINE_IMAGE"] = "node:24-alpine"
    $envOverrides["NODE_20_ALPINE_IMAGE"] = "node:20-alpine"
    $envOverrides["NGINX_ALPINE_IMAGE"] = "nginx:alpine"
    $envOverrides["POSTGRES_IMAGE"] = "postgres:16"
    $envOverrides["REDIS_IMAGE"] = "redis:7-alpine"
    $envOverrides["NEO4J_IMAGE"] = "neo4j:5.26"
    $envOverrides["ETCD_IMAGE"] = "quay.io/coreos/etcd:v3.5.5"
    $envOverrides["MINIO_IMAGE"] = "minio/minio:RELEASE.2023-03-20T20-16-18Z"
    $envOverrides["MILVUS_IMAGE"] = "milvusdb/milvus:v2.5.6"
    $envOverrides["MOSQUITTO_IMAGE"] = "eclipse-mosquitto:2"
    $envOverrides["MINERU_BASE_IMAGE"] = "docker.m.daocloud.io/vllm/vllm-openai:v0.11.2"
    $envOverrides["PADDLEX_BASE_IMAGE"] = "ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlex/paddlex:paddlex3.0.1-paddlepaddle3.0.0-gpu-cuda11.8-cudnn8.9-trt8.6"
    Write-Host "Registry 不可达或配置失败：镜像回退公网（Docker Hub / 公共镜像）"
}
if (-not $status[8088]) {
    $envOverrides["PYPI_BASE_URL"] = "https://pypi.org"
    $envOverrides["PYPI_INDEX_URL"] = "https://pypi.org/simple"
    $envOverrides["PYPI_FALLBACK_INDEX_URL"] = "https://pypi.org/simple"
    $envOverrides["PYPI_TRUSTED_HOST"] = "pypi.org"
}
if (-not $status[4873]) {
    $envOverrides["NPM_REGISTRY"] = "https://registry.npmmirror.com"
    $envOverrides["NPM_FALLBACK_REGISTRY"] = "https://registry.npmjs.org"
}
if (-not $status[3142]) {
    $envOverrides["APT_PROXY"] = ""
}

foreach ($key in $envOverrides.Keys) {
    Set-Item -Path ("Env:" + $key) -Value $envOverrides[$key]
}

$cmd = @("docker", "compose")
if ($Up) { $cmd += @("up", "-d", "--build") } else { $cmd += "build" }
if ($Services.Count -gt 0) { $cmd += $Services }

Write-Host ""
Write-Host ("执行: " + ($cmd -join " "))

if ($DryRun) {
    Write-Host "（-DryRun 模式：仅预览，未真正执行）"
    if ($envOverrides.Count -gt 0) {
        Write-Host "本次将覆盖的环境变量："
        $envOverrides.GetEnumerator() | Sort-Object Key | ForEach-Object { Write-Host ("  {0}={1}" -f $_.Key, $_.Value) }
    } else {
        Write-Host "无需覆盖，直接使用 .env 的本地镜像配置。"
    }
    exit 0
}

Set-Location -LiteralPath $ProjectRoot
& $cmd[0] $cmd[1..($cmd.Count - 1)]
exit $LASTEXITCODE
