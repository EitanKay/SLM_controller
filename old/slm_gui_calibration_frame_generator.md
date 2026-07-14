# Meadowlark SLM GUI Calibration Frame Generator

## Goal

Before using the proper Meadowlark SDK, we want to test an SLM phase-calibration workflow using the existing **Blink DVI GUI**.

The script `generate_slm_calibration_frames.py` generates calibration frame sequences as **512×512 24-bit BMP files** that can be loaded by the Meadowlark DVI GUI.

The target SLM/controller is a Meadowlark 512×512 phase SLM with a **DVI 16-bit controller**.

---

## Meadowlark DVI bitmap format

The Meadowlark DVI controller is a 16-bit system, but the GUI typically loads **24-bit bitmap images**.

The 16-bit pixel value is packed into RGB as:

```text
Green channel = 8 most significant bits
Red channel   = 8 least significant bits
Blue channel  = ignored, set to 0
```

So for a 16-bit value

```text
value16 = 0 ... 65535
```

we write:

```python
red   = value16 & 0x00FF
green = value16 >> 8
blue  = 0
```

This produces GUI-compatible 24-bit BMPs while still addressing the 16-bit phase levels of the SLM.

Important: do **not** save these as ordinary 16-bit grayscale BMPs. The GUI expects the 24-bit red/green packing.

---

## Frame geometry

Each frame is a 512×512 image split vertically:

```text
+----------------------+----------------------+
|                      |                      |
|   Left half          |   Right half         |
|                      |                      |
|   constant mirror    |   binary grating     |
|   phase              |   phase pattern      |
|                      |                      |
+----------------------+----------------------+
```

Default split:

```python
split_x = 256
```

So:

```python
frame[:, :256]  = mirror_value
frame[:, 256:] = grating
```

The left side acts as a flat phase reference.

The right side acts as a diffractive grating.

---

## Physics idea

The SLM is phase-only when the input polarization is aligned correctly with the liquid-crystal axis.

A constant phase region behaves like a mirror:

```math
E_L(x,y) = A_L e^{i\phi_m}
```

The grating region behaves like a periodic phase mask:

```math
E_R(x,y) = A_R e^{i\phi_g(x)}
```

where `phi_g(x)` alternates between two phase values.

Because the right half is periodic, it sends light into diffraction orders. In the Fourier plane of a lens, the grating produces separated diffraction spots/orders.

The left half produces a reference contribution. The two halves interfere in the Fourier plane. Changing the phase of the constant mirror side changes the relative phase between the reference and the grating contribution.

This causes the measured fringe/intensity pattern to shift or oscillate. By scanning the mirror brightness value and recording the camera intensity, we can infer the mapping:

```text
SLM input gray value → optical phase
```

This is the basis for generating a LUT.

---

## Why two scan modes?

There are two generated calibration modes.

---

## Mode A: constant mirror, scan grating contrast

Command option:

```powershell
--mode constant_mirror
```

Meaning:

```text
Left side:
    fixed mirror value

Right side:
    binary grating with low value fixed
    high value scanned
```

The generated grating alternates between:

```text
grating_low
grating_high
```

with:

```text
grating_high = linspace(scan_start, scan_stop, n_frames)
```

Purpose:

Use this mode to find a useful grating contrast. In practice, this helps identify two SLM gray values that give a strong, clean diffraction/fringe signal.

Example:

```powershell
python .\generate_slm_calibration_frames.py --mode constant_mirror --out frames_A_constant_mirror --n 16 --mirror 32768 --scan-start 40000 --scan-stop 50000 --grating-low 0 --stripe-width 8
```

This creates 16 frames where:

```text
mirror_value = 32768
grating_low = 0
grating_high scans from 40000 to 50000
stripe_width = 8 px
```

---

## Mode B: constant grating, scan mirror brightness

Command option:

```powershell
--mode constant_grating
```

Meaning:

```text
Left side:
    mirror value scanned

Right side:
    binary grating fixed
```

The mirror value is:

```text
mirror_value = linspace(0, scan_stop, n_frames)
```

The grating alternates between fixed:

```text
grating_low
grating_high
```

Purpose:

Use this mode after choosing good grating values from Mode A. The fixed grating acts as the comparison field, while the mirror phase is scanned. Camera intensity/fringe position versus mirror gray value gives the phase response curve.

Example:

```powershell
python .\generate_slm_calibration_frames.py --mode constant_grating --out frames_B_constant_grating --n 32 --scan-stop 65535 --grating-low 0 --grating-high 50000 --stripe-width 8
```

This creates 32 frames where:

```text
mirror_value scans from 0 to 65535
grating_low = 0
grating_high = 50000
stripe_width = 8 px
```

---

## Fringe / grating width

The parameter:

```powershell
--stripe-width
```

sets the width of each binary grating stripe in pixels.

Example:

```powershell
--stripe-width 8
```

means the grating alternates every 8 pixels:

```text
00000000 11111111 00000000 11111111 ...
```

Smaller stripe width gives larger diffraction angle / wider Fourier-plane separation.

Larger stripe width gives smaller diffraction angle / closer diffraction orders.

For an SLM pixel pitch `p = 15 µm`, the binary grating period is:

```math
\Lambda = 2 \cdot \text{stripe_width_px} \cdot p
```

Approximate first-order diffraction angle:

```math
\sin\theta \approx \frac{\lambda}{\Lambda}
```

For small angles:

```math
\theta \approx \frac{\lambda}{\Lambda}
```

At a lens focal length `f`, the first-order displacement in the Fourier plane is approximately:

```math
x_1 \approx f \frac{\lambda}{\Lambda}
```

So with:

```text
lambda = 735 nm
p = 15 µm
stripe_width = 8
f = 200 mm
```

the period is:

```text
Lambda = 2 * 8 * 15 µm = 240 µm
```

and:

```text
x1 ≈ 200 mm * 735 nm / 240 µm ≈ 0.61 mm
```

This is a good order-of-magnitude check for whether the diffraction orders fit on the camera.

---

## Script behavior

The script creates:

```text
output_folder/
    000_....bmp
    001_....bmp
    002_....bmp
    ...
    metadata.csv
```

The numbering is intentional because the Blink DVI GUI reads bitmaps from a folder and may not sort filenames in the expected order unless they are explicitly numbered.

The `metadata.csv` stores the parameters for each generated frame, which is useful when matching camera images back to SLM values.

---

## Python API (class-based)

The script now also exposes a class API while keeping CLI usage unchanged.

```python
from calibration_frame_generator import CalibrationFrameGenerator

generator = CalibrationFrameGenerator()
```

Generate in-memory numpy arrays (no files written):

```python
frames, metadata = generator.generate_constant_mirror_scan_arrays(
    n_frames=16,
    scan_start=40000,
    scan_stop=50000,
    mirror_value=32768,
    grating_low=0,
    stripe_width_px=8,
    split_x=256,
    grating_axis="x",
)

# frames shape: (n_frames, 512, 512), dtype=uint16
single_frame = frames[0]
```

Write frames to disk (BMP + metadata.csv) and still get arrays:

```python
frames, metadata = generator.generate_constant_grating_scan(
    out_dir="frames_B_constant_grating",
    n_frames=32,
    scan_stop=65535,
    grating_low=0,
    grating_high=50000,
    stripe_width_px=8,
    split_x=256,
    grating_axis="x",
)
```

Additional API helpers:

```python
frame16 = generator.make_frame(
    mirror_value=32768,
    grating_low=0,
    grating_high=50000,
    stripe_width_px=8,
)
rgb = generator.pack_meadowlark_dvi_16bit_to_rgb(frame16)
generator.save_bmp_24bit(frame16, "single_frame.bmp")

---

## Importing & Usage (as a Python module)

If you want to use the generator from another script or a Jupyter notebook, import the class directly from the package path. When running from the repository root the import looks like:

```python
from scripts.calibration.generate_slm_calibration_frames import CalibrationFrameGenerator

gen = CalibrationFrameGenerator()
# generate arrays in-memory
frames, metadata = gen.generate_constant_grating_scan_arrays(
    n_frames=8,
    scan_stop=50000,
    grating_low=0,
    grating_high=40000,
    stripe_width_px=8,
)

# write frames to disk and get metadata
frames, metadata = gen.generate_constant_grating_scan(
    out_dir="out_frames",
    n_frames=8,
    scan_stop=50000,
    grating_low=0,
    grating_high=40000,
    stripe_width_px=8,
)
```

Notes on importability:
- If Python cannot find `scripts`, either run your script from the repository root or add the repo root to `PYTHONPATH` or `sys.path`.
- Alternatively install the repository in editable mode from the repo root:

```bash
pip install -e .
```

Jupyter / notebook tip:

```python
import sys
sys.path.append(r"C:/Users/Eitan/Documents/SLM")
from scripts.calibration.generate_slm_calibration_frames import CalibrationFrameGenerator
```

This makes it convenient to prototype generation and preview frames interactively before writing to disk.
```

---

## Main parameters

```text
--mode
    constant_mirror
    constant_grating

--out
    Output directory

--n
    Number of frames to generate

--scan-start
    Lower end of scan range for constant_mirror mode.
    Default: 0

--scan-stop
    Upper end of scan range.

--mirror
    Mirror value for constant_mirror mode.
    Default: 32768

--grating-low
    Low value of the binary grating.
    Default: 0

--grating-high
    High value of the binary grating for constant_grating mode.
    Default: 65535

--stripe-width
    Stripe width in pixels.
    Default: 8

--split-x
    Column where mirror side ends and grating side begins.
    Default: 256

--axis
    x gives vertical stripes, varying along x.
    y gives horizontal stripes, varying along y.
```

---

## PowerShell usage

Use single-line commands in PowerShell to avoid line-continuation issues.

Example Mode A:

```powershell
python .\generate_slm_calibration_frames.py --mode constant_mirror --out frames_A_constant_mirror --n 16 --mirror 32768 --scan-start 40000 --scan-stop 50000 --grating-low 0 --stripe-width 8
```

Example Mode B:

```powershell
python .\generate_slm_calibration_frames.py --mode constant_grating --out frames_B_constant_grating --n 32 --scan-stop 65535 --grating-low 0 --grating-high 50000 --stripe-width 8
```

If multiline PowerShell is needed, use backticks:

```powershell
python .\generate_slm_calibration_frames.py `
  --mode constant_mirror `
  --out frames_A_constant_mirror `
  --n 16 `
  --mirror 32768 `
  --scan-start 40000 `
  --scan-stop 50000 `
  --grating-low 0 `
  --stripe-width 8
```

Do not use `^` in PowerShell. That is for `cmd.exe`.

---

## Practical calibration workflow

1. Generate Mode A frames.

2. Load the folder in the Blink DVI GUI.

3. Display frames manually or with the GUI sequence tool.

4. Observe the Fourier-plane pattern on the camera.

5. Pick grating values that give strong, stable, measurable fringes/diffraction signal.

6. Generate Mode B frames using those chosen grating values.

7. Record camera image/intensity for each mirror value.

8. Extract a scalar signal from the camera, for example:
   - brightness of a selected diffraction order,
   - contrast of fringes,
   - fitted phase shift of fringe pattern,
   - intensity difference between two ROIs.

9. Fit the measured signal versus SLM gray value.

10. Convert the fit into an approximate phase response curve.

11. Build a LUT mapping desired linear phase to required SLM input gray value.

---

## Important caveat about the GUI LUT

The Blink DVI GUI can apply a LUT.

If the LUT is active, then the BMP values are not necessarily raw voltage values. They are input values that pass through the LUT before reaching the hardware.

So for calibration, decide explicitly whether the goal is:

```text
A. characterize the SLM with the existing LUT active
```

or

```text
B. characterize raw-ish SLM response with LUT disabled / identity LUT
```

For building a new wavelength LUT, option B is usually the cleaner concept, but it depends on what the GUI allows.

---

## Important optical caveats

The method assumes:

1. The laser is coherent enough across the two halves of the illuminated SLM area.

2. The SLM is illuminated with the correct linear polarization.

3. The camera is really in the Fourier plane of the lens.

4. The diffraction orders are not clipped.

5. The exposure is not saturated.

6. The beam covers both halves of the SLM reasonably uniformly.

7. The grating diffraction order used for measurement is isolated enough from the zero order and pixel-grid diffraction artifacts.

8. The SLM response may depend on wavelength and temperature.

---

## Code structure summary

Key functions in the script:

```python
pack_meadowlark_dvi_16bit_to_rgb(value16_img)
```

Packs a 16-bit image into Meadowlark-compatible RGB BMP format.

```python
make_square_grating(...)
```

Creates the binary grating region.

```python
make_frame(...)
```

Creates one full 512×512 frame with left mirror and right grating.

```python
generate_constant_mirror_scan(...)
```

Mode A generator.

```python
generate_constant_grating_scan(...)
```

Mode B generator.

```python
write_metadata(...)
```

Saves a CSV file linking each frame to its SLM parameters.

---

## Next likely tasks for the Copilot agent

1. Add a preview plot showing the 16-bit phase image before saving.

2. Add support for sinusoidal gratings, not only binary gratings.

3. Add support for blazed/sawtooth phase ramps.

4. Add an identity LUT generator for the Blink GUI, if needed.

5. Add camera-image analysis:
   - load image sequence,
   - crop ROI,
   - measure intensity,
   - fit sinusoid,
   - unwrap phase,
   - generate LUT.

6. Add a config-file interface, for example `config.yaml`, so calibration runs are reproducible.

7. Add safety checks:
   - no saturated camera frames,
   - expected diffraction order location,
   - warning if stripe width makes order too far from camera center.

8. Add experimental log output:
   - timestamp,
   - SLM serial,
   - wavelength,
   - LUT used,
   - camera exposure,
   - lens focal length,
   - stripe width,
   - selected diffraction order ROI.
