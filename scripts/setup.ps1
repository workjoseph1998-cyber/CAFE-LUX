. "$PSScriptRoot\common.ps1"
try {
    Set-Location -LiteralPath $AppRoot
    Write-Step '1/6 - Find supported Python and create/verify virtual environment'
    if (!(Test-Path -LiteralPath $Python)) {
        $bootstrap = Find-Python
        $executable = $bootstrap.Executable
        $prefixArguments = $bootstrap.Prefix
        & $executable @prefixArguments -m venv --without-pip (Join-Path $AppRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed. Check Python venv support, permissions and free disk space.' }
    }
    if (!(Test-SupportedPython $Python)) { throw 'Existing .venv uses unsupported or broken Python. Stop Cafe LUX, rename .venv to .venv.old, then rerun setup. Never remove the separate data directory.' }
    Write-Step '2/6 - Initialize persistent non-secret installation configuration and data directories'
    Invoke-CheckedPython -Arguments @($Manager, 'init-config')
    Read-Installation
    Write-Host "Application: $AppRoot"
    Write-Host "Data: $script:DataRoot"
    Write-Step '3/6 - Verify pip and install pinned application dependencies'
    $hasPip = $false
    try { & $Python -m pip --version; $hasPip = $LASTEXITCODE -eq 0 } catch { $hasPip = $false }
    if (!$hasPip) {
        Write-Host 'Installing bundled pip into this virtual environment using ensurepip.'
        Invoke-CheckedPython -Arguments @('-m', 'ensurepip', '--upgrade', '--default-pip')
    }
    Invoke-CheckedPython -Arguments @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', (Join-Path $AppRoot 'requirements.txt'))
    Write-Step '4/6 - Verify dependency compatibility'
    Invoke-CheckedPython -Arguments @('-m', 'pip', 'check')
    Write-Step '5/6 - Initialize or migrate database without deleting existing data'
    Invoke-CheckedPython -Arguments @($Manager, 'init-db')
    Write-Step '6/6 - Verify application imports, configuration and database integrity'
    Invoke-CheckedPython -Arguments @($Manager, 'check')
    Write-Host 'SETUP COMPLETE. Existing orders, products, accounts and uploads are preserved.'
    Write-Host 'Create an administrator: .\.venv\Scripts\python.exe manage.py init-admin'
    Write-Host 'Start: .\start.bat'
    Write-Host 'If IIS preserves your public Host header, add it with: .\.venv\Scripts\python.exe manage.py configure --host YOUR-HOSTNAME'
    Write-Host 'Production cookies require HTTPS. See docs\WINDOWS.md for localhost-only HTTP testing.'
    exit 0
} catch {
    Report-Failure $_
    exit 1
}
