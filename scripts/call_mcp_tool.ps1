$ErrorActionPreference = 'Stop'

# Force UTF-8 output for Chinese recipe names.
chcp 65001 > $null
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

param(
    [Parameter(Mandatory = $true)]
    [string]$Tool,

    [Parameter(Mandatory = $false)]
    [string]$ArgsJson = '{}',

    [Parameter(Mandatory = $false)]
    [string]$Url = 'http://127.0.0.1:9000/sse'
)

$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw ".venv Python not found: $python"
}

$caller = Join-Path $PSScriptRoot 'call_mcp_tool.py'
if (-not (Test-Path $caller)) {
    throw "Caller script not found: $caller"
}

& $python $caller --url $Url --tool $Tool --args $ArgsJson
