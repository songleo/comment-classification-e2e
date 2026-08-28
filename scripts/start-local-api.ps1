[CmdletBinding()]
param(
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$model = Join-Path $projectRoot 'artifacts\model\config.json'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Missing .venv. Follow the environment setup in README.md first.'
}
if (-not (Test-Path -LiteralPath $model -PathType Leaf)) {
    throw 'Missing trained model. Run python -m comment_classifier.train first.'
}

Push-Location $projectRoot
try {
    & $python -m uvicorn comment_classifier.api:app --host 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}
