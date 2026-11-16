$ErrorActionPreference = 'Stop'
$AppRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (!$env:CAFE_LUX_DATA_DIR) { throw 'Set CAFE_LUX_DATA_DIR to a dedicated path, e.g. D:\CafeLUXData. Do not use Cirrus storage.' }
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
$ProcessRecord = Join-Path $DataRoot 'server-process.json'
