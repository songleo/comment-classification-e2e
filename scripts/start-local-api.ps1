[CmdletBinding()]
param(
    [string]$Image = 'comment-classifier-dev:0.1.0',
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$artifactPath = Join-Path $projectRoot 'artifacts'

Push-Location $projectRoot
try {
    if (-not (Test-Path (Join-Path $artifactPath 'model'))) {
        throw 'Model artifacts are missing. Run the end-to-end container first.'
    }

    docker run --rm `
        --name comment-classifier-api `
        --publish "${Port}:8000" `
        --mount "type=bind,source=$artifactPath,target=/app/artifacts,readonly" `
        $Image
    if ($LASTEXITCODE -ne 0) { throw 'Docker API service failed.' }
}
finally {
    Pop-Location
}
