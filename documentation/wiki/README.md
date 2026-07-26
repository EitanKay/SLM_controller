# SLM Project Wiki

This is a small hand-over wiki for the Meadowlark 512×512 SLM project in the Bekenstein Lab.
It is meant to sit next to the codebase and the longer Overleaf guide, not to replace them.

## Who this is for

1. A new lab user who wants to operate the SLM system safely and reliably.
2. A future maintainer who needs to troubleshoot, recalibrate, modify, or rebuild the setup.

## Start here

- [`wiki/00_quick_start.md`](wiki/00_quick_start.md) — shortest path to seeing a diffracted spot.
- [`wiki/01_safety_and_scope.md`](wiki/01_safety_and_scope.md) — what not to assume, especially LUT/wavelength dependence.
- [`wiki/03_hardware_optical_layout.md`](wiki/03_hardware_optical_layout.md) — current known hardware and alignment-critical conditions.
- [`wiki/04_software_setup.md`](wiki/04_software_setup.md) — Windows/Python/SDK setup and run commands.
- [`wiki/08_calibration.md`](wiki/08_calibration.md) — active LUT calibration workflow.
- [`wiki/09_troubleshooting.md`](wiki/09_troubleshooting.md) — symptom → likely causes → checks → corrective actions.

## Current system snapshot

| Item | Current note |
|---|---|
| SLM | Meadowlark 512×512 phase-only LCoS SLM |
| Controller | Meadowlark DVI 16-bit controller |
| Camera | Thorlabs camera, controlled through ThorImageCAM / pylablib |
| Main software repo | `EitanKay/SLM_controller` |
| Main guide repo | `EitanKay/SLM-Guide` |
| Presentation repo | `EitanKay/SLM-presentation` |
| Routine GUI command | `.\scripts\run_gui.ps1` from the controller repo root |
| Simulator GUI command | `.\scripts\run_gui_sim.ps1` from the controller repo root |
| Active calibration entry point | `scripts/calibration/README.md` |
| Known warning | LUTs are wavelength-specific; do not assume a 635 nm LUT is correct at 737 nm. |

> Note: Replace every `TODO` with the real lab value before treating this as final documentation.

## Wiki philosophy

Keep this small and practical. Every page should answer one of two questions:

- How do I reproduce the working state?
- What should I not waste two weeks rediscovering?

Avoid hiding important operational knowledge in slide decks, notebooks, or private messages. If it matters for the next user, put it here.
