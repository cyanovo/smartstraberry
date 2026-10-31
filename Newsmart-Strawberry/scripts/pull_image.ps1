param(
    [Parameter(Mandatory=$true)]
    [string]$ImageTag
)

$ErrorActionPreference = "Stop"

function Get-MirrorTag([string]$Image) {
    $domesticPrefixes = @(
        "enterprise-public-cn-beijing.cr.volces.com/",
        "ccr-2vdh3abv-pub.cnc.bj.baidubce.com/",
        "docker.m.daocloud.io/",
        "m.daocloud.io/"
    )

    foreach ($prefix in $domesticPrefixes) {
        if ($Image.StartsWith($prefix)) {
            return $null
        }
    }

    if ($Image.StartsWith("ghcr.io/") -or $Image.StartsWith("quay.io/") -or $Image.StartsWith("gcr.io/") -or $Image.StartsWith("registry.k8s.io/")) {
        return "m.daocloud.io/$Image"
    }

    if ($Image.StartsWith("docker.io/")) {
        return "m.daocloud.io/$Image"
    }

    $slashCount = ($Image -split '/' | Measure-Object).Count - 1
    if ($slashCount -eq 0) {
        return "m.daocloud.io/docker.io/library/$Image"
    }

    if ($slashCount -eq 1) {
        return "m.daocloud.io/docker.io/$Image"
    }

    return $null
}

function Pull-Image([string]$Image) {
    Write-Host "Pulling: $Image" -ForegroundColor Yellow
    docker pull $Image
}

Write-Host "Preparing image: $ImageTag" -ForegroundColor Green

$mirrorTag = Get-MirrorTag $ImageTag

if ($mirrorTag) {
    try {
        Write-Host "Trying China mirror: $mirrorTag" -ForegroundColor Cyan
        Pull-Image $mirrorTag

        if ($mirrorTag -ne $ImageTag) {
            docker tag $mirrorTag $ImageTag
        }

        Write-Host "Successfully pulled via China mirror: $ImageTag" -ForegroundColor Green
        exit 0
    } catch {
        Write-Host "China mirror failed, falling back to original image: $ImageTag" -ForegroundColor Yellow
    }
} else {
    Write-Host "Image is already from a China-friendly registry or unsupported mirror mapping. Pulling original tag." -ForegroundColor Cyan
}

try {
    Pull-Image $ImageTag
    Write-Host "Successfully pulled original image: $ImageTag" -ForegroundColor Green
} catch {
    Write-Host "Failed to pull image from both mirror and original source: $ImageTag" -ForegroundColor Red
    Write-Host $_ -ForegroundColor Red
    exit 1
}
