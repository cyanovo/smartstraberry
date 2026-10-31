$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runtime = Join-Path $root '.runtime'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$headers = @{ 'User-Agent' = 'strawberry-local-setup' }
$uv = Get-Command uv -ErrorAction SilentlyContinue
$uvPath = if ($uv) { $uv.Source } else { (Get-Item "$env:USERPROFILE/.local/bin/uv.exe" -ErrorAction Stop).FullName }
& $uvPath sync --project $PSScriptRoot --python 3.12 --frozen
if ($LASTEXITCODE -ne 0) { throw 'MQTT environment setup failed' }
function Get-Archive($url, $name, $directory, $digest = '') {
    $archive = Join-Path $runtime $name
    if (-not (Test-Path -LiteralPath $archive) -or (Get-Item -LiteralPath $archive).Length -eq 0) {
        Write-Host "Downloading $name"
        & curl.exe --fail --location --retry 2 --continue-at - --connect-timeout 30 --max-time 900 --output "$archive.part" $url
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $name" }
        Move-Item -LiteralPath "$archive.part" -Destination $archive -Force
    }
    if ($digest -and (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower() -ne $digest.Replace('sha256:', '').ToLower()) {
        throw "Checksum mismatch: $archive"
    }
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    Expand-Archive -LiteralPath $archive -DestinationPath $directory -Force
}
if (-not (Test-Path "$runtime/pgsql/bin/postgres.exe")) {
    Get-Archive 'https://get.enterprisedb.com/postgresql/postgresql-17.6-1-windows-x64-binaries.zip' 'postgresql-17.6.zip' $runtime
}
if (-not (Get-ChildItem "$runtime/redis" -Recurse -Filter redis-server.exe -ErrorAction SilentlyContinue)) {
    $release = Invoke-RestMethod 'https://api.github.com/repos/redis-windows/redis-windows/releases/latest' -Headers $headers
    $asset = $release.assets | Where-Object name -Match '^Redis-.*-Windows-x64-cygwin.zip$' | Select-Object -First 1
    if (-not $asset) { throw 'Redis Windows asset not found' }
    Get-Archive $asset.browser_download_url $asset.name "$runtime/redis" $asset.digest
}
if (-not (Test-Path "$runtime/seaweedfs/weed.exe")) {
    Get-Archive 'https://github.com/seaweedfs/seaweedfs/releases/download/4.48/windows_amd64.zip' 'seaweedfs-4.48.zip' "$runtime/seaweedfs" 'fe90c04c0620ad1a1c756f86cd5e1443773f56a446688077a4bb5ec04c3cc874'
}
if (-not (Test-Path "$runtime/qdrant/qdrant.exe")) {
    Get-Archive 'https://github.com/qdrant/qdrant/releases/download/v1.19.2/qdrant-x86_64-pc-windows-msvc.zip' 'qdrant-1.19.2.zip' "$runtime/qdrant" '7d86596f16c6e85d45a50312f5e16ccb51e059b62e3d7308110cb65b4c799a4d'
}
if (-not (Test-Path "$runtime/java/jdk-21.0.12.1+1-jre/bin/java.exe")) {
    Get-Archive 'https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/OpenJDK21U-jre_x64_windows_hotspot_21.0.12.1_1.zip' 'java21.zip' "$runtime/java" 'd35f31e712f0fcf6ac5a093edc90204fbff22f720ba3950bd09d331d5e621636'
}
if (-not (Test-Path "$runtime/apache-maven-3.9.9/bin/mvn.cmd")) {
    Get-Archive 'https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.9/apache-maven-3.9.9-bin.zip' 'apache-maven.zip' $runtime
}
$env:JAVA_HOME = Join-Path $runtime 'java/jdk-21.0.12.1+1-jre'
& "$runtime/apache-maven-3.9.9/bin/mvn.cmd" -B -f "$PSScriptRoot/neo4j/pom.xml" "-Dmaven.repo.local=$runtime/maven-cache" org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy-dependencies '-DincludeScope=runtime' "-DoutputDirectory=$runtime/neo4j/lib"
if ($LASTEXITCODE -ne 0) { throw 'Neo4j official Maven dependency download failed' }
Write-Host 'Dependency downloads complete.'
