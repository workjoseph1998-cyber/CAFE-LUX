# Cross-platform PowerShell unit checks. These do NOT claim Windows execution.
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$actualRoot = $AppRoot
$AppRoot = Join-Path ([IO.Path]::GetTempPath()) 'Nested Folder/Cafe LUX'
$quoted = 'python.exe -u "' + (Join-Path $AppRoot 'run.py') + '"'
if (!(Test-RunCommand $quoted)) { throw 'Quoted script path was not recognized.' }
if (Test-RunCommand 'python.exe "unrelated/run.py"') { throw 'Unrelated command was accepted.' }
if (!(Test-RunCommand 'python.exe run.py' $true)) { throw 'Legacy command was not recognized.' }
if (Test-RunCommand 'python.exe myrun.py' $true) { throw 'Ambiguous legacy command was accepted.' }
$AppRoot = $actualRoot
$oldExplicit = $env:CAFE_LUX_PYTHON
try {
    Remove-Item Env:CAFE_LUX_PYTHON -ErrorAction SilentlyContinue
    function Get-Command { param($Name, $ErrorAction) return $null }
    $missing = $false
    try { Find-Python | Out-Null } catch { $missing = $_.Exception.Message.Contains('No supported Python found') }
    if (!$missing) { throw 'Missing Python did not produce the expected diagnostic.' }
    $env:CAFE_LUX_PYTHON = 'unsupported-python'
    function Test-SupportedPython { param($Executable, $PrefixArguments) return $false }
    $unsupported = $false
    try { Find-Python | Out-Null } catch { $unsupported = $_.Exception.Message.Contains('3.11, 3.12 or 3.13') }
    if (!$unsupported) { throw 'Unsupported Python did not produce the expected diagnostic.' }
} finally {
    if ($null -eq $oldExplicit) { Remove-Item Env:CAFE_LUX_PYTHON -ErrorAction SilentlyContinue } else { $env:CAFE_LUX_PYTHON = $oldExplicit }
}
Write-Output 'PASS: command identity, missing Python and unsupported Python diagnostics (mocked discovery).'
