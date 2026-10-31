#!/bin/bash
# 环境检查脚本 - 检查系统是否正确配置
# Usage: ./scripts/check-env.sh

echo "🔍 番茄温室智能管控平台 - 环境检查"
echo "=================================="
echo ""

issues=()
warnings=()

# 1. 检查 Docker
echo "📦 检查 Docker..."
if command -v docker &> /dev/null; then
    docker_version=$(docker --version 2>&1)
    echo "  ✅ Docker 已安装: $docker_version"
else
    issues+=("Docker 未安装或不在 PATH 中")
    echo "  ❌ Docker 未安装"
fi

# 2. 检查 Docker Compose
echo "📦 检查 Docker Compose..."
if docker compose version &> /dev/null; then
    compose_version=$(docker compose version 2>&1)
    echo "  ✅ Docker Compose 已安装: $compose_version"
else
    issues+=("Docker Compose 未安装")
    echo "  ❌ Docker Compose 未安装"
fi

# 3. 检查 .env 文件
echo ""
echo "📝 检查环境配置..."
if [ -f ".env" ]; then
    echo "  ✅ .env 文件存在"

    # 检查必填项
    if grep -q "^SILICONFLOW_API_KEY=." .env; then
        echo "  ✅ SILICONFLOW_API_KEY 已配置"
    else
        issues+=("SILICONFLOW_API_KEY 未配置")
        echo "  ❌ SILICONFLOW_API_KEY 未配置"
    fi

    # 检查 JWT
    if grep -q "^JWT_SECRET_KEY=." .env; then
        echo "  ✅ JWT_SECRET_KEY 已配置"
    else
        warnings+=("JWT_SECRET_KEY 未配置（会自动生成）")
        echo "  ⚠️  JWT_SECRET_KEY 未配置（会自动生成）"
    fi

    # 检查 MQTT
    if grep -q "^MQTT_ENABLED=true" .env; then
        echo "  ✅ MQTT 已启用"
    else
        warnings+=("MQTT 未启用（IoT 功能不可用）")
        echo "  ⚠️  MQTT 未启用"
    fi
else
    issues+=(".env 文件不存在")
    echo "  ❌ .env 文件不存在"
    echo "     运行: ./scripts/init.sh"
fi

# 4. 检查 Docker 容器状态
echo ""
echo "🐳 检查 Docker 容器..."
for service in api-dev web-dev postgres redis mosquitto; do
    if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
        echo "  ✅ $service 正在运行"
    elif docker ps -a --format '{{.Names}}' | grep -q "^${service}$"; then
        warnings+=("$service 未运行")
        echo "  ⚠️  $service 未运行"
    else
        warnings+=("$service 未创建")
        echo "  ⚠️  $service 未创建"
    fi
done

# 5. 检查端口
echo ""
echo "🔌 检查端口占用..."
for port in 5173 8000 5432 6379 1883; do
    if nc -z localhost $port 2>/dev/null; then
        echo "  ✅ 端口 $port 已开放"
    else
        warnings+=("端口 $port 未开放")
        echo "  ⚠️  端口 $port 未开放"
    fi
done

# 6. 检查 Python（用于本地检测服务）
echo ""
echo "🐍 检查 Python..."
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version 2>&1)
    echo "  ✅ Python 已安装: $python_version"

    # 检查 ultralytics
    if python3 -c "import ultralytics" 2>/dev/null; then
        echo "  ✅ ultralytics 已安装"
    else
        warnings+=("ultralytics 未安装（YOLO 检测功能不可用）")
        echo "  ⚠️  ultralytics 未安装"
        echo "     运行: pip3 install ultralytics opencv-python"
    fi
elif command -v python &> /dev/null; then
    python_version=$(python --version 2>&1)
    echo "  ✅ Python 已安装: $python_version"
else
    echo "  ⚠️  Python 未安装（本地检测服务不可用）"
fi

# 总结
echo ""
echo "=================================="
if [ ${#issues[@]} -eq 0 ]; then
    echo "✅ 环境检查通过！"
    if [ ${#warnings[@]} -gt 0 ]; then
        echo ""
        echo "⚠️  警告:"
        for warning in "${warnings[@]}"; do
            echo "  - $warning"
        done
    fi
    echo ""
    echo "🚀 启动命令: docker compose up -d --build"
else
    echo "❌ 发现以下问题:"
    for issue in "${issues[@]}"; do
        echo "  - $issue"
    done
    if [ ${#warnings[@]} -gt 0 ]; then
        echo ""
        echo "⚠️  警告:"
        for warning in "${warnings[@]}"; do
            echo "  - $warning"
        done
    fi
    echo ""
    echo "📖 请参考 docs/troubleshooting.md 解决问题"
fi
