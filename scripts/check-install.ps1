$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$failed = 0
function Check($label, $action) {
    try { & $action; Write-Host "PASS $label" -ForegroundColor Green }
    catch { Write-Host "FAIL ${label}: $_" -ForegroundColor Red; $script:failed++ }
}
Check 'Virtual environment / Python' { if (!(Test-Path $Python)) { throw 'Run setup.bat' }; & $Python --version; if ($LASTEXITCODE) { throw 'Python failed' } }
Check 'Dependencies' { & $Python -m pip check; if ($LASTEXITCODE) { throw 'Dependency check failed' } }
Check 'Configuration / database / uploads / import' { & $Python (Join-Path $AppRoot 'scripts\diagnose.py'); if ($LASTEXITCODE) { throw 'Application diagnosis failed' } }
Check 'Port 8000' { if (Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue) { Write-Host 'Port occupied; stop the existing listener before start.bat. Nothing terminated.' } else { Write-Host 'Port available' } }
Write-Host "Diagnostics complete: $failed failure(s)."
if ($failed) { exit 1 }
