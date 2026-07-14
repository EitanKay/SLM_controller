$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$SpecPath = Join-Path $RepoRoot "packaging\SLMControl.spec"
$DistDir = Join-Path $RepoRoot "dist"
$BundleDir = Join-Path $DistDir "SLMControl"
$ZipPath = Join-Path $DistDir "SLMControl.zip"

if (-not (Test-Path $PythonExe)) {
    throw "Virtual environment not found. Run .\scripts\setup_windows.ps1 first, then install build requirements."
}

Set-Location $RepoRoot

& $PythonExe -c "import struct; raise SystemExit(0 if struct.calcsize('P') == 8 else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Offline builds require 64-bit Python."
}

& $PythonExe -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Python 3.12 x64 is recommended for offline builds. Continuing with the current 64-bit Python."
}

& $PythonExe -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed. Run: .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt"
}

if (Test-Path $BundleDir) {
    Remove-Item -LiteralPath $BundleDir -Recurse -Force
}
if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

& $PythonExe -m PyInstaller --clean --noconfirm $SpecPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

Copy-Item -LiteralPath (Join-Path $RepoRoot "packaging\README_OFFLINE.txt") -Destination (Join-Path $BundleDir "README_OFFLINE.txt") -Force

for ($attempt = 1; $attempt -le 5; $attempt++) {
    try {
        if (Test-Path $ZipPath) {
            Remove-Item -LiteralPath $ZipPath -Force
        }
        Start-Sleep -Seconds $attempt
        Compress-Archive -LiteralPath $BundleDir -DestinationPath $ZipPath -Force -ErrorAction Stop
        break
    } catch {
        if ($attempt -eq 5) {
            throw "Failed to create $ZipPath after $attempt attempts: $($_.Exception.Message)"
        }
        Write-Warning "Zip attempt $attempt failed because a file may still be locked. Retrying..."
    }
}

Write-Host ""
Write-Host "Offline GUI package created:"
Write-Host $ZipPath
