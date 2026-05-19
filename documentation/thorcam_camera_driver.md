# Thorlabs Camera Driver (pylablib)

This document describes the simple camera driver in `src/thorcam_camera_driver.py`. It wraps `pylablib.devices.Thorlabs.ThorlabsTLCamera` and returns captured frames as PIL `Image` objects.

---

## Overview

The `CameraDriver` class provides:

- exposure control in milliseconds
- optional gain control (if supported by the device backend)
- start/stop acquisition helpers
- `get_image()` returning a PIL Image in either raw 16-bit or auto-scaled 8-bit
- context manager support for clean open/close

---

## Requirements

- Thorlabs camera with TLCam SDK installed
- Python package `pylablib`
- Python package `Pillow`
- Thorlabs TLCam DLL path available (usually under ThorImageCAM or ThorCam install)

Example DLL path:

```
C:\Program Files\Thorlabs\Scientific Imaging\ThorImageCAM\bin
```

---

## Class: CameraDriver

### Constructor

```python
CameraDriver(
    exposure_time_ms: float = 1.0,
    gain: int = 0,
    dll_path: Optional[str] = None,
    serial: Optional[str] = None,
)
```

- `exposure_time_ms`: exposure in milliseconds (converted to seconds for pylablib)
- `gain`: requested gain value (applied if backend supports it)
- `dll_path`: optional path to the Thorlabs TLCam DLLs
- `serial`: optional camera serial; if None, the first detected device is used

### Methods

```python
open()
close()
set_exposure_time(exposure_time_ms: float)
set_gain(gain: int)
start_acquisition()
stop_acquisition()
get_image(output_format: str = "raw16", timeout_s: float = 5.0) -> Image.Image
```

#### get_image output formats

- `raw16`: returns a 16-bit PIL image (`mode="I;16"`)
- `scaled8`: returns an 8-bit grayscale image (`mode="L"`) with autoscaling

---

## Usage example

```python
from src.thorcam_camera_driver import CameraDriver

camera_driver = CameraDriver(
    exposure_time_ms=20.0,
    dll_path=r"C:\Program Files\Thorlabs\Scientific Imaging\ThorImageCAM\bin",
)

with camera_driver:
    raw_img = camera_driver.get_image(output_format="raw16")
    raw_img.save("camera_raw16.tif")

    scaled_img = camera_driver.get_image(output_format="scaled8")
    scaled_img.save("camera_scaled8.png")
```

---

## Notes

- If no camera is found, `open()` raises `RuntimeError`.
- Gain control depends on device support; some models expose `set_gain`, others `set_gain_db`.
- The driver sets trigger mode to `int` (internal) on open.
