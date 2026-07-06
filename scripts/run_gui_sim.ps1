$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Virtual environment not found. Run .\scripts\setup_windows.ps1 first."
}

Set-Location $RepoRoot
& $PythonExe -m src.slm_gui.app --sim
