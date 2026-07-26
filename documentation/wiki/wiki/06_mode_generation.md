# 06 — Mode generation

## Core idea

The SLM is phase-only. It does not directly paint the desired output intensity. Instead, it modifies the wavefront so that after propagation, diffraction, Fourier filtering, or holographic encoding, the desired pattern appears approximately in the selected plane/order.

## Basic modes and tasks

| Task | Starting mask | What to look for |
|---|---|---|
| sanity check | flat phase | strong zero order |
| steering | linear ramp | shifted diffraction order |
| focus/defocus | quadratic phase | shifted focal plane |
| vortex | helical phase + carrier | donut in selected order |
| HG/TEM mode | encoded HG/TEM mask + carrier | expected lobes in selected order |
| target pattern | GS/holographic mask + carrier | approximate target intensity |

## Beam steering

A linear phase ramp acts as a grating. It shifts the desired diffraction order away from the zero order. Use this when you need to separate the useful order from residual unmodulated light.

Procedure:

1. Display flat mask.
2. Locate zero order.
3. Add a small linear ramp.
4. Locate shifted first order.
5. Increase/decrease ramp frequency as needed.
6. Use iris to isolate selected order.

## Vortex beams

A helical phase wraps around the beam axis. A clean vortex should show a central intensity null, but only after correct order selection and alignment.

If the result is a spot:

- you may be looking at the zero order;
- the selected order may not be isolated;
- the LUT may not provide a full 2π response at the operating wavelength;
- the beam may be off-center;
- the camera may not be in the intended plane.

## HG/TEM modes

Recommended starting point:

1. Reproduce TEM00 / Gaussian-like baseline.
2. Try HG10 or HG01.
3. Try HG11.
4. Only then attempt higher order modes.

For each mode, record:

| Field | Value |
|---|---|
| Mode | TODO |
| Waist parameter | TODO |
| Rotation | TODO |
| Carrier/ramp | TODO |
| LUT/WFC | TODO |
| Camera exposure/gain | TODO |
| Output image filename | TODO |
| Notes | TODO |

## Gerchberg–Saxton / holography

The GS idea:

1. Start with a target intensity in the output plane.
2. Alternate between SLM plane and output plane using Fourier transforms.
3. Enforce the known amplitude constraint in each plane.
4. Keep only the phase at the SLM plane.
5. Display that phase mask and verify experimentally.

Use GS/holography when an approximate target intensity is sufficient. Do not expect exact arbitrary complex-field control from a phase-only SLM without additional constraints or optical encoding.

## Recommended comparison plots

For handover records, save:

- target intensity;
- generated phase mask;
- raw camera image;
- cropped/normalized camera image;
- line cuts through the lobes;
- exposure/gain metadata.
