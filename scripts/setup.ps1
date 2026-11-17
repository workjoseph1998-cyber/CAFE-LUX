. "$PSScriptRoot\common.ps1"
Set-Location $AppRoot
if (!(Test-Path $Python)) {
    $candidate = $null
    foreach ($command in @('py','python','python3')) {
        if (!(Get-Command $command -ErrorAction SilentlyContinue)) { continue }
        $arguments = @('-c', 'import sys; print(sys.executable) if sys.version_info >= (3,11) else sys.exit(1)')
        if ($command -eq 'py') { $arguments = @('-3') + $arguments }
        $resolved = & $command @arguments
        if ($LASTEXITCODE -eq 0) { $candidate = $resolved; break }
    }
    if (!$candidate) { throw 'Install Python 3.11 or newer with the Python launcher.' }
    & $candidate -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $Python -m flask --app cafe:create_app init-db
if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed.' }
Write-Host 'Database ready; existing data preserved. No accounts or starter products added automatically.'
Write-Host 'Fresh installation only: .venv\Scripts\python.exe manage.py init-admin (reuse existing accounts on upgrade).'
Write-Host 'Use restrictive NTFS permissions on the data directory. See docs/WINDOWS.md.'

if (!(Test-Path $ConfigFile)) {
    @{ CAFE_LUX_ALLOWED_HOSTS = 'localhost,127.0.0.1,172.18.69.59'; CAFE_LUX_INSECURE_LOCAL = '1' } | ConvertTo-Json | Set-Content $ConfigFile
}
Write-Host 'Existing runtime configuration preserved. Check runtime.json; local HTTP mode must not be used for future public HTTPS.'
