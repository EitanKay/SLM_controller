from __future__ import annotations

from typing import Optional

import numpy as np
import pylablib as pll
from PIL import Image
from pylablib.devices import Thorlabs

class CameraDriver:
    def __init__(
        self,
        exposure_time_ms: float = 1.0,
        gain: int = 0,
        dll_path: Optional[str] = None,
        serial: Optional[str] = None,
    ):
        self.gain = gain
        self.exposure_time_ms = float(exposure_time_ms)
        self.dll_path = dll_path
        self.serial = serial

        self._cam: Optional[Thorlabs.ThorlabsTLCamera] = None
        self._acquiring = False

    def open(self):
        if self._cam is not None:
            return

        if self.dll_path:
            pll.par["devices/dlls/thorlabs_tlcam"] = self.dll_path

        if self.serial is None:
            serials = Thorlabs.list_cameras_tlcam()
            if not serials:
                raise RuntimeError("No Thorlabs TLCamera devices found")
            self.serial = serials[0]

        self._cam = Thorlabs.ThorlabsTLCamera(serial=self.serial)
        self.set_exposure_time(self.exposure_time_ms)
        self.set_gain(self.gain)
        self._cam.set_trigger_mode("int")

    def close(self):
        if self._cam is None:
            return
        if self._acquiring:
            self.stop_acquisition()
        self._cam.close()
        self._cam = None

    def set_gain(self, gain: int):
        self.gain = gain
        if self._cam is None:
            return

        if hasattr(self._cam, "set_gain"):
            self._cam.set_gain(gain)
        elif hasattr(self._cam, "set_gain_db"):
            self._cam.set_gain_db(gain)
        else:
            raise NotImplementedError("Camera backend does not support gain control")

    def set_exposure_time(self, exposure_time_ms: float):
        self.exposure_time_ms = float(exposure_time_ms)
        if self._cam is None:
            return
        self._cam.set_exposure(self.exposure_time_ms / 1000.0)

    def start_acquisition(self):
        if self._cam is None:
            self.open()
        if not self._acquiring:
            self._cam.start_acquisition()
            self._acquiring = True

    def stop_acquisition(self):
        if self._cam is None:
            return
        if self._acquiring:
            self._cam.stop_acquisition()
            self._acquiring = False

    def get_image(self, output_format: str = "raw16", timeout_s: float = 5.0) -> Image.Image:
        if self._cam is None:
            self.open()

        started_here = False
        if not self._acquiring:
            self.start_acquisition()
            started_here = True

        frame = self._cam.snap(timeout=timeout_s)

        if started_here:
            self.stop_acquisition()

        if output_format == "raw16":
            frame16 = frame.astype(np.uint16)
            return Image.fromarray(frame16, mode="I;16")

        if output_format == "scaled8":
            frame_float = frame.astype(np.float32)
            frame_float -= frame_float.min()
            max_val = frame_float.max()
            if max_val > 0:
                frame_float /= max_val
            img8 = (255 * frame_float).astype(np.uint8)
            return Image.fromarray(img8, mode="L")

        raise ValueError("output_format must be 'raw16' or 'scaled8'")

    def __enter__(self) -> "CameraDriver":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


# usage
if __name__ == "__main__":
    
    camera_driver = CameraDriver(
        exposure_time_ms=20.0,
        dll_path=r"C:\Program Files\Thorlabs\Scientific Imaging\ThorImageCAM\bin",
    )

    with camera_driver:
        raw_img = camera_driver.get_image(output_format="raw16")
        raw_img.save("camera_raw16.tif")

        scaled_img = camera_driver.get_image(output_format="scaled8")
        scaled_img.save("camera_scaled8.png")
