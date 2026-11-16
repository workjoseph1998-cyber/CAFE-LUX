. "$PSScriptRoot\common.ps1"
$operationLock = $null
try {
    Set-Location -LiteralPath $AppRoot
    Write-Step '1/4 - Load saved installation and validate application'
    if (!(Test-Path -LiteralPath $Python)) { throw 'Virtual environment is missing. Run setup.bat first.' }
    Read-Installation
    foreach ($file in @('session.key','cafe.sqlite3')) {
        if (!(Test-Path -LiteralPath (Join-Path $script:DataRoot $file))) { throw "Missing $file in configured data directory. Run setup.bat; do not select another database accidentally." }
    }
    Invoke-CheckedPython -Arguments @($Manager, 'check')
    $operationLock = Enter-OperationLock
    Write-Step '2/4 - Refuse duplicates and check exclusive port 8000 availability'
    if (Test-Path -LiteralPath $script:ProcessRecord) { throw 'Process record exists. Run stop.bat first. If stale, follow the process-record troubleshooting steps; do not kill a process by port.' }
    Invoke-CheckedPython -Arguments @('-c', 'from run import port_available; port_available()')
    Write-Step '3/4 - Launch dedicated Waitress process on 127.0.0.1:8000'
    # Quote the absolute script path explicitly: Start-Process joins ArgumentList on Windows.
    $runScript = '"' + (Join-Path $AppRoot 'run.py') + '"'
    $stdout = Join-Path $script:DataRoot 'logs\stdout.log'
    $stderr = Join-Path $script:DataRoot 'logs\stderr.log'
    $process = Start-Process -FilePath $Python -ArgumentList @('-u', $runScript) -WorkingDirectory $AppRoot -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $process.Refresh()
    $record = @{ Id = $process.Id; Started = $process.StartTime.ToUniversalTime().Ticks.ToString(); Python = $Python; App = $AppRoot; Script = (Join-Path $AppRoot 'run.py') }
    try { Save-ProcessRecord $record }
    catch { if (!$process.HasExited) { Stop-Process -InputObject $process }; throw 'Cannot save process ownership record; stopped only the just-created Cafe LUX process.' }
    Write-Step '4/4 - Wait for application readiness'
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        $process.Refresh()
        if ($process.HasExited) {
            Remove-Item -LiteralPath $script:ProcessRecord
            throw "Waitress exited with code $($process.ExitCode). Inspect $stderr and logs\application.log in the configured data directory."
        }
        if (!$record.Worker) {
            $child = Find-Worker $process.Id
            if ($child) { $record.Worker = $child; Save-ProcessRecord $record }
        }
        try {
            $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/healthz' -UseBasicParsing -TimeoutSec 2
            $health = $response.Content | ConvertFrom-Json
            if ($response.StatusCode -eq 200 -and $health.application -eq 'cafe-lux' -and ($health.pid -eq $process.Id -or ($record.Worker -and $health.pid -eq $record.Worker.Id))) {
                Write-Host 'STARTED: Cafe LUX is responding on http://127.0.0.1:8000.'
                Write-Host 'Check your existing IIS URL. If it returns Invalid host, configure that hostname in the application; no IIS rewrite change is normally needed.'
                exit 0
            }
        } catch { }
    }
    throw "Readiness failed. Inspect $stderr. The recorded Cafe LUX process was left available for diagnosis; run stop.bat to stop only that process."
} catch {
    Report-Failure $_
    exit 1
} finally {
    if ($operationLock) { $operationLock.Dispose() }
}
