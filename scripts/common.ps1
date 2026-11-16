# ASCII source for Windows PowerShell 5.1; Python handles all files as UTF-8.
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$AppRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $AppRoot '.venv\Scripts\python.exe'
$Manager = Join-Path $AppRoot 'manage.py'
$ConfigFile = Join-Path $AppRoot 'cafe-lux.local.json'
$script:Step = 'initialization'
$script:DataRoot = $null

function Write-Step([string]$Name) {
    $script:Step = $Name
    Write-Host "[Cafe LUX] $Name"
}

function Invoke-CheckedPython([string[]]$Arguments) {
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python command failed (exit $LASTEXITCODE). Review the output immediately above." }
}

function Read-Installation {
    if (!(Test-Path -LiteralPath $ConfigFile)) { throw 'Missing cafe-lux.local.json. Run setup.bat first.' }
    # Resolve effective values in exactly the same way as Flask and manage.py.
    $result = & $Python -c "from deployment import load_environment,validate_data_path; import os; load_environment(); print(validate_data_path(os.environ['CAFE_LUX_DATA_DIR'],protected=[p for p in os.environ.get('CAFE_LUX_PROTECTED_DIRS','').split(os.pathsep) if p]))"
    if ($LASTEXITCODE -ne 0) { throw 'Cannot load installation configuration. Check the error above and cafe-lux.local.json.' }
    $script:DataRoot = ($result | Select-Object -Last 1).Trim()
    $script:ProcessRecord = Join-Path $script:DataRoot 'server-process.json'
}

function Test-SupportedPython([string]$Executable, [string[]]$PrefixArguments = @()) {
    try {
        $result = & $Executable @PrefixArguments -c "import sys,struct; print(sys.version.split()[0]); sys.exit(0 if (3,11)<=sys.version_info[:2]<(3,14) and struct.calcsize('P')==8 else 7)" 2>&1
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}

function Find-Python {
    if ($env:CAFE_LUX_PYTHON) {
        if (!(Test-SupportedPython $env:CAFE_LUX_PYTHON)) { throw 'CAFE_LUX_PYTHON must point to a working 64-bit Python 3.11, 3.12 or 3.13 executable.' }
        return @{ Executable = $env:CAFE_LUX_PYTHON; Prefix = @() }
    }
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        foreach ($version in @('-3.12', '-3.13', '-3.11', '-3')) {
            if (Test-SupportedPython $launcher.Source @($version)) { return @{ Executable = $launcher.Source; Prefix = @($version) } }
        }
    }
    foreach ($name in @('python.exe', 'python3.exe')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and (Test-SupportedPython $command.Source)) { return @{ Executable = $command.Source; Prefix = @() } }
    }
    throw 'No supported Python found. Install 64-bit CPython 3.12 (3.11/3.13 also supported), then reopen the terminal. Enable the py launcher or add Python to PATH. You may set CAFE_LUX_PYTHON to its executable.'
}

function Report-Failure($Failure) {
    $message = "[Cafe LUX] FAILED at step '$script:Step': $($Failure.Exception.Message)"
    Write-Host $message -ForegroundColor Red
    Write-Host 'See docs\TROUBLESHOOTING.md. Run from an already-open CMD or PowerShell terminal so output remains visible.'
    # No transcript, environment dump, passwords, secret keys or request/customer data.
    try {
        $log = Join-Path $AppRoot 'setup-error.log'
        if ($script:DataRoot -and (Test-Path -LiteralPath (Join-Path $script:DataRoot 'logs'))) { $log = Join-Path $script:DataRoot 'logs\deployment-error.log' }
        Add-Content -LiteralPath $log -Value ((Get-Date -Format o) + ' ' + $message) -Encoding UTF8
        Write-Host "Error summary: $log"
    } catch { Write-Host 'Could not write an error summary; use the terminal output above.' }
}

function Enter-OperationLock {
    $path = Join-Path $script:DataRoot 'server-operation.lock'
    try { return [IO.FileStream]::new($path, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None, 4096, [IO.FileOptions]::DeleteOnClose) }
    catch { throw 'Another Cafe LUX start/stop operation is in progress, or the data directory is not writable. Retry after it completes.' }
}

function Save-ProcessRecord($Record) {
    $temporary = $script:ProcessRecord + '.tmp'
    $Record | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $script:ProcessRecord -Force
}

function Test-RunCommand([string]$CommandLine, [bool]$Legacy = $false) {
    $path = [regex]::Escape((Join-Path $AppRoot 'run.py'))
    if ($Legacy) { return $CommandLine -match '(?i)(?:^|\s)run\.py(?:\s|$)' }
    return $CommandLine -match ('(?i)(?:^|\s)(?:"' + $path + '"|' + $path + ')(?:\s|$)')
}

function Assert-OwnedProcess($ProcessId, $Started, $Executable, [bool]$Legacy = $false) {
    $owned = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (!$owned) { return $null }
    $info = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId"
    $sameStart = $owned.StartTime.ToUniversalTime().Ticks.ToString() -eq [string]$Started
    if (!$sameStart) { $sameStart = $owned.StartTime.ToUniversalTime().ToString('o') -eq [string]$Started }
    if (!$sameStart -or !$info -or $info.ExecutablePath -ne $Executable -or !(Test-RunCommand $info.CommandLine $Legacy)) { throw 'Process identity mismatch. Refusing to stop an unrelated process. Inspect the saved process record; never kill by port or process name.' }
    return $owned
}

function Find-Worker($LauncherId) {
    # CPython Windows venv redirectors may spawn a child interpreter. Never assume the launcher PID serves HTTP.
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $LauncherId")
    foreach ($child in $children) {
        if (Test-RunCommand $child.CommandLine) {
            $worker = Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
            if ($worker) { return @{ Id = $worker.Id; Started = $worker.StartTime.ToUniversalTime().Ticks.ToString(); Executable = $child.ExecutablePath } }
        }
    }
    return $null
}
