. "$PSScriptRoot\common.ps1"
if (!(Test-Path $ProcessRecord)) { Write-Host 'No Café LUX process record. No process was stopped.'; exit 0 }
$record = Get-Content $ProcessRecord -Raw | ConvertFrom-Json
$process = Get-Process -Id $record.Id -ErrorAction SilentlyContinue
if (!$process) { Remove-Item $ProcessRecord; Write-Host 'Removed stale process record.'; exit 0 }
$info = Get-CimInstance Win32_Process -Filter "ProcessId = $($record.Id)"
if ($process.StartTime.ToUniversalTime().ToString('o') -ne $record.Started -or $info.ExecutablePath -ne $record.Python -or $record.App -ne $AppRoot -or $info.CommandLine -notmatch 'run\.py') { throw 'Process identity mismatch. Refusing to stop an unrelated process.' }
Write-Host 'Before stopping: disable orders and drain active requests through IIS as described in docs/WINDOWS.md.'
Stop-Process -Id $record.Id
Wait-Process -Id $record.Id -ErrorAction SilentlyContinue
Remove-Item $ProcessRecord
Write-Host 'Recorded Café LUX process stopped. No other application was changed.'
