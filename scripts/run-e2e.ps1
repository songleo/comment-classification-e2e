[CmdletBinding()]
param(
    [string]$Image = 'comment-classifier-dev:0.1.0',
    [string]$HuggingFaceEndpoint = 'https://hf-mirror.com'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$artifactPath = Join-Path $projectRoot 'artifacts'
$cacheVolume = 'comment-classifier-huggingface-cache'

Push-Location $projectRoot
try {
    New-Item -ItemType Directory -Force -Path $artifactPath | Out-Null

    docker volume create $cacheVolume | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Hugging Face cache volume.' }

    docker run --rm `
        --name comment-classifier-e2e `
        --mount "type=bind,source=$artifactPath,target=/app/artifacts" `
        --mount "type=volume,source=$cacheVolume,target=/cache/huggingface" `
        --env "HF_ENDPOINT=$HuggingFaceEndpoint" `
        $Image `
        /bin/sh /app/scripts/run-e2e.sh
    if ($LASTEXITCODE -ne 0) { throw 'Docker end-to-end validation failed.' }
}
finally {
    Pop-Location
}
