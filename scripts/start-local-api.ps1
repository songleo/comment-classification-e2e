[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $projectRoot
try {
    docker compose up --build api
    if ($LASTEXITCODE -ne 0) { throw 'Docker API service failed.' }
}
finally {
    Pop-Location
}
