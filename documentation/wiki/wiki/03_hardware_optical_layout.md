# 03 — Hardware and optical layout

## Hardware inventory

| Component | Current note | 
|---|---|
| SLM head | Meadowlark 512×512 phase-only SLM | 
| Controller | Meadowlark DVI 16-bit controller | 
| Computer | Windows lab PC 
| Laser | LP730-SF15 laser diode available
| Camera | Thorlabs camera |
| Fourier lens | Used for observing diffraction/Fourier plane Adjust focal point to fit the system|
|
| Relay/telescope | Used after order selection if needed 
| Iris | Selects desired diffraction order Located at the fourier plane |
| Halfe-wave plate | Used to match the SLM's polarization |

## Basic Optical Layout

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
Iris selecting desired order
  ↓
optional telescope / relay optics
  ↓
camera or downstream experiment
```

![Holography setupe diagram](images/Holography_setup.png)

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

The SLM requires the incident beam polarization to be aligned to the correct liquid-crystal axis. If the polarization is wrong, the software may appear to work while the optical output does not respond correctly. The best way to find the correct polarization is by adjusting the half-wave plate until the intensity in the 0th order is minimal.
Practical rule: do not diagnose mode quality before checking polarization.

### Beam position

The input beam should be centered on the active SLM area. If the beam clips or uses a poor region of the aperture, mode quality will degrade.

### Incidence angle

Keep the off-axis angle as small as practical while still separating the incoming and reflected beams. A large angle increases the chance that the beam samples more than one pixel region and can reduce effective phase performance.

### Fourier-plane observation

Use the Fourier plane to debug order selection. A linear ramp should move the selected diffraction order; the iris should isolate it before downstream imaging.

### Known-good configuration record

Fill this after the final alignment:

| Setting | Known-good value |
|---|---|
| Laser current / power | 30mW |
| Polarization optics angle | Adjust s.t 0th order is minimal |
| SLM-to-Fourier-lens distance | 150mm |
| Fourier lens focal length | 150mm |
| Iris position | At Fourier plane |
| Relay/telescope lens distances | 75 / 50 mm |
| Camera exposure | minimum |
| Camera gain | default |
| LUT | 737 custom LUT |
| WFC | NONE |

## calibration Setup

TODO: Fill in calibration setup
