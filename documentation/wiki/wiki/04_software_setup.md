# 04 — Software setup

The software source of truth is the `EitanKay/SLM_controller` repository.

## Repository layout

Current top-level structure from the controller README:

| Path | Purpose |
|---|---|
| `src/` | reusable Python modules |
| `scripts/` | runnable scripts and setup helpers |
| `scripts/calibration/` | calibration capture, analysis, frames, and guide |
| `documentation/` | project documentation |
| `notebooks/` | analysis notebooks |
| `slm-files/` | LUTs and local SLM assets |
| `tests/` | automated tests |

## Windows setup

Target environment:

- Windows lab computer;
- 64-bit Python 3.12 recommended;
- Meadowlark Blink DVI SDK installed;
- ThorImageCAM runtime installed for the Thorlabs camera;
- repository Python dependencies installed in `.venv`.

From the repo root:

```powershell
.\scripts\setup_windows.ps1
```

The Meadowlark SDK is expected at:

```text
C:\Program Files\Meadowlark Optics\Blink DVI\SDK
```

The key DLL expected by the Python driver is:

```text
C:\Program Files\Meadowlark Optics\Blink DVI\SDK\Blink_C_wrapper.dll
```

Do not commit vendor SDK installers, DLLs, or archives unless redistribution permission is explicit.

## Health check

```powershell
.\.venv\Scripts\python.exe scripts\check_hardware_setup.py
```

Run this after moving to a new computer, changing the SDK installation, or debugging missing DLL problems.

## Run the GUI with hardware

```powershell
.\scripts\run_gui.ps1
```

This runs:

```powershell
.\.venv\Scripts\python.exe -m src.slm_gui.app
```

## Run the GUI in simulator mode

```powershell
.\scripts\run_gui_sim.ps1
```

This runs:

```powershell
.\.venv\Scripts\python.exe -m src.slm_gui.app --sim
```

Simulator mode is useful for:

- checking the GUI layout;
- testing mask-generation logic;
- working without the Meadowlark SDK or hardware.

Simulator mode is **not** optical validation.

## Offline GUI package

To build an offline Windows package:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\scripts\build_offline_gui.ps1
```

Expected outputs:

```text
dist\SLMControl\SLMControl.exe
dist\SLMControl.zip
```

The offline package includes the GUI executable, bundled Python runtime, Python dependencies, LUT files, and `slm-files\WFC_files\black.bmp`.

It does **not** include vendor SDK installers/drivers. The target computer still needs the Meadowlark Blink DVI SDK and Thorlabs runtime installed.

## Versioning rule

For every calibration or important measurement, record:

```powershell
git rev-parse HEAD
```

Paste the commit hash into the calibration/experiment record.
