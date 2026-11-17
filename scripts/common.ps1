$ErrorActionPreference = 'Stop'
$AppRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (!$env:CAFE_LUX_DATA_DIR) { $env:CAFE_LUX_DATA_DIR = 'C:\CafeLuxData' }
$DataRoot = [IO.Path]::GetFullPath($env:CAFE_LUX_DATA_DIR).TrimEnd('\')
if (![IO.Path]::IsPathRooted($env:CAFE_LUX_DATA_DIR)) { throw 'Data directory must be absolute.' }
if ($DataRoot -match '(?i)cirrus' -or $DataRoot -eq $AppRoot -or $DataRoot.StartsWith($AppRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Data directory overlaps source or protected Cirrus path.' }
if ($env:CAFE_LUX_PROTECTED_DIRS) {
    foreach ($protected in $env:CAFE_LUX_PROTECTED_DIRS.Split(';')) {
        if (!$protected) { continue }
        $p = [IO.Path]::GetFullPath($protected).TrimEnd('\')
        if ($DataRoot -eq $p -or $DataRoot.StartsWith($p + '\', [StringComparison]::OrdinalIgnoreCase) -or $p.StartsWith($DataRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Data directory overlaps a protected directory.' }
    }
}
$Python = Join-Path $AppRoot '.venv\Scripts\python.exe'
$ConfigFile = Join-Path $DataRoot 'runtime.json'
if (Test-Path $ConfigFile) {
    $runtime = Get-Content $ConfigFile -Raw | ConvertFrom-Json
    foreach ($key in @('CAFE_LUX_ALLOWED_HOSTS','CAFE_LUX_TRUST_PROXY','CAFE_LUX_INSECURE_LOCAL')) {
        $value = $runtime.$key
        if ($value -and !(Test-Path "Env:$key")) { Set-Item "Env:$key" $value }
    }
}
$ProcessRecord = Join-Path $DataRoot 'server-process.json'
