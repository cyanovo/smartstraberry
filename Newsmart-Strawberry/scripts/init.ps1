# Greenhouse Strawberry Initialization Script for PowerShell
# This script helps set up the environment for the greenhouse project
# Note: API keys will be visible during input - use with care

function New-RandomHex($ByteCount) {
    $bytes = [byte[]]::new($ByteCount)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return -join ($bytes | ForEach-Object { $_.ToString("x2") })
}

function Test-EnvValue($Name) {
    return [bool](Select-String -Path ".env" -Pattern "^$Name=.+" -Quiet)
}

function Set-EnvValue($Name, $Value) {
    $line = "$Name=$Value"
    if (Select-String -Path ".env" -Pattern "^$Name=" -Quiet) {
        $content = Get-Content -Path ".env"
        $content = $content | ForEach-Object {
            if ($_ -match "^$Name=") { $line } else { $_ }
        }
        $content | Set-Content -Path ".env" -Encoding UTF8
    } else {
        Add-Content -Path ".env" -Value $line -Encoding UTF8
    }
}

function Ensure-JwtEnv {
    if ((Test-EnvValue "JWT_SECRET_KEY") -and (Test-EnvValue "GREENHOUSE_INSTANCE_ID")) {
        return
    }

    Write-Host "JWT security settings are missing in .env. Generating local values..." -ForegroundColor Yellow
    if (-not (Test-EnvValue "JWT_SECRET_KEY")) {
        $JWT_SECRET_KEY = New-RandomHex 32
        Set-EnvValue "JWT_SECRET_KEY" $JWT_SECRET_KEY
    }

    if (-not (Test-EnvValue "GREENHOUSE_INSTANCE_ID")) {
        $GREENHOUSE_INSTANCE_ID = "instance-$(New-RandomHex 8)"
        Set-EnvValue "GREENHOUSE_INSTANCE_ID" $GREENHOUSE_INSTANCE_ID
    }

    Write-Host "Generated JWT_SECRET_KEY and GREENHOUSE_INSTANCE_ID in .env." -ForegroundColor Green
}

Write-Host "🚀 Initializing Greenhouse Strawberry project..." -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Check if .env file exists
if (Test-Path ".env") {
    Write-Host "✅ .env file already exists. Skipping environment setup." -ForegroundColor Green
    Ensure-JwtEnv
} else {
    Write-Host "📝 .env file not found. Let's set up your environment variables." -ForegroundColor Yellow
    Write-Host ""

    # Get SILICONFLOW_API_KEY
    Write-Host "🔑 SiliconFlow API Key required" -ForegroundColor Yellow
    Write-Host "Get your API key from: https://cloud.siliconflow.cn/i/Eo5yTHGJ" -ForegroundColor Blue
    Write-Host "Note: Press Ctrl+C at any time to cancel" -ForegroundColor Gray
    Write-Host ""

    do {
        $apiKey = Read-Host "Please enter your SILICONFLOW_API_KEY"
        if ([string]::IsNullOrEmpty($apiKey)) {
            Write-Host "❌ API Key cannot be empty. Please try again." -ForegroundColor Red
        }
    } while ([string]::IsNullOrEmpty($apiKey))

    # Get TAVILY_API_KEY (optional)
    Write-Host ""
    Write-Host "🔍 Tavily API Key (optional) - for search service" -ForegroundColor Yellow
    Write-Host "Get your API key from: https://app.tavily.com/" -ForegroundColor Blue

    $TAVILY_API_KEY = Read-Host "Please enter your TAVILY_API_KEY (press Enter to skip)"

    Write-Host ""
    Write-Host "JWT security settings" -ForegroundColor Yellow
    $JWT_SECRET_KEY = Read-Host "Please enter your JWT_SECRET_KEY (press Enter to auto-generate)"
    if ([string]::IsNullOrEmpty($JWT_SECRET_KEY)) {
        $JWT_SECRET_KEY = New-RandomHex 32
        Write-Host "Generated JWT_SECRET_KEY and saved it to .env." -ForegroundColor Green
    }

    $GREENHOUSE_INSTANCE_ID = Read-Host "Please enter your GREENHOUSE_INSTANCE_ID (press Enter to auto-generate)"
    if ([string]::IsNullOrEmpty($GREENHOUSE_INSTANCE_ID)) {
        $GREENHOUSE_INSTANCE_ID = "instance-$(New-RandomHex 8)"
        Write-Host "Generated GREENHOUSE_INSTANCE_ID and saved it to .env." -ForegroundColor Green
    }

    # Create .env file
    $envContent = @"
# SiliconFlow API Key (required)
SILICONFLOW_API_KEY=$apiKey

# Tavily API Key (optional - for search service)
"@

    if (-not [string]::IsNullOrEmpty($TAVILY_API_KEY)) {
        $envContent += "`nTAVILY_API_KEY=$TAVILY_API_KEY"
    }

    $envContent += @"

# JWT security settings
JWT_SECRET_KEY=$JWT_SECRET_KEY
GREENHOUSE_INSTANCE_ID=$GREENHOUSE_INSTANCE_ID
"@

    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ .env file created successfully!" -ForegroundColor Green

    # Clear the variables from memory
    Remove-Variable -Name "apiKey" -ErrorAction SilentlyContinue
    Remove-Variable -Name "TAVILY_API_KEY" -ErrorAction SilentlyContinue
    Remove-Variable -Name "JWT_SECRET_KEY" -ErrorAction SilentlyContinue
    Remove-Variable -Name "GREENHOUSE_INSTANCE_ID" -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "📦 Pulling Docker images..." -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

# List of Docker images to pull
$images = @(
    "python:3.12-slim",
    "node:24-slim",
    "node:24-alpine",
    "milvusdb/milvus:v2.5.6",
    "neo4j:5.26",
    "minio/minio:RELEASE.2023-03-20T20-16-18Z",
    "ghcr.io/astral-sh/uv:0.7.2",
    "nginx:alpine",
    "quay.io/coreos/etcd:v3.5.5",
    "postgres:16",
    "redis:7-alpine",
    "eclipse-mosquitto:2",
    "enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest"
)

# Pull each image
foreach ($image in $images) {
    Write-Host "🔄 Pulling ${image}..." -ForegroundColor Yellow
    try {
        & scripts/pull_image.ps1 $image
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Successfully pulled ${image}" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to pull ${image}" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "❌ Error pulling ${image}: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "🎉 Initialization complete!" -ForegroundColor Green
Write-Host "==========================" -ForegroundColor Green
Write-Host "You can now run: docker compose up -d --build" -ForegroundColor Cyan
Write-Host "This will start all services in development mode with hot-reload enabled." -ForegroundColor Cyan
