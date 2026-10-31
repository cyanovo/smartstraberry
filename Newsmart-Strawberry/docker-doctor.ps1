# ============================================================
# docker-doctor.ps1 - 自检 + 自愈 Docker 本地镜像仓库（insecure-registry）配置
#
# 背景：Docker Desktop 不同版本读取的 daemon 配置位置不同：
#   - 4.3x 之前    : %APPDATA%\Docker\daemon.json
#   - 4.3x+（4.81 实测）: %USERPROFILE%\.docker\daemon.json
#   配置写错位置 -> 引擎用 HTTPS 访问 HTTP registry -> 报
#   "http: server gave HTTP response to HTTPS client"
#
# 本脚本做的事（全自动，无需人工）：
#   1. 检测镜像站 registry 是否可达（TCP :5000）
#   2. 检测 docker 引擎是否可用、insecure-registries 是否已包含本地仓库
#   3. 未包含 -> 向两个 daemon.json 位置写入（合并原配置、无 BOM UTF-8），
#      并重启 Docker Desktop 让引擎重新加载，再验证
#   4. 仍失败且本机就是镜像站（localhost:5000 可达）-> 提示改用 localhost:5000
#      （loopback 永不需要 insecure-registry 配置，任何 Docker Desktop 版本都有效）
#
# 用法：
#   powershell -ExecutionPolicy Bypass -File docker-doctor.ps1 -MirrorHostIp 192.168.31.83
#   powershell ... -NoRestart          # 只写配置，不自动重启 Docker Desktop
#
# 退出码：0=一切正常  1=已自动修复  2=修复失败（本机可用 localhost 兜底）  3=镜像站不可达
# ============================================================

param(
    [string]$MirrorHostIp = "192.168.31.83",
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"

function Test-TcpPort {
    param([string]$Target, [int]$Port, [int]$TimeoutMs = 1200)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $result = $client.BeginConnect($Target, $Port, $null, $null)
        $ok = $result.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if ($ok -and $client.Connected) { $client.EndConnect($result); return $true }
        return $false
    } catch { return $false } finally { $client.Close() }
}

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

Write-Host "== Docker 本地镜像仓库自检（$MirrorHostIp）=="

# 1) 镜像站 registry 可达？
if (-not (Test-TcpPort -Target $MirrorHostIp -Port 5000)) {
    if (Test-TcpPort -Target 'localhost' -Port 5000) {
        Write-Host "[提示] $MirrorHostIp`:5000 不通，但本机 localhost:5000 可达（本机就是镜像站？）"
        exit 2
    }
    Write-Host "[失败] 镜像站 registry ($MirrorHostIp`:5000) 不可达 - 请先启动镜像站容器"
    exit 3
}

# 2) docker 引擎可用？
docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[失败] Docker 引擎不可用，请先启动 Docker Desktop"
    exit 3
}

# 3) insecure-registries 是否已包含本地仓库？
$inSec = Get-InsecureRegistries
$hasIp = $inSec -contains "$MirrorHostIp`:5000"
$hasAlias = $inSec -contains 'registry.strawberry.lan:5000'
if ($hasIp -or $hasAlias) {
    Write-Host "[正常] insecure-registries 已包含 $MirrorHostIp`:5000（当前 Docker 引擎已生效）"
    exit 0
}

# 4) 自愈：双位置写入 + 重启引擎
Write-Host "[修复] insecure-registries 缺失，写入两个 daemon.json 位置..."
Write-Host "  " + (Join-Path $env:APPDATA "Docker\daemon.json")
Write-DaemonConfig -Ip $MirrorHostIp -DaemonPath (Join-Path $env:APPDATA "Docker\daemon.json")
Write-DaemonConfig -Ip $MirrorHostIp -DaemonPath (Join-Path $env:USERPROFILE ".docker\daemon.json")

if (-not $NoRestart) {
    Write-Host "[修复] 重启 Docker Desktop 让引擎重新加载配置（约 1 分钟）..."
    $restarted = Restart-DockerDesktop
    if (-not $restarted) {
        Write-Host "[失败] Docker Desktop 重启超时，请手动重启后再试"
        exit 2
    }
    $inSec = Get-InsecureRegistries
    if (($inSec -contains "$MirrorHostIp`:5000") -or ($inSec -contains 'registry.strawberry.lan:5000')) {
        Write-Host "[修复完成] insecure-registries 已生效（已自动重启 Docker Desktop）"
        exit 1
    }
}

# 5) 仍失败：localhost 兜底判定（loopback 永不需要 insecure 配置）
Write-Host "[失败] insecure-registries 仍未生效"
if (Test-TcpPort -Target 'localhost' -Port 5000) {
    Write-Host "[兜底] 本机 localhost:5000 可达 - 请把项目 .env 的镜像变量改为 localhost:5000，"
    Write-Host "       或使用 build-with-fallback.ps1（会自动切换）。"
    exit 2
}
exit 2
