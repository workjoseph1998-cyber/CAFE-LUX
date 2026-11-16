. "$PSScriptRoot\common.ps1"
Set-Location $AppRoot
if (!(Test-Path $Python)) {
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 x64 with the Windows launcher.' }
}
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $Python -m flask --app cafe:create_app init-db
if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed.' }
Write-Host 'Database ready. No default admin or products are published.'
Write-Host 'Create an admin: .venv\Scripts\python.exe -m flask --app cafe:create_app create-admin'
Write-Host 'Use restrictive NTFS permissions on the data directory. See docs/WINDOWS.md.'
