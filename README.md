# SLM Project

Optics and control code for a Meadowlark 512x512 SLM system with a DVI 16-bit controller and Thorlabs camera.

## Fresh Windows Computer Setup

Target environment:

- Windows lab computer
- 64-bit Python 3.12
- Meadowlark Blink DVI SDK installed at:

```text
C:\Program Files\Meadowlark Optics\Blink DVI\SDK
```

The Meadowlark SDK installer is legacy vendor software supplied by Meadowlark customer support or lab-managed storage. Do not commit the installer, SDK DLLs, or vendor archives to this repository unless Meadowlark explicitly grants redistribution permission.

After installing the SDK, verify this file exists:

```text
C:\Program Files\Meadowlark Optics\Blink DVI\SDK\Blink_C_wrapper.dll
```

Then set up Python from PowerShell:

```powershell
.\scripts\setup_windows.ps1
```

Run the GUI with hardware:

```powershell
.\scripts\run_gui.ps1
```

Run the GUI in simulator mode, which does not require the Meadowlark SDK or hardware:

```powershell
.\scripts\run_gui_sim.ps1
```

Check the current machine setup:

```powershell
.\.venv\Scripts\python.exe scripts\check_hardware_setup.py
```

## Offline Executable Package

To build a thumb-drive package for an offline Windows computer, use 64-bit
Python on the build computer. Python 3.12 x64 is recommended for the most
predictable PyInstaller behavior, but the build script will also allow other
64-bit Python versions.

Install build dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
```

Build the folder bundle and zip:

```powershell
.\scripts\build_offline_gui.ps1
```

The build output is:

```text
dist\SLMControl\SLMControl.exe
dist\SLMControl.zip
```

The zip includes the GUI executable, bundled Python runtime, Python
dependencies, LUT files, and `slm-files\WFC_files\black.bmp`. It does not
include Meadowlark or Thorlabs vendor SDK installers/drivers. The offline
computer must still have the Meadowlark Blink DVI SDK installed at:

```text
C:\Program Files\Meadowlark Optics\Blink DVI\SDK
```

## Hardware

- Meadowlark 512x512 SLM
- DVI 16-bit controller
- LP730-SF15 laser diode
- Thorlabs camera
- Fourier lens / calibration optics

## Main Goals

1. Generate phase masks and calibration frames.
2. Control/display frames on the SLM.
3. Capture camera images.
4. Build LUT calibration workflow for the operating wavelength.
5. Document optical alignment and calibration procedures.

## Repository Structure

- `src/` - reusable Python modules
- `scripts/` - runnable scripts and setup helpers
- `documentation/` - project documentation
- `notebooks/` - analysis notebooks
- `slm-files/` - LUTs and local SLM assets
- `tests/` - automated tests
