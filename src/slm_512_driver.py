
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

    @staticmethod
    def _set_dpi_awareness():
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

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
        self._set_dpi_awareness()
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
                arr = np.clip(arr, 0, 255).astype(np.uint8)
            self._validate_dims(arr)
            return np.ascontiguousarray(arr)

        if arr.ndim == 3 and arr.shape[2] == 3:
            if arr.dtype != np.uint8:
                arr = np.clip(arr, 0, 255).astype(np.uint8)
            if self.height is None or self.width is None:
                raise RuntimeError("SLM dimensions unknown. Call open() first.")
            if arr.shape[:2] != (self.height, self.width):
                raise ValueError(f"Expected RGB shape {(self.height, self.width, 3)}, got {arr.shape}")
            return np.ascontiguousarray(arr)

        raise ValueError("Pattern must be a uint8 array or PIL Image (L/RGB).")

    def set_pattern(self, pattern):
        if not self.created:
            self.open()

        arr = self._to_uint8_array(pattern)

        if arr.ndim == 3:
            self.slm.Write_image(arr.ctypes.data_as(POINTER(c_ubyte)), 0)
            return

        use_cal = self.calibration_enabled and self.lut_loaded and self.wfc_loaded
        if use_cal:
            out = np.empty((self.height, self.width, 3), dtype=np.uint8)
            ok = self.slm.CalibrateImageArray(
                arr.ctypes.data_as(POINTER(c_ubyte)),
                out.ctypes.data_as(POINTER(c_ubyte)),
                True,
            )
            if not ok:
                raise RuntimeError("CalibrateImageArray failed")
            self.slm.Write_image(out.ctypes.data_as(POINTER(c_ubyte)), 0)
            return

        self.slm.Write_image(arr.ctypes.data_as(POINTER(c_ubyte)), 1)

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