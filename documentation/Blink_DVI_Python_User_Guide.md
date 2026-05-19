# Blink DVI Python SDK User Guide

This guide summarizes how to control the Meadowlark Blink DVI SLM from Python using the SDK files supplied by Meadowlark.

The control route is:

```text
Python -> ctypes -> Blink_C_wrapper.dll -> SDK display window -> DVI controller -> SLM
```

This is not a separate visible application. Your Python process creates the hidden/SDK display window and writes image data to it.

---

## 1. Files you need

Keep these files together in one SDK folder, for example:

```text
C:\Program Files\Meadowlark Optics\Blink DVI\SDK\
```

Required for Python control:

```text
Blink_C_wrapper.dll
Blink_C_wrapper.h
HdmiDisplay.dll
ImageGen.dll
freeglut.dll
glew64.dll
```

Useful examples / documentation:

```text
LoadImageSequence.py
BlinkSDKexample.cpp
Blink Software Development Kit READ ME.pdf
ImageGen.h
```

Calibration files, usually outside the SDK folder:

```text
C:\Program Files\Meadowlark Optics\Blink DVI\LUT Files\linear.lut
C:\Program Files\Meadowlark Optics\Blink DVI\WFC Files\black.bmp
```

Replace `linear.lut` with your wavelength-specific/custom LUT when you have one. The example notes that `linear.lut` only maps input gray levels linearly to output voltages; it does **not** guarantee linear optical phase.

---

## 2. Python environment

Recommended packages:

```powershell
python -m pip install numpy pillow
```

The supplied example imports `scipy.misc`, but for basic SLM control you do not need SciPy.

Important: Python architecture must match the DLL architecture. If the DLLs are 64-bit, use 64-bit Python. If they are 32-bit, use 32-bit Python.

To check a DLL architecture:

```powershell
python -m pip install pefile
python
```

```python
import pefile
pe = pefile.PE(r"C:\Program Files\Meadowlark Optics\Blink DVI\SDK\Blink_C_wrapper.dll")
print(hex(pe.FILE_HEADER.Machine))
```

```text
0x14c  = 32-bit x86
0x8664 = 64-bit x64
```

---

## 3. Basic import and DLL loading

Use `ctypes` to load the Meadowlark DLLs. Modern Windows often needs the SDK folder explicitly added to the DLL search path.

```python
import os
import ctypes
from ctypes import *
from pathlib import Path

SDK_DIR = Path(r"C:\Program Files\Meadowlark Optics\Blink DVI\SDK")
BLINK_DIR = SDK_DIR.parent

os.add_dll_directory(str(SDK_DIR))

slm = ctypes.CDLL(str(SDK_DIR / "Blink_C_wrapper.dll"))
imagegen = ctypes.CDLL(str(SDK_DIR / "ImageGen.dll"))
```

For correct pixel placement on the SLM display, set DPI awareness before creating the SDK window:

```python
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
```

---

## 4. Blink_C_wrapper callable functions

These are the core functions from `Blink_C_wrapper.h`.

### `Create_SDK(bCppOrPython)`

Initializes the SDK and creates the display window used to send images to the SLM.

C prototype:

```cpp
void Create_SDK(bool bCppOrPython);
```

Python declaration:

```python
slm.Create_SDK.argtypes = [c_bool]
slm.Create_SDK.restype = None
```

Use:

```python
slm.Create_SDK(True)   # True for C++ / Python
```

---

### `Delete_SDK()`

Closes the SDK and cleans up resources.

C prototype:

```cpp
void Delete_SDK();
```

Python declaration:

```python
slm.Delete_SDK.argtypes = []
slm.Delete_SDK.restype = None
```

Use:

```python
slm.Delete_SDK()
```

Always call this before exiting.

---

### `Load_LUT(file_path)`

Loads a `.lut` file. The LUT maps input grayscale values to output voltages to compensate the nonlinear liquid-crystal voltage-to-phase response.

C prototype:

```cpp
int Load_LUT(char* file_path);
```

Python declaration:

```python
slm.Load_LUT.argtypes = [c_char_p]
slm.Load_LUT.restype = c_int
```

Use:

```python
lut_path = str(BLINK_DIR / "LUT Files" / "linear.lut").encode()
ok = slm.Load_LUT(lut_path)
print("Load LUT:", ok)
```

Returns nonzero/true if loaded correctly. If loading fails, the SDK falls back to a linear grayscale-to-grayscale mapping.

---

### `Load_WavefrontCorrection(file_path)`

Loads a bitmap correction image used to compensate static spatial phase nonuniformities.

C prototype:

```cpp
int Load_WavefrontCorrection(char* file_path);
```

Python declaration:

```python
slm.Load_WavefrontCorrection.argtypes = [c_char_p]
slm.Load_WavefrontCorrection.restype = c_int
```

Use:

```python
wfc_path = str(BLINK_DIR / "WFC Files" / "black.bmp").encode()
ok = slm.Load_WavefrontCorrection(wfc_path)
print("Load WFC:", ok)
```

`black.bmp` is a blank correction. Replace it with a measured/custom wavefront correction when available.

---

### `CalibrateImage(file_path, Image)`

Loads an image file, applies the LUT and wavefront correction, and returns a calibrated RGB image array.

C prototype:

```cpp
int CalibrateImage(char* file_path, unsigned char* Image);
```

Python declaration:

```python
slm.CalibrateImage.argtypes = [c_char_p, POINTER(c_ubyte)]
slm.CalibrateImage.restype = c_int
```

Usually, `CalibrateImageArray` is more convenient in Python.

---

### `CalibrateImageArray(InputImage, OutputImage, is_8_bit)`

Applies LUT and wavefront correction to an image array.

C prototype:

```cpp
int CalibrateImageArray(unsigned char* InputImage, unsigned char* OutputImage, bool is_8_bit);
```

Python declaration:

```python
slm.CalibrateImageArray.argtypes = [POINTER(c_ubyte), POINTER(c_ubyte), c_bool]
slm.CalibrateImageArray.restype = c_int
```

Use for an 8-bit input phase image:

```python
raw = np.zeros((height, width), dtype=np.uint8)
cal = np.empty((height, width, 3), dtype=np.uint8)

ok = slm.CalibrateImageArray(
    raw.ctypes.data_as(POINTER(c_ubyte)),
    cal.ctypes.data_as(POINTER(c_ubyte)),
    True,
)
```

The output is RGB, so when sending `cal` to the SLM you should call `Write_image(..., False)`.

---

### `Write_image(image_data, is_8_bit)`

Writes image data to the SLM display window.

C prototype:

```cpp
int Write_image(unsigned char* image_data, int is_8_bit);
```

Python declaration:

```python
slm.Write_image.argtypes = [POINTER(c_ubyte), c_int]
slm.Write_image.restype = c_int
```

Use for an 8-bit grayscale array:

```python
ok = slm.Write_image(raw.ctypes.data_as(POINTER(c_ubyte)), 1)
```

Use for an RGB calibrated array:

```python
ok = slm.Write_image(cal.ctypes.data_as(POINTER(c_ubyte)), 0)
```

Recommended workflow: generate an 8-bit phase image, pass it through `CalibrateImageArray`, then send the calibrated RGB output using `Write_image(..., 0)`.

---

### `Get_Height()` and `Get_Width()`

Return the SLM dimensions detected by the SDK.

C prototypes:

```cpp
int Get_Height();
int Get_Width();
```

Python declarations:

```python
slm.Get_Height.argtypes = []
slm.Get_Height.restype = c_int

slm.Get_Width.argtypes = []
slm.Get_Width.restype = c_int
```

Use:

```python
height = slm.Get_Height()
width = slm.Get_Width()
print(width, height)
```

For the P512 DVI system, this should normally be `512 x 512`.

---

## 5. ImageGen callable functions

These functions generate common 8-bit phase patterns. They write into an already-allocated `uint8` array of length `width * height`.

Common Python declaration pattern:

```python
imagegen.Generate_Solid.argtypes = [POINTER(c_ubyte), c_int, c_int, c_int]
imagegen.Generate_Solid.restype = None
```

The full list from `ImageGen.h`:

```cpp
void Generate_Stripe(unsigned char* Array, int width, int height,
                     int PixelValOne, int PixelValTwo, int PixelsPerStripe);

void Generate_Checkerboard(unsigned char* Array, int width, int height,
                           int PixelValOne, int PixelValTwo, int PixelsPerCheck);

void Generate_Solid(unsigned char* Array, int width, int height, int PixelVal);

void Generate_Random(unsigned char* Array, int width, int height);

void Generate_Zernike(unsigned char* Array, int width, int height,
                      int centerX, int centerY, int radius,
                      double Piston, double TiltX, double TiltY,
                      double Power, double AstigX, double AstigY,
                      double ComaX, double ComaY, double PrimarySpherical,
                      double TrefoilX, double TrefoilY,
                      double SecondaryAstigX, double SecondaryAstigY,
                      double SecondaryComaX, double SecondaryComaY,
                      double SecondarySpherical,
                      double TetrafoilX, double TetrafoilY,
                      double TertiarySpherical,
                      double QuaternarySpherical);

void Generate_FresnelLens(unsigned char* Array, int width, int height,
                          int centerX, int centerY, int radius,
                          double Power, bool cylindrical, bool horizontal);

void Generate_Grating(unsigned char* Array, int width, int height,
                      int Period, bool increasing, bool horizontal);

void Generate_Sinusoid(unsigned char* Array, int width, int height,
                       int Period, bool horizontal);

void Generate_LG(unsigned char* Array, int width, int height,
                 int VortexCharge, int centerX, int centerY, bool fork);

void Generate_ConcentricRings(unsigned char* Array, int width, int height,
                              int InnerDiameter, int OuterDiameter,
                              int PixelValOne, int PixelValTwo,
                              int centerX, int centerY);

void Generate_Axicon(unsigned char* Array, int width, int height,
                     int PhaseDelay, int centerX, int centerY, bool increasing);

void Mask_Image(unsigned char* Array, int width, int height,
                int Region, int NumRegions);

bool Initalize_HologramGenerator(int width, int height, int iterations);

bool Generate_Hologram(unsigned char* Array,
                       float* x_spots, float* y_spots, float* z_spots,
                       float* I_spots, int N_spots);

void Destruct_HologramGenerator();

bool Initalize_RegionalLUT(int width, int height);

bool Load_RegionalLUT(const char* const RegionalLUTPath, float* Max, float* Min);

bool Apply_RegionalLUT(unsigned char* Array);

void Destruct_RegionalLUT();

bool SetBESTConstants(int FocalLength, float BeamDiameter, float Wavelength,
                      float SLMpitch, int SLMNumPixels, float ObjNA,
                      float ObjMag, float ObjRefInd, float TubeLength,
                      float RelayMag);

bool GetBESTAmplitudeMask(float* AmplitudeY, float* Peaks,
                          int* PeaksIndex, float Period);

bool GetBESTAxialPSF(double* axialAmplitude, float* Intensity,
                     float Period, float OuterDiameter, float InnerDiameter);

void Generate_BESTRings(unsigned char* Array, int width, int height,
                        int centerX, int centerY, float S);
```

For our SLM calibration workflow, you mostly need your own NumPy-generated gratings rather than `ImageGen.dll`, but `Generate_Grating`, `Generate_Solid`, `Generate_Stripe`, and `Generate_LG` are useful for sanity checks.

---

## 6. Minimal reusable Python wrapper

Create a file named `blink_dvi.py`:

```python
import os
import ctypes
from ctypes import c_bool, c_char_p, c_int, c_ubyte, POINTER
from pathlib import Path
import numpy as np


class BlinkDVI:
    def __init__(self, sdk_dir=r"C:\Program Files\Meadowlark Optics\Blink DVI\SDK"):
        self.sdk_dir = Path(sdk_dir)
        self.blink_dir = self.sdk_dir.parent
        os.add_dll_directory(str(self.sdk_dir))
        self.slm = ctypes.CDLL(str(self.sdk_dir / "Blink_C_wrapper.dll"))
        self._declare_functions()
        self.created = False
        self.width = None
        self.height = None

    def _declare_functions(self):
        self.slm.Create_SDK.argtypes = [c_bool]
        self.slm.Create_SDK.restype = None

        self.slm.Delete_SDK.argtypes = []
        self.slm.Delete_SDK.restype = None

        self.slm.Load_LUT.argtypes = [c_char_p]
        self.slm.Load_LUT.restype = c_int

        self.slm.Load_WavefrontCorrection.argtypes = [c_char_p]
        self.slm.Load_WavefrontCorrection.restype = c_int

        self.slm.CalibrateImageArray.argtypes = [POINTER(c_ubyte), POINTER(c_ubyte), c_bool]
        self.slm.CalibrateImageArray.restype = c_int

        self.slm.Write_image.argtypes = [POINTER(c_ubyte), c_int]
        self.slm.Write_image.restype = c_int

        self.slm.Get_Height.argtypes = []
        self.slm.Get_Height.restype = c_int

        self.slm.Get_Width.argtypes = []
        self.slm.Get_Width.restype = c_int

    @staticmethod
    def set_dpi_awareness():
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def open(self, lut_path=None, wfc_path=None):
        self.set_dpi_awareness()
        self.slm.Create_SDK(True)
        self.created = True

        self.width = self.slm.Get_Width()
        self.height = self.slm.Get_Height()

        if lut_path is None:
            lut_path = self.blink_dir / "LUT Files" / "linear.lut"
        if wfc_path is None:
            wfc_path = self.blink_dir / "WFC Files" / "black.bmp"

        lut_ok = self.slm.Load_LUT(str(lut_path).encode())
        wfc_ok = self.slm.Load_WavefrontCorrection(str(wfc_path).encode())

        if not lut_ok:
            raise RuntimeError(f"Failed to load LUT: {lut_path}")
        if not wfc_ok:
            raise RuntimeError(f"Failed to load wavefront correction: {wfc_path}")

        return self.width, self.height

    def calibrate_8bit(self, image8):
        image8 = np.ascontiguousarray(image8, dtype=np.uint8)
        if image8.shape != (self.height, self.width):
            raise ValueError(f"Expected image shape {(self.height, self.width)}, got {image8.shape}")

        out = np.empty((self.height, self.width, 3), dtype=np.uint8)
        ok = self.slm.CalibrateImageArray(
            image8.ctypes.data_as(POINTER(c_ubyte)),
            out.ctypes.data_as(POINTER(c_ubyte)),
            True,
        )
        if not ok:
            raise RuntimeError("CalibrateImageArray failed")
        return out

    def write_8bit(self, image8, apply_calibration=True):
        if apply_calibration:
            rgb = self.calibrate_8bit(image8)
            return self.write_rgb(rgb)

        image8 = np.ascontiguousarray(image8, dtype=np.uint8)
        ok = self.slm.Write_image(image8.ctypes.data_as(POINTER(c_ubyte)), 1)
        if not ok:
            raise RuntimeError("Write_image failed for 8-bit image")
        return ok

    def write_rgb(self, rgb):
        rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        if rgb.shape != (self.height, self.width, 3):
            raise ValueError(f"Expected RGB shape {(self.height, self.width, 3)}, got {rgb.shape}")

        ok = self.slm.Write_image(rgb.ctypes.data_as(POINTER(c_ubyte)), 0)
        if not ok:
            raise RuntimeError("Write_image failed for RGB image")
        return ok

    def close(self):
        if self.created:
            self.slm.Delete_SDK()
            self.created = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
```

---

## 7. Example: display a solid gray level

```python
import numpy as np
import time
from blink_dvi import BlinkDVI

with BlinkDVI() as slm:
    img = np.full((slm.height, slm.width), 128, dtype=np.uint8)
    slm.write_8bit(img, apply_calibration=True)
    time.sleep(5)
```

---

## 8. Example: display a blazed grating

```python
import numpy as np
import time
from blink_dvi import BlinkDVI


def blazed_grating(width, height, period_px, horizontal=False):
    if horizontal:
        y = np.arange(height)[:, None]
        phase = (y % period_px) / period_px
        img = np.repeat(phase, width, axis=1)
    else:
        x = np.arange(width)[None, :]
        phase = (x % period_px) / period_px
        img = np.repeat(phase, height, axis=0)

    return np.asarray(np.round(255 * img), dtype=np.uint8)


with BlinkDVI() as slm:
    img = blazed_grating(slm.width, slm.height, period_px=64, horizontal=False)
    slm.write_8bit(img, apply_calibration=True)
    time.sleep(5)
```

`horizontal=False` means the phase varies along x, so the diffraction orders move along the x direction in the Fourier plane.

---

## 9. Example: send an image sequence

```python
import numpy as np
import time
from blink_dvi import BlinkDVI


def blazed_grating(width, height, period_px):
    x = np.arange(width)[None, :]
    img = ((x % period_px) / period_px) * 255
    return np.repeat(img, height, axis=0).astype(np.uint8)

periods = [256, 128, 64, 32, 16]

with BlinkDVI() as slm:
    # Precompute and calibrate frames before timing-critical display
    frames = []
    for p in periods:
        raw = blazed_grating(slm.width, slm.height, p)
        frames.append(slm.calibrate_8bit(raw))

    for _ in range(5):
        for frame in frames:
            slm.write_rgb(frame)
            time.sleep(0.5)
```

Precomputing the calibrated RGB frames is better than applying `CalibrateImageArray` inside a fast loop.

---

## 10. Recommended system setup order

A typical experiment should follow this order:

```text
1. Import libraries
2. Set Windows DPI awareness
3. Load Blink_C_wrapper.dll
4. Call Create_SDK(True)
5. Query width and height with Get_Width / Get_Height
6. Load LUT with Load_LUT
7. Load wavefront correction with Load_WavefrontCorrection
8. Generate raw phase images as NumPy uint8 arrays
9. Calibrate images using CalibrateImageArray
10. Send images using Write_image
11. At the end, call Delete_SDK
```

In code:

```python
with BlinkDVI() as slm:
    raw = make_my_phase_mask(...)
    calibrated = slm.calibrate_8bit(raw)
    slm.write_rgb(calibrated)
```

---

## 11. Notes about 8-bit vs RGB / 16-bit DVI data

The safe SDK workflow is:

```text
8-bit phase image -> CalibrateImageArray -> RGB image -> Write_image(..., is_8_bit=0)
```

This is the workflow used by Meadowlark's own examples.

The older DVI documentation states that 24-bit bitmap images encode 16-bit SLM values using color channels: green as the 8 most significant bits, red as the 8 least significant bits, and blue ignored. However, the SDK header comments also say that `Write_image` can accept either 8-bit grayscale or RGB data, and the provided examples rely on `CalibrateImageArray` to produce the RGB image.

So, until we verify the exact raw RGB channel mapping experimentally, use the Meadowlark-provided calibration path rather than directly constructing 16-bit RGB images.

For your LUT calibration work, start with 8-bit input levels. Once the 8-bit workflow is stable, we can test raw 16-bit encoding separately using known gratings and diffraction efficiency measurements.

---

## 12. Practical tips

- Keep the SLM as the secondary display, usually to the right of the main monitor.
- Set display scaling to 100% if possible.
- Call the DPI awareness code before `Create_SDK`.
- Use contiguous NumPy arrays: `np.ascontiguousarray(..., dtype=np.uint8)`.
- Always call `Delete_SDK()` before exiting.
- Precompute calibrated frames before running a timed sequence.
- For calibration experiments, log the exact LUT, WFC file, grating period, phase level, exposure, and camera gain for each frame.

---

## 13. Minimal calibration-frame idea for your setup

For your split mirror/grating calibration method, generate a raw 8-bit image like this:

```python
import numpy as np


def split_mirror_grating(width, height, mirror_level, grating_period, grating_min=0, grating_max=255):
    img = np.zeros((height, width), dtype=np.uint8)

    mid = width // 2

    # Left half: mirror / constant phase
    img[:, :mid] = mirror_level

    # Right half: blazed grating
    x = np.arange(width - mid)[None, :]
    ramp = (x % grating_period) / grating_period
    grating = grating_min + ramp * (grating_max - grating_min)
    img[:, mid:] = np.repeat(grating, height, axis=0).astype(np.uint8)

    return img
```

Then display it:

```python
with BlinkDVI() as slm:
    raw = split_mirror_grating(
        slm.width,
        slm.height,
        mirror_level=128,
        grating_period=64,
    )
    slm.write_8bit(raw, apply_calibration=True)
```
