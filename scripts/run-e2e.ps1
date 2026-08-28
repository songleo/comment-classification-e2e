[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $projectRoot
try {
    docker compose run --rm e2e
    if ($LASTEXITCODE -ne 0) { throw 'Docker end-to-end validation failed.' }
}
finally {
    Pop-Location
}
