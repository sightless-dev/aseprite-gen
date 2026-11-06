param([switch]$BuildAseprite)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required' }
    }
    & '.venv/Scripts/python.exe' -m pip install -r requirements-windows.lock
    if ($LASTEXITCODE -ne 0) { throw 'Pinned Python dependency installation failed' }
    & '.venv/Scripts/python.exe' -m pip install -e . --no-deps
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
    if ($BuildAseprite) { & "$PSScriptRoot/build-aseprite.ps1" }
    & '.venv/Scripts/python.exe' -m aseprite_gen.cli doctor
    if ($LASTEXITCODE -ne 0) { throw 'Set ASEPRITE_PATH or run scripts/build-aseprite.ps1' }
} finally { Pop-Location }
