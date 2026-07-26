# 02 — System overview

## What the SLM is

The SLM is a two-dimensional array of independently controlled pixels. In this setup it is used as a reflective, phase-only spatial light modulator: each pixel changes the phase delay of the reflected laser light.

In practical terms, a **phase mask** is an image sent from the computer to the SLM. The image encodes a spatial phase pattern across the beam.

## What “phase-only” means here

Ideally, the SLM does not directly set the output intensity at each point. Instead, it sets a spatial phase. The desired output intensity appears after propagation, diffraction, Fourier filtering, or holographic encoding.

Useful consequences:

- a linear phase ramp acts like a grating and steers light;
- a quadratic phase acts like a lens;
- a helical phase can produce a vortex beam;
- iterative holography can approximate target intensity patterns.

Important limitations:

- direct intensity control is not available without optical encoding;
- the input beam still determines the available power and spatial support;
- polarization must be matched to the liquid-crystal axis;
- a zero order and other diffraction orders remain;
- calibration is wavelength-specific.

## System-level flow

```text
laser → collimation / polarization → SLM → Fourier lens → iris/order selection → relay/telescope → camera or experiment
```

Control and measurement flow:

```text
Python GUI → Meadowlark DVI SDK/controller → SLM head
camera → Thorlabs/ThorImageCAM runtime → Python acquisition/analysis
```

## Mask → optical effect map

| Phase mask | Expected optical effect | Common use |
|---|---|---|
| Flat / constant | Mostly zero order | sanity check |
| Linear ramp / blazed grating | Shifts a diffraction order | order selection / steering |
| Quadratic phase | Adds focusing/defocusing | programmable lens |
| Helical phase | Vortex with central intensity null, after correct order selection | OAM/vortex test |
| HG/TEM encoded mask | Approximate transverse mode | lab delivery mode |
| GS/holographic phase | Approximate target intensity in Fourier plane | arbitrary-ish patterns |

## What to verify before trusting a result

1. Camera is not saturated.
2. Correct diffraction order is selected.
3. Polarization is correct.
4. Beam is centered on the active SLM area.
5. LUT and WFC are intentional.
6. The same simple test pattern still behaves as expected.
