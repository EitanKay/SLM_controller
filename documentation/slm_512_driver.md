# SLM 512 Driver (Blink DVI SDK)

This document describes the `slm_512_driver` class in `src/slm_512_driver.py`. The class provides a simple, high-level interface for sending patterns to the Meadowlark Blink DVI 512x512 SLM without exposing DLL or SDK details.

---

## Overview

The driver supports:

- SDK initialization and teardown
- LUT and wavefront correction loading
- Raw 8-bit writes or calibrated writes
- NumPy arrays and PIL Images as input patterns
- Context manager usage

Default behavior is **raw write** unless both LUT and WFC are loaded and calibration is enabled.

---

## Requirements

- Meadowlark Blink DVI SDK installed
- 64-bit Python if the SDK DLLs are 64-bit
- Python packages: `numpy`, `Pillow`

Default SDK directory (used unless overridden):

```
C:\Program Files\Meadowlark Optics\Blink DVI\SDK
```

---

## Class: slm_512_driver

### Constructor

```python
slm_512_driver(sdk_dir: Optional[str] = None)
```

- `sdk_dir`: optional path to the Blink DVI SDK folder. If omitted, the default path is used.

### Core methods

```python
open() -> Tuple[int, int]
close()
get_status() -> dict

load_lut(lut_path: Optional[str] = None)
load_wfc(wfc_path: Optional[str] = None)
set_use_calibration(enabled: bool)

set_pattern(pattern)
clear_pattern()
```

---

## Patterns: accepted input types

`set_pattern()` accepts:

- NumPy `uint8` arrays of shape `(height, width)`
- PIL Images in mode `L` (grayscale)
- PIL Images in mode `RGB` (sent directly as RGB)

Non-`uint8` arrays are clipped to `[0, 255]` and converted to `uint8`.

---

## Calibration behavior

- If `set_use_calibration(True)` **and** both LUT + WFC are loaded, the driver uses `CalibrateImageArray` and sends RGB data.
- Otherwise, it writes raw 8-bit grayscale data directly.

This lets you run in "raw" mode by default and opt-in to calibration only when ready.

---

## Example: raw write

```python
import numpy as np
from src.slm_512_driver import slm_512_driver

slm = slm_512_driver()
slm.open()

pattern = np.zeros((slm.height, slm.width), dtype=np.uint8)
pattern[:, : slm.width // 2] = 128

slm.set_pattern(pattern)
slm.close()
```

---

## Example: calibrated write

```python
import numpy as np
from src.slm_512_driver import slm_512_driver

slm = slm_512_driver(r"C:\Program Files\Meadowlark Optics\Blink DVI\SDK")
slm.open()

slm.load_lut(r"C:\Program Files\Meadowlark Optics\Blink DVI\LUT Files\linear.lut")
slm.load_wfc(r"C:\Program Files\Meadowlark Optics\Blink DVI\WFC Files\black.bmp")
slm.set_use_calibration(True)

pattern = np.random.randint(0, 256, size=(slm.height, slm.width), dtype=np.uint8)
slm.set_pattern(pattern)
slm.close()
```

---

## Context manager usage

```python
import numpy as np
from src.slm_512_driver import slm_512_driver

with slm_512_driver() as slm:
    slm.load_lut()
    slm.load_wfc()
    slm.set_use_calibration(True)

    pattern = np.full((slm.height, slm.width), 200, dtype=np.uint8)
    slm.set_pattern(pattern)
```

---

## Notes

- `clear_pattern()` sends a zero-valued 8-bit image.
- If the SDK directory is missing, `open()` raises `FileNotFoundError`.
- If LUT/WFC loading fails, the driver raises `RuntimeError`.
