param(
    [Parameter(Mandatory = $true)]
    [string]$Tool,

    [Parameter(Mandatory = $false)]
    [string[]]$Arg = @(),

    [Parameter(Mandatory = $false)]
    [string]$ArgsJson = '{}',

    [Parameter(Mandatory = $false)]
    [string]$Url = 'http://127.0.0.1:9000/sse'
)

$ErrorActionPreference = 'Stop'

# Force UTF-8 output for Chinese recipe names.
chcp 65001 > $null
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw ".venv Python not found: $python"
}

$caller = Join-Path $PSScriptRoot 'call_mcp_tool.py'
if (-not (Test-Path $caller)) {
    throw "Caller script not found: $caller"
}

$pyArgs = @($caller, '--url', $Url, '--tool', $Tool)

if ($Arg -and $Arg.Count -gt 0) {
    $joinedArg = ($Arg -join ' ').Trim()
    $looksLikeJson = $joinedArg.StartsWith('{') -or $joinedArg.StartsWith('[')

    # PowerShell quoting can occasionally route JSON text into -Arg by mistake.
    # If it looks like raw JSON, pass it through --args for compatibility.
    if ($looksLikeJson -and ($Arg | Where-Object { $_ -match '=' }).Count -eq 0) {
        $pyArgs += @('--args', $joinedArg)
        & $python @pyArgs
        exit $LASTEXITCODE
    }

    foreach ($item in $Arg) {
        if ($item -notmatch '=') {
            throw "Invalid -Arg value '$item'. Expected key=value"
        }
        $pyArgs += @('--arg', $item)
    }
}
else {
    $pyArgs += @('--args', $ArgsJson)
}

& $python @pyArgs
