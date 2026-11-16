# Actual Windows-only batch / PowerShell / Waitress integration suite.
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This test requires a real Windows runner.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$testRoot = Join-Path $env:TEMP ('Cafe LUX deployment ' + [guid]::NewGuid().ToString('N'))
$source = Join-Path $testRoot ('nested folder\Caf' + [char]0xE9 + ' LUX\application')
$data = Join-Path $testRoot 'separate persistent data'
New-Item -ItemType Directory -Path $source -Force | Out-Null
Get-ChildItem -LiteralPath $root -Force | Where-Object { $_.Name -notin @('.git','.venv','dist','__pycache__','.pytest_cache','cafe-lux.local.json','setup-error.log') } | Copy-Item -Destination $source -Recurse -Force
$oldData = $env:CAFE_LUX_DATA_DIR
$oldPython = $env:CAFE_LUX_PYTHON
$oldNoIndex = $env:PIP_NO_INDEX
$venvPython = Join-Path $source '.venv\Scripts\python.exe'
$busy = $null
$expected = 0
function Batch([string]$Name, [bool]$ShouldPass = $true) {
    $path = Join-Path $source ($Name + '.bat')
    & $path
    $code = $LASTEXITCODE
    if (($ShouldPass -and $code -ne 0) -or (!$ShouldPass -and $code -eq 0)) { throw "$Name returned unexpected exit code $code" }
    $script:expected++
}
try {
    Set-Location -LiteralPath $testRoot
    $env:CAFE_LUX_DATA_DIR = $data
    Batch 'start' $false
    $env:CAFE_LUX_PYTHON = Join-Path $testRoot 'missing-python.exe'
    Batch 'setup' $false
    if ($oldPython) { $env:CAFE_LUX_PYTHON = $oldPython } else { Remove-Item Env:CAFE_LUX_PYTHON -ErrorAction SilentlyContinue }
    Batch 'setup'
    Remove-Item Env:CAFE_LUX_DATA_DIR -ErrorAction SilentlyContinue
    & $venvPython (Join-Path $source 'tests\windows_probe.py') seed
    if ($LASTEXITCODE -ne 0) { throw 'Admin initialization failed.' }
    Batch 'setup'
    & $venvPython (Join-Path $source 'tests\windows_probe.py') verify
    if ($LASTEXITCODE -ne 0) { throw 'Existing database/accounts/uploads were not preserved.' }
    $requirements = Join-Path $source 'requirements.txt'
    $original = Get-Content -LiteralPath $requirements -Raw
    Set-Content -LiteralPath $requirements -Value 'cafe-lux-nonexistent-test-package==0.0.0' -Encoding ASCII
    $env:PIP_NO_INDEX = '1'
    Batch 'setup' $false
    Set-Content -LiteralPath $requirements -Value $original -Encoding ASCII
    if ($null -eq $oldNoIndex) { Remove-Item Env:PIP_NO_INDEX -ErrorAction SilentlyContinue } else { $env:PIP_NO_INDEX = $oldNoIndex }
    Batch 'setup'
    $probe = '"' + (Join-Path $source 'tests\windows_probe.py') + '"'
    $busy = Start-Process -FilePath $venvPython -ArgumentList @($probe,'busy') -WorkingDirectory $source -PassThru
    for ($i=0; $i -lt 50 -and !(Test-Path (Join-Path $data 'busy-ready')); $i++) { Start-Sleep -Milliseconds 100 }
    if (!(Test-Path (Join-Path $data 'busy-ready'))) { throw 'Busy-port fixture failed.' }
    Batch 'start' $false
    $busy.Refresh(); if ($busy.HasExited) { throw 'Startup terminated an unrelated listener.' }
    Stop-Process -InputObject $busy; $busy.WaitForExit(); $busy = $null
    Batch 'start'
    & $venvPython (Join-Path $source 'tests\windows_probe.py') health
    if ($LASTEXITCODE -ne 0) { throw 'Waitress HTTP check failed.' }
    Batch 'start' $false
    $recordPath = Join-Path $data 'server-process.json'
    $record = Get-Content -LiteralPath $recordPath -Raw -Encoding UTF8
    $changed = $record | ConvertFrom-Json; $changed.Started = '0'
    $changed | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordPath -Encoding UTF8
    Batch 'stop' $false
    Set-Content -LiteralPath $recordPath -Value $record -Encoding UTF8
    Batch 'stop'
    Batch 'stop'
    $listener = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($listener) { throw 'Port remained occupied after stopping the owned interpreter/launcher.' }
    & $venvPython (Join-Path $source 'tests\windows_probe.py') verify
    if ($LASTEXITCODE -ne 0) { throw 'Stop changed persistent application data.' }
    Write-Host "PASS: $expected batch outcomes plus first-admin, preservation, health and process ownership probes."
} finally {
    if ($busy) { $busy.Refresh(); if (!$busy.HasExited) { Stop-Process -InputObject $busy } }
    if (Test-Path (Join-Path $data 'server-process.json')) { & (Join-Path $source 'stop.bat') }
    $env:CAFE_LUX_DATA_DIR = $oldData
    $env:CAFE_LUX_PYTHON = $oldPython
    $env:PIP_NO_INDEX = $oldNoIndex
    Set-Location -LiteralPath $root
    Write-Host "Disposable test directory: $testRoot"
}
