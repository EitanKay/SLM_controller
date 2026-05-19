# SLM Project

Optics and control code for a Meadowlark 512x512 SLM system.

## Hardware

- Meadowlark 512x512 SLM
- DVI 16-bit controller
- LP730-SF15 laser diode
- Thorlabs camera
- Fourier lens / calibration optics

## Main goals

1. Generate phase masks and calibration frames.
2. Control/display frames on the SLM.
3. Capture camera images.
4. Build LUT calibration workflow for the operating wavelength.
5. Document optical alignment and calibration procedures.

## Repository structure

- `src/` — reusable Python modules
- `scripts/` — runnable scripts
- `docs/` — project documentation
- `notebooks/` — analysis notebooks
- `data/` — local measurement data, mostly ignored
- `outputs/` — generated files, ignored