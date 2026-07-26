# 03 — Hardware and optical layout

## Hardware inventory

| Component | Current note | Fill in / verify |
|---|---|---|
| SLM head | Meadowlark 512×512 phase-only SLM | Serial number: TODO |
| Controller | Meadowlark DVI 16-bit controller | Exact model: TODO |
| Computer | Windows lab PC | GPU/display configuration: TODO |
| Laser | LP730-SF15 laser diode available | Operating wavelength: TODO |
| Camera | Thorlabs camera | Exact model + serial: TODO |
| Fourier lens | Used for observing diffraction/Fourier plane | Focal length: TODO |
| Relay/telescope | Used after order selection if needed | Lens pair/distances: TODO |
| Iris | Selects desired diffraction order | Location: Fourier plane |

## Current optical layout

```text
laser diode
  ↓
collimation and polarization optics
  ↓
SLM, slight off-axis incidence
  ↓
Fourier lens
  ↓
Fourier plane / diffraction orders
  ↓
iris selecting desired order
  ↓
optional telescope / relay optics
  ↓
camera or downstream experiment
```

Add photos here:

- `diagrams/beam_path_photo_annotated.png`
- `diagrams/slm_mount_photo_annotated.png`
- `diagrams/fourier_plane_photo_annotated.png`

## Electrical / computer connections

```text
Control PC second display / DVI output
  ↔ Meadowlark DVI controller
  ↔ custom/ribbon cable
  ↔ SLM optical head
```

```text
Control PC USB
  ↔ Thorlabs camera
```

## Alignment-critical conditions

### Polarization

Phase-only operation requires the incident beam polarization to be aligned to the correct liquid-crystal axis. If the polarization is wrong, the software may appear to work while the optical output does not respond correctly.

Practical rule: do not diagnose mode quality before checking polarization.

### Beam position

The input beam should be centered on the active SLM area. If the beam clips or uses a poor region of the aperture, mode quality will degrade.

Record:

| Quantity | Value |
|---|---|
| Beam diameter on SLM | TODO |
| Beam center relative to SLM | TODO |
| Incidence angle | TODO |
| SLM rotation | TODO |

### Incidence angle

Keep the off-axis angle as small as practical while still separating the incoming and reflected beams. A large angle increases the chance that the beam samples more than one pixel region and can reduce effective phase performance.

### Fourier-plane observation

Use the Fourier plane to debug order selection. A linear ramp should move the selected diffraction order; the iris should isolate it before downstream imaging.

## Known-good configuration record

Fill this after the final alignment:

| Setting | Known-good value |
|---|---|
| Laser current / power | TODO |
| Polarization optics angle | TODO |
| SLM incidence angle | TODO |
| SLM-to-Fourier-lens distance | TODO |
| Fourier lens focal length | TODO |
| Iris position | TODO |
| Relay/telescope lens distances | TODO |
| Camera exposure | TODO |
| Camera gain | TODO |
| LUT | TODO |
| WFC | TODO |
