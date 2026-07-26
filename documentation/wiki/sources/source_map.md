# Source map used for this draft

This wiki draft was prepared from the project repositories and vendor documents available in the project context.

## Code and guide repositories

| Source | What was used |
|---|---|
| `EitanKay/SLM_controller/README.md` | Windows setup, run commands, hardware list, offline package, repo layout |
| `EitanKay/SLM_controller/scripts/calibration/README.md` | active calibration workflow, directory layout, scan/notebook process |
| `EitanKay/SLM_controller/scripts/calibration/calibration_scan.py` | current scan constants, raw16 TIFF capture, disabled calibration during scan |
| `EitanKay/SLM_controller/scripts/calibration/generate_slm_calibration_frames.py` | Meadowlark 16-bit DVI RGB packing, optional manual BMP generation |
| `EitanKay/SLM_controller/src/slm_512_driver.py` | SDK path, LUT/WFC loading, calibration enable behavior, pattern handling |
| `EitanKay/SLM_controller/src/thorcam_camera_driver.py` | ThorImageCAM DLL path, exposure/gain/raw16/scaled8 behavior |
| `EitanKay/SLM-presentation/Presenation.tex` | curated high-level explanations, system workflow, limitations, calibration story, future work |
| `EitanKay/SLM-Guide/BookTemplate.tex` | relationship to longer hand-over guide / Overleaf structure |

## Vendor documents

| Source | What was used |
|---|---|
| Meadowlark Standard 512 DVI User Manual | DVI operation, LUT concept, image format, polarization, diffraction, cleaning cautions |
| Meadowlark 512×512 datasheet | main specs: 512×512, 15 µm pitch, 16-bit controller option, response-time/order-efficiency context |
| Meadowlark SLM overview / XY Series docs | general SLM principle, DVI limitations, calibration wavelength dependence, diffraction efficiency concepts |

## Unverified / intentionally left as TODO

- exact SLM serial number;
- final installed LUT/WFC filename;
- final optical distances;
- final camera model/serial;
- final known-good camera settings;
- final validated HG/TEM results;
- final fiber-coupling conclusion.
