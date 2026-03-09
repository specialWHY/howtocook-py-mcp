$ErrorActionPreference = 'Stop'

# Force UTF-8 in this shell before starting Python.
chcp 65001 > $null
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$python = Join-Path $PSScriptRoot '..\\.venv\\Scripts\\python.exe'
if (-not (Test-Path $python)) {
    throw ".venv Python not found: $python"
}

& $python -m src.app
