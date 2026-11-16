. "$PSScriptRoot\common.ps1"
$operationLock = $null
try {
    Set-Location -LiteralPath $AppRoot
    Write-Step '1/2 - Load installation and verify owned process identities'
    if (!(Test-Path -LiteralPath $Python)) { throw 'Virtual environment is missing. Restore this installation before using its stop script.' }
    Read-Installation
    $operationLock = Enter-OperationLock
    if (!(Test-Path -LiteralPath $script:ProcessRecord)) { Write-Host 'No Cafe LUX process record. No process was stopped.'; exit 0 }
    $record = Get-Content -LiteralPath $script:ProcessRecord -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($record.Python -ne $Python -or $record.App -ne $AppRoot) { throw 'Process record belongs to another installation. Nothing was stopped.' }
    $legacy = !$record.Script
    $launcher = Assert-OwnedProcess $record.Id $record.Started $record.Python $legacy
    $worker = $null
    if ($record.Worker) {
        $worker = Assert-OwnedProcess $record.Worker.Id $record.Worker.Started $record.Worker.Executable
    } elseif ($launcher) {
        if (!$legacy) {
            $child = Find-Worker $launcher.Id
            if ($child) { $worker = Assert-OwnedProcess $child.Id $child.Started $child.Executable }
        }
    }
    # Verify all identities before terminating any process. PID reuse/unknown ownership fails closed.
    Write-Step '2/2 - Stop only verified Cafe LUX interpreter and launcher'
    Write-Host 'Orders should be disabled and active requests drained through IIS before stopping. See docs\WINDOWS.md.'
    if ($worker -and (!$launcher -or $worker.Id -ne $launcher.Id)) {
        Stop-Process -InputObject $worker -ErrorAction Stop
        if (!$worker.WaitForExit(10000)) { throw 'Owned interpreter did not exit. Process record retained.' }
    }
    if ($launcher) {
        $launcher.Refresh()
        if (!$launcher.HasExited) { Stop-Process -InputObject $launcher -ErrorAction Stop }
        if (!$launcher.WaitForExit(10000)) { throw 'Owned launcher did not exit. Process record retained.' }
    }
    Remove-Item -LiteralPath $script:ProcessRecord
    Write-Host 'STOPPED: only the recorded Cafe LUX process(es). IIS and other applications were not changed.'
    exit 0
} catch {
    Report-Failure $_
    exit 1
} finally {
    if ($operationLock) { $operationLock.Dispose() }
}
