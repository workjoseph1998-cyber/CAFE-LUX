. "$PSScriptRoot\common.ps1"
Set-Location $AppRoot
if (!$env:CAFE_LUX_ALLOWED_HOSTS) { throw 'Set CAFE_LUX_ALLOWED_HOSTS to your public hostname and 127.0.0.1 (comma separated, no scheme).' }
if (!(Test-Path $Python)) { throw 'Run setup.bat first.' }
if (!(Test-Path (Join-Path $DataRoot 'session.key')) -or !(Test-Path (Join-Path $DataRoot 'cafe.sqlite3'))) { throw 'Missing initialized data. Run setup.bat and create an administrator.' }
if (Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue) { throw 'Port 8000 is occupied. Stop your previous app yourself. Nothing was terminated.' }
if (Test-Path $ProcessRecord) { throw 'Process record already exists. Run stop.bat or inspect docs/WINDOWS.md for stale records.' }
$env:CAFE_LUX_TRUST_PROXY = '1'
Remove-Item Env:CAFE_LUX_INSECURE_LOCAL -ErrorAction SilentlyContinue
$process = Start-Process -FilePath $Python -ArgumentList 'run.py' -WorkingDirectory $AppRoot -PassThru -RedirectStandardOutput (Join-Path $DataRoot 'logs\stdout.log') -RedirectStandardError (Join-Path $DataRoot 'logs\stderr.log')
$process.Refresh()
@{ Id = $process.Id; Started = $process.StartTime.ToUniversalTime().ToString('o'); Python = $Python; App = $AppRoot } | ConvertTo-Json | Set-Content $ProcessRecord
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Milliseconds 500
    $process.Refresh()
    if ($process.HasExited) { Remove-Item $ProcessRecord; throw 'Café LUX exited. Inspect data\logs\stderr.log.' }
    try {
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200 -and $response.Content.Contains('CAFÉ LUX')) { Write-Host 'Café LUX ready on 127.0.0.1:8000. Check HTTPS through IIS before accepting orders.'; exit 0 }
    } catch { }
}
throw 'Readiness failed. Inspect logs; run stop.bat to stop only the recorded Café LUX process.'
