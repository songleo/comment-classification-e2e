[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Missing .venv. Follow the environment setup in README.md first.'
}

Push-Location $projectRoot
try {
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed.' }
    & $python -m comment_classifier.data_validation
    if ($LASTEXITCODE -ne 0) { throw 'Dataset validation failed.' }
    & $python -m comment_classifier.train
    if ($LASTEXITCODE -ne 0) { throw 'Training failed.' }
    & $python -m comment_classifier.evaluate
    if ($LASTEXITCODE -ne 0) { throw 'Evaluation failed.' }
    & $python -m comment_classifier.predict --text '客服一直不处理退款'
    if ($LASTEXITCODE -ne 0) { throw 'Inference failed.' }
}
finally {
    Pop-Location
}
