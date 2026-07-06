$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $RepoRoot ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

function Find-Python312 {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        try {
            & py -3.12 -c "import sys, struct; raise SystemExit(0 if struct.calcsize('P') == 8 else 1)"
            if ($LASTEXITCODE -eq 0) {
                return @("py", "-3.12")
            }
        } catch {
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        try {
            & python -c "import sys, struct; raise SystemExit(0 if sys.version_info[:2] == (3, 12) and struct.calcsize('P') == 8 else 1)"
            if ($LASTEXITCODE -eq 0) {
                return @("python")
            }
        } catch {
        }
    }

    throw "Python 3.12 x64 was not found. Install 64-bit Python 3.12, then rerun this script."
}

Set-Location $RepoRoot
$PythonCommand = Find-Python312
$PythonProgram = $PythonCommand[0]
$PythonArgs = @()
if ($PythonCommand.Length -gt 1) {
    $PythonArgs = $PythonCommand[1..($PythonCommand.Length - 1)]
}

if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating virtual environment at $VenvPath"
    & $PythonProgram @PythonArgs -m venv $VenvPath
}

Write-Host "Upgrading pip"
& $PythonExe -m pip install --upgrade pip

Write-Host "Installing runtime dependencies"
& $PythonExe -m pip install -r (Join-Path $RepoRoot "requirements.txt")

Write-Host ""
Write-Host "Setup complete."
Write-Host "Run hardware GUI: .\scripts\run_gui.ps1"
Write-Host "Run simulator GUI: .\scripts\run_gui_sim.ps1"
Write-Host "Check hardware setup: .\.venv\Scripts\python.exe scripts\check_hardware_setup.py"
