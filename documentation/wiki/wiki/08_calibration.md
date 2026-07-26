# 08 — LUT calibration

## Purpose

The LUT converts desired input pixel values into SLM/controller values that produce an approximately linear optical phase response. The LUT is wavelength-specific and must be validated optically.

## Active workflow summary

The active calibration workflow lives in:

```text
scripts/calibration/
```

Important files:

| File | Role |
|---|---|
| `calibration_scan.py` | displays calibration patterns and captures camera TIFFs |
| `calibration.ipynb` | analyzes TIFFs and generates LUT/plots |
| `generate_slm_calibration_frames.py` | optional offline BMP frame generator; historical/manual support |
| `reference/` | comparison LUT used by notebook |
| `results/current/` | current camera captures, ignored by git |
| `results/analysis/` | generated plots and LUTs, ignored by git |

## Before calibrating

Confirm:

- laser wavelength is known;
- polarization is correct;
- SLM is aligned and not clipping;
- Fourier/fringe signal is visible;
- camera image is not saturated;
- selected ROI captures the relevant signal;
- repository commit is recorded;
- old captures are copied elsewhere if they must be preserved.

## Important current behavior

The scan script calls:

```python
slm.set_use_calibration(False)
```

This means the scan measures the uncalibrated controller response rather than a GUI-applied calibrated response. Be explicit about this in every calibration record.

## Calibration procedure

1. Review constants at the top of `calibration_scan.py`:

   - `GRATING_LOW`
   - `GRATING_HIGH`
   - `STRIPE_WIDTH_PX`
   - `SPLIT_X`
   - `GRATING_AXIS`
   - `SCAN_STEPS`
   - `EXPOSURE_TIME_MS`
   - `DLL_PATH`

2. Confirm the calibration feature is visible and not saturated.

3. Run from the repo root:

   ```powershell
   python scripts/calibration/calibration_scan.py
   ```

4. The scan clears old `.tif`/`.tiff` files in `scripts/calibration/results/current` before capture.

5. Open and run:

   ```text
   scripts/calibration/calibration.ipynb
   ```

6. Inspect:

   - raw image previews;
   - ROI choice;
   - extracted phase curve;
   - smoothed result;
   - inverse LUT;
   - comparison to reference LUT.

7. Copy only a validated LUT into:

   ```text
   slm-files/LUT_files/
   ```

8. Use a meaningful filename:

   ```text
   slm3324_737nm_YYYYMMDD_operator_method.lut
   ```

9. Validate optically before calling it “working.”

## Optical validation suggestions

Use at least:

- flat phase;
- linear ramp / grating efficiency check;
- vortex phase with selected order;
- one simple HG mode, e.g. HG10;
- camera saturation check.

## Calibration record template

See [`../calibration_records/calibration_record_template.md`](../calibration_records/calibration_record_template.md).

## Historical/manual frame generation

`generate_slm_calibration_frames.py` can generate Meadowlark-compatible 24-bit BMP files. This is useful for documentation and fallback/manual workflows, but it is not the preferred active calibration route.

The Meadowlark DVI 16-bit packing used by the generator is:

```text
Green = 8 most significant bits
Red   = 8 least significant bits
Blue  = ignored / 0
```

Use the automated scan + notebook workflow first unless there is a specific reason not to.
