# SLM Calibration Workflow

This directory contains the complete active workflow for measuring the SLM
phase response and producing a wavelength-specific lookup table (LUT).

## Directory layout

```text
scripts/calibration/
|-- calibration_scan.py                 # displays patterns and captures camera TIFFs
|-- generate_slm_calibration_frames.py  # optional offline BMP frame generator
|-- calibration.ipynb                   # camera-data analysis and LUT generation
|-- reference/                          # comparison LUT used by the notebook
|-- frames/reference/                   # committed example/manual GUI frame sets
|-- frames/generated/                   # locally generated BMP frame sets (ignored)
`-- results/
    |-- current/                        # current camera captures (ignored)
    `-- analysis/                       # plots and generated LUTs (ignored)
```

The historical capture archive remains at
`output/calibration_frames backup`. It is intentionally not part of the active
workflow and is not changed by the scripts here.

## Prerequisites

- A Meadowlark 512 x 512 DVI SLM and its Blink SDK must be installed.
- A supported Thorlabs camera and the ThorImageCAM runtime must be available.
- The laser, polarization, Fourier lens, and camera must be aligned so the
  selected diffraction/fringe signal is measurable without saturation.
- Install the repository Python dependencies, then run commands from the
  repository root.

Before measuring a new response, decide which LUT state is being
characterized. The scan explicitly calls `slm.set_use_calibration(False)`, so
it measures the uncalibrated controller response rather than a GUI-applied
calibration LUT.

## Automated scan and analysis

1. Review the scan and camera constants near the top of
   `calibration_scan.py`, especially grating levels, stripe width, scan steps,
   exposure, and the camera DLL path.

2. Confirm the camera image is not saturated and the intended diffraction
   feature is visible. Then start the capture:

   ```powershell
   python scripts/calibration/calibration_scan.py
   ```

   The scan always clears existing `.tif` and `.tiff` files in
   `results/current` before capture. Copy a run elsewhere first if it must be
   retained. New files are named `camera_capture_<mirror_value>.tif`.

3. Open `calibration.ipynb`. Its configuration cell contains the image line
   ROI, selected brightness branch, smoothing settings, and all local paths.
   Run the notebook from top to bottom. It loads the current TIFF set, extracts
   the fringe phase, creates an inverse phase-to-brightness LUT, and writes its
   plots and `custom_slm_lut.lut` to `results/analysis`.

4. Inspect the phase and LUT plots before using the result. Copy a verified
   LUT into `slm-files/LUT_files` using a meaningful filename; that directory
   remains the GUI/package runtime location and is deliberately outside this
   calibration workspace.

## Optional manual GUI frame generation

`generate_slm_calibration_frames.py` creates Meadowlark-compatible 24-bit BMP
files. It packs each 16-bit phase value as green = most-significant byte, red =
least-significant byte, and blue = zero.

Generate a constant-mirror grating-contrast scan:

```powershell
python scripts/calibration/generate_slm_calibration_frames.py --mode constant_mirror --n 16 --mirror 32768 --scan-start 40000 --scan-stop 50000 --grating-low 0 --stripe-width 8
```

Generate a constant-grating mirror scan:

```powershell
python scripts/calibration/generate_slm_calibration_frames.py --mode constant_grating --n 32 --scan-stop 65535 --grating-low 0 --grating-high 50000 --stripe-width 8
```

Without `--out`, generated files are written to
`frames/generated/<mode>`. Supply `--out <path>` to choose another folder.
The committed historical/example sets are stored separately in
`frames/reference` and are not the default output target.

## Verification and troubleshooting

- Confirm the camera is acquiring `raw16` data and that no selected ROI clips
  the diffraction feature.
- Use the notebook's first preview plot to set the line ROI before fitting.
- If no captures are found, run the scan or update the configuration cell to a
  deliberate alternate data directory.
- If the comparison LUT cannot be loaded, confirm
  `reference/slm3324_at635_DVI.lut` exists.
- Treat a monotonic-looking inverse LUT as a necessary check, not proof of
  calibration quality; validate the installed LUT optically.

The previous generator-focused document is retained at
`old/slm_gui_calibration_frame_generator.md` for historical reference only.
