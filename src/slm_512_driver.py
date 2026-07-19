
from __future__ import annotations

import ctypes
import os
from ctypes import c_bool, c_char_p, c_int, c_ubyte, POINTER
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image


class slm_512_driver:
    """
    High-level driver for the Meadowlark Blink DVI 512x512 SLM.

    Default SDK directory:
        C:\\Program Files\\Meadowlark Optics\\Blink DVI\\SDK

    Example usage:
        slm = slm_512_driver(
            sdk_dir=r"C:\\Program Files\\Meadowlark Optics\\Blink DVI\\SDK"
        )
        slm.open()
        slm.load_lut(r"C:\\Program Files\\Meadowlark Optics\\Blink DVI\\LUT Files\\linear.lut")
        slm.load_wfc(r"C:\\Program Files\\Meadowlark Optics\\Blink DVI\\WFC Files\\black.bmp")
        slm.set_use_calibration(True)

        img = np.zeros((slm.height, slm.width), dtype=np.uint8)
        slm.set_pattern(img)
        slm.close()
    """

    def __init__(self, sdk_dir: Optional[str] = None):
        self.sdk_dir = Path(
            sdk_dir or r"C:\Program Files\Meadowlark Optics\Blink DVI\SDK"
        )
        self.blink_dir = self.sdk_dir.parent

        self.slm = None
        self.created = False
        self.width: Optional[int] = None
        self.height: Optional[int] = None
        self.lut_loaded = False
        self.wfc_loaded = False
        self.calibration_enabled = False
        
        # For thread-safe double buffering
        self._out_buffers = None
        self._out_buffer_idx = 0
        self._in_buffer = None

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

    def open(self) -> Tuple[int, int]:
        if self.created:
            return self.width, self.height

        if not self.sdk_dir.exists():
            raise FileNotFoundError(f"SDK directory not found: {self.sdk_dir}")

        os.add_dll_directory(str(self.sdk_dir))
        self.slm = ctypes.CDLL(str(self.sdk_dir / "Blink_C_wrapper.dll"))
        self._declare_functions()

        self.slm.Create_SDK(True)
        self.created = True

        self.width = int(self.slm.Get_Width())
        self.height = int(self.slm.Get_Height())
        return self.width, self.height

    def load_lut(self, lut_path: Optional[str] = None):
        if not self.created:
            self.open()

        if lut_path is None:
            lut_path = self.blink_dir / "LUT Files" / "linear.lut"
        else:
            lut_path = Path(lut_path)

        ok = self.slm.Load_LUT(str(lut_path).encode())
        if not ok:
            raise RuntimeError(f"Failed to load LUT: {lut_path}")
        self.lut_loaded = True

    def load_wfc(self, wfc_path: Optional[str] = None):
        if not self.created:
            self.open()

        if wfc_path is None:
            wfc_path = self.blink_dir / "WFC Files" / "black.bmp"
        else:
            wfc_path = Path(wfc_path)

        ok = self.slm.Load_WavefrontCorrection(str(wfc_path).encode())
        if not ok:
            raise RuntimeError(f"Failed to load wavefront correction: {wfc_path}")
        self.wfc_loaded = True

    def set_use_calibration(self, enabled: bool):
        self.calibration_enabled = bool(enabled)

    def _validate_dims(self, arr: np.ndarray):
        if self.width is None or self.height is None:
            raise RuntimeError("SLM dimensions unknown. Call open() first.")
        if arr.shape != (self.height, self.width):
            raise ValueError(f"Expected shape {(self.height, self.width)}, got {arr.shape}")

    def _to_uint8_array(self, pattern) -> np.ndarray:
        if isinstance(pattern, Image.Image):
            if pattern.mode == "L":
                arr = np.array(pattern, dtype=np.uint8)
                self._validate_dims(arr)
                return np.ascontiguousarray(arr)

            if pattern.mode in ("RGB", "RGBA"):
                arr = np.array(pattern, dtype=np.uint8)
                arr = arr[..., :3]
                if self.height is None or self.width is None:
                    raise RuntimeError("SLM dimensions unknown. Call open() first.")
                if arr.shape[:2] != (self.height, self.width):
                    raise ValueError(
                        f"Expected image size {(self.width, self.height)}, got {pattern.size}"
                    )
                return np.ascontiguousarray(arr)

            raise ValueError("Unsupported PIL mode. Use L or RGB.")

        arr = np.asarray(pattern)
        if arr.ndim == 2:
            if arr.dtype != np.uint8:
                # If they pass >8 bit masks purposely and driver requires 8-bit, 
                # we just use modulo 256 for phase wrapping logic explicitly 
                # instead of clipping to 255 which destroys the phase wrap.
                # NOTE: For Meadowlark 16-bit DVI they actually pack into an RGB image.
                # Here we respect the driver's interface requiring 8-bit inputs
                # for CalibrateImageArray(..., is_8_bit=True) 
                arr = np.mod(arr, 256).astype(np.uint8)
            self._validate_dims(arr)
            return np.ascontiguousarray(arr)

        if arr.ndim == 3 and arr.shape[2] == 3:
            if arr.dtype != np.uint8:
                 # If treating a >8 bit RGB, apply phase-wrapping mask logic (mod 256)
                arr = np.mod(arr, 256).astype(np.uint8)
            if self.height is None or self.width is None:
                raise RuntimeError("SLM dimensions unknown. Call open() first.")
            if arr.shape[:2] != (self.height, self.width):
                raise ValueError(f"Expected RGB shape {(self.height, self.width, 3)}, got {arr.shape}")
            return np.ascontiguousarray(arr)

        raise ValueError("Pattern must be a >8-bit array, uint8 array or PIL Image (L/RGB).")

    def set_pattern(self, pattern):
        if not self.created:
            self.open()

        arr = self._to_uint8_array(pattern)
        
        # Allocate exactly one stable static memory block for the input array.
        # This prevents the Python Garbage Collector from freeing the RAM 
        # while the C++ DVI graphics thread is still reading it asynchronously.
        if self._in_buffer is None or self._in_buffer.shape != arr.shape:
            self._in_buffer = np.empty_like(arr, order='C')
            
        np.copyto(self._in_buffer, arr)

        if self._in_buffer.ndim == 3:
            self.slm.Write_image(self._in_buffer.ctypes.data_as(POINTER(c_ubyte)), 0)
            return

        use_cal = self.calibration_enabled and self.lut_loaded and self.wfc_loaded
        if use_cal:
            # Use double buffering to prevent graphics driver from reading stale memory.
            # The DVI driver thread may still be reading the previous frame while we
            # calibrate the next one. Alternating buffers ensures consistency.
            if self._out_buffers is None:
                self._out_buffers = [
                    np.ascontiguousarray(np.empty((self.height, self.width, 3), dtype=np.uint8)),
                    np.ascontiguousarray(np.empty((self.height, self.width, 3), dtype=np.uint8)),
                ]
                self._out_buffer_idx = 0
            
            # Swap to the next buffer
            self._out_buffer_idx = 1 - self._out_buffer_idx
            out_buffer = self._out_buffers[self._out_buffer_idx]
            
            ok = self.slm.CalibrateImageArray(
                self._in_buffer.ctypes.data_as(POINTER(c_ubyte)),
                out_buffer.ctypes.data_as(POINTER(c_ubyte)),
                True,
            )
            if not ok:
                raise RuntimeError("CalibrateImageArray failed")
            
            self.slm.Write_image(out_buffer.ctypes.data_as(POINTER(c_ubyte)), 0)
            # Give the DVI driver time to queue the buffer before returning
            import time
            time.sleep(0.001)  # 1ms pause to ensure DLL has grabbed the pointer
            return
        
        # 1 indicates 8-bit grayscale for Write_image
        self.slm.Write_image(self._in_buffer.ctypes.data_as(POINTER(c_ubyte)), 1)
        # Give the DVI driver time to queue the buffer before returning
        import time
        time.sleep(0.001)  # 1ms pause to ensure DLL has grabbed the pointer

    def clear_pattern(self):
        if not self.created:
            self.open()
        if self.width is None or self.height is None:
            raise RuntimeError("SLM dimensions unknown. Call open() first.")
        zeros = np.zeros((self.height, self.width), dtype=np.uint8)
        self.set_pattern(zeros)

    def get_status(self) -> dict:
        return {
            "created": self.created,
            "width": self.width,
            "height": self.height,
            "lut_loaded": self.lut_loaded,
            "wfc_loaded": self.wfc_loaded,
            "calibration_enabled": self.calibration_enabled,
            "sdk_dir": str(self.sdk_dir),
        }

    def close(self):
        if self.created and self.slm is not None:
            self.slm.Delete_SDK()
        self.created = False
        self.slm = None
        self.width = None
        self.height = None

    def __enter__(self) -> "slm_512_driver":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
