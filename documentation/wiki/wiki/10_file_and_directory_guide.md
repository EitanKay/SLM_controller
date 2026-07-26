# 10 — File and directory guide

## Main repositories

| Repository | Purpose |
|---|---|
| `EitanKay/SLM_controller` | Python GUI, hardware drivers, calibration scripts, packaging |
| `EitanKay/SLM-Guide` | long-form Overleaf/LaTeX hand-over guide |
| `EitanKay/SLM-presentation` | final hand-over presentation and curated visual explanations |

## Important controller paths

| Path | Meaning |
|---|---|
| `README.md` | setup, run commands, repo overview |
| `src/slm_512_driver.py` | Meadowlark Blink DVI Python wrapper |
| `src/thorcam_camera_driver.py` | Thorlabs camera wrapper |
| `src/slm_gui/` | GUI application |
| `scripts/setup_windows.ps1` | Windows virtualenv/dependency setup |
| `scripts/run_gui.ps1` | launch GUI with hardware |
| `scripts/run_gui_sim.ps1` | launch GUI simulator |
| `scripts/check_hardware_setup.py` | verify local installation/hardware assumptions |
| `scripts/build_offline_gui.ps1` | build offline GUI bundle |
| `scripts/calibration/README.md` | active calibration workflow |
| `scripts/calibration/calibration_scan.py` | active scan/capture script |
| `scripts/calibration/calibration.ipynb` | active analysis/LUT notebook |
| `scripts/calibration/generate_slm_calibration_frames.py` | optional/manual BMP generator |
| `slm-files/LUT_files/` | runtime LUT location |
| `slm-files/WFC_files/` | runtime WFC location |

## What should be committed

Commit:

- source code;
- Markdown documentation;
- small example/test patterns;
- calibration records;
- analysis scripts;
- final selected LUTs/WFCs if redistribution/storage is allowed by lab policy.

Do not casually commit:

- vendor installers;
- SDK DLLs;
- huge raw camera scans;
- temporary analysis outputs;
- private lab credentials;
- unclear binary files without a README.

## Naming conventions

Suggested LUT filename:

```text
slm<serial>_<wavelength>nm_<YYYYMMDD>_<operator>_<method>.lut
```

Suggested calibration capture archive:

```text
calibration_<wavelength>nm_<YYYYMMDD>_<short-note>/
```

Suggested output image filename:

```text
<YYYYMMDD>_<mode>_<lut>_<exposure>ms_raw16.tif
```
