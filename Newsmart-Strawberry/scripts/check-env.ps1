# 环境检查脚本 - 检查系统是否正确配置
# Usage: .\scripts\check-env.ps1

Write-Host "🔍 番茄温室智能管控平台 - 环境检查" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

$issues = @()
$warnings = @()

# 1. 检查 Docker
Write-Host "📦 检查 Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Docker 已安装: $dockerVersion" -ForegroundColor Green
    } else {
        $issues += "Docker 未安装或不在 PATH 中"
        Write-Host "  ❌ Docker 未安装" -ForegroundColor Red
    }
} catch {
    $issues += "Docker 未安装或不在 PATH 中"
    Write-Host "  ❌ Docker 未安装" -ForegroundColor Red
}

# 2. 检查 Docker Compose
Write-Host "📦 检查 Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker compose version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Docker Compose 已安装: $composeVersion" -ForegroundColor Green
    } else {
        $issues += "Docker Compose 未安装"
        Write-Host "  ❌ Docker Compose 未安装" -ForegroundColor Red
    }
} catch {
    $issues += "Docker Compose 未安装"
    Write-Host "  ❌ Docker Compose 未安装" -ForegroundColor Red
}

# 3. 检查 .env 文件
Write-Host ""
Write-Host "📝 检查环境配置..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  ✅ .env 文件存在" -ForegroundColor Green

    # 检查必填项
    $envContent = Get-Content ".env" -Raw

    if ($envContent -match "SILICONFLOW_API_KEY=(.+)") {
        $apiKey = $Matches[1].Trim()
        if ([string]::IsNullOrEmpty($apiKey)) {
            $issues += "SILICONFLOW_API_KEY 未配置"
            Write-Host "  ❌ SILICONFLOW_API_KEY 未配置" -ForegroundColor Red
        } else {
            Write-Host "  ✅ SILICONFLOW_API_KEY 已配置" -ForegroundColor Green
        }
    } else {
        $issues += "SILICONFLOW_API_KEY 未配置"
        Write-Host "  ❌ SILICONFLOW_API_KEY 未配置" -ForegroundColor Red
    }

    # 检查 JWT
    if ($envContent -match "JWT_SECRET_KEY=(.+)") {
        $jwtKey = $Matches[1].Trim()
        if ([string]::IsNullOrEmpty($jwtKey)) {
            $warnings += "JWT_SECRET_KEY 未配置（会自动生成）"
            Write-Host "  ⚠️  JWT_SECRET_KEY 未配置（会自动生成）" -ForegroundColor Yellow
        } else {
            Write-Host "  ✅ JWT_SECRET_KEY 已配置" -ForegroundColor Green
        }
    }

    # 检查 MQTT
    if ($envContent -match "MQTT_ENABLED=true") {
        Write-Host "  ✅ MQTT 已启用" -ForegroundColor Green
    } else {
        $warnings += "MQTT 未启用（IoT 功能不可用）"
        Write-Host "  ⚠️  MQTT 未启用" -ForegroundColor Yellow
    }
} else {
    $issues += ".env 文件不存在"
    Write-Host "  ❌ .env 文件不存在" -ForegroundColor Red
    Write-Host "     运行: .\scripts\init.ps1" -ForegroundColor Gray
}

# 4. 检查 Docker 容器状态
Write-Host ""
Write-Host "🐳 检查 Docker 容器..." -ForegroundColor Yellow
$containers = docker ps -a --format "table {{.Names}}\t{{.Status}}" 2>&1
if ($LASTEXITCODE -eq 0) {
    $requiredServices = @("api-dev", "web-dev", "postgres", "redis", "mosquitto")
    foreach ($service in $requiredServices) {
        if ($containers -match $service) {
            if ($containers -match "$service.*Up") {
                Write-Host "  ✅ $service 正在运行" -ForegroundColor Green
            } else {
                $warnings += "$service 未运行"
                Write-Host "  ⚠️  $service 未运行" -ForegroundColor Yellow
            }
        } else {
            $warnings += "$service 未创建"
            Write-Host "  ⚠️  $service 未创建" -ForegroundColor Yellow
        }
    }
} else {
    $warnings += "无法获取容器状态"
    Write-Host "  ⚠️  无法获取容器状态" -ForegroundColor Yellow
}

# 5. 检查端口
Write-Host ""
Write-Host "🔌 检查端口占用..." -ForegroundColor Yellow
$ports = @(5173, 8000, 5432, 6379, 1883)
foreach ($port in $ports) {
    $connection = Test-NetConnection -ComputerName localhost -Port $port -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($connection.TcpTestSucceeded) {
        Write-Host "  ✅ 端口 $port 已开放" -ForegroundColor Green
    } else {
        $warnings += "端口 $port 未开放"
        Write-Host "  ⚠️  端口 $port 未开放" -ForegroundColor Yellow
    }
}

# 6. 检查 Python（用于本地检测服务）
Write-Host ""
Write-Host "🐍 检查 Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Python 已安装: $pythonVersion" -ForegroundColor Green

        # 检查 ultralytics
        $hasUltralytics = python -c "import ultralytics" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ ultralytics 已安装" -ForegroundColor Green
        } else {
            $warnings += "ultralytics 未安装（YOLO 检测功能不可用）"
            Write-Host "  ⚠️  ultralytics 未安装" -ForegroundColor Yellow
            Write-Host "     运行: pip install ultralytics opencv-python" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠️  Python 未安装（本地检测服务不可用）" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  Python 未安装（本地检测服务不可用）" -ForegroundColor Yellow
}

# 总结
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
if ($issues.Count -eq 0) {
    Write-Host "✅ 环境检查通过！" -ForegroundColor Green
    if ($warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "⚠️  警告:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "  - $warning" -ForegroundColor Yellow
        }
    }
    Write-Host ""
    Write-Host "🚀 启动命令: docker compose up -d --build" -ForegroundColor Cyan
} else {
    Write-Host "❌ 发现以下问题:" -ForegroundColor Red
    foreach ($issue in $issues) {
        Write-Host "  - $issue" -ForegroundColor Red
    }
    if ($warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "⚠️  警告:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "  - $warning" -ForegroundColor Yellow
        }
    }
    Write-Host ""
    Write-Host "📖 请参考 docs/troubleshooting.md 解决问题" -ForegroundColor Cyan
}
