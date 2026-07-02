from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class SLMStatus:
    mode: str
    connected: bool
    width: int | None = None
    height: int | None = None
    lut_path: str | None = None
    lut_loaded: bool = False
    wfc_path: str | None = None
    wfc_loaded: bool = False
    message: str = ""


class SLMBackend(Protocol):
    def connect(
        self, lut_path: str | None = None, wfc_path: str | None = None
    ) -> SLMStatus: ...

    def disconnect(self) -> None: ...

    def load_lut(self, path: str | None) -> None: ...

    def send(self, pattern: np.ndarray) -> None: ...

    def clear(self) -> None: ...

    def status(self) -> SLMStatus: ...


class SimulatedSLMBackend:
    def __init__(self, width: int = 512, height: int = 512):
        self.width = int(width)
        self.height = int(height)
        self.connected = False
        self.lut_path: str | None = None
        self.wfc_path: str | None = None
        self.lut_loaded = False
        self.wfc_loaded = False
        self.last_pattern: np.ndarray | None = None
        self.message = "Simulator idle"

    def connect(
        self, lut_path: str | None = None, wfc_path: str | None = None
    ) -> SLMStatus:
        self.connected = True
        self.lut_path = str(Path(lut_path)) if lut_path else None
        self.wfc_path = str(Path(wfc_path)) if wfc_path else None
        self.lut_loaded = bool(lut_path)
        self.wfc_loaded = bool(wfc_path)
        self.message = "Simulator connected"
        return self.status()

    def disconnect(self) -> None:
        self.connected = False
        self.message = "Simulator disconnected"

    def load_lut(self, path: str | None) -> None:
        self.lut_path = str(Path(path)) if path else None
        self.lut_loaded = bool(path)
        self.message = "Simulator LUT selected" if path else "Simulator using default LUT"

    def send(self, pattern: np.ndarray) -> None:
        if not self.connected:
            raise RuntimeError("Simulator is not connected.")
        self.last_pattern = np.ascontiguousarray(pattern).copy()
        self.message = f"Simulator received pattern {self.last_pattern.shape}"

    def clear(self) -> None:
        if not self.connected:
            raise RuntimeError("Simulator is not connected.")
        self.last_pattern = np.zeros((self.height, self.width), dtype=np.uint8)
        self.message = "Simulator cleared"

    def status(self) -> SLMStatus:
        return SLMStatus(
            mode="Simulator",
            connected=self.connected,
            width=self.width,
            height=self.height,
            lut_path=self.lut_path,
            lut_loaded=self.lut_loaded,
            wfc_path=self.wfc_path,
            wfc_loaded=self.wfc_loaded,
            message=self.message,
        )


class HardwareSLMBackend:
    def __init__(self, sdk_dir: str | None = None):
        self.sdk_dir = sdk_dir
        self.driver = None
        self.lut_path: str | None = None
        self.wfc_path: str | None = None
        self.message = "Hardware disconnected"

    def connect(
        self, lut_path: str | None = None, wfc_path: str | None = None
    ) -> SLMStatus:
        if self.driver is None:
            try:
                from src.slm_512_driver import slm_512_driver
            except ImportError:
                from slm_512_driver import slm_512_driver

            self.driver = slm_512_driver(sdk_dir=self.sdk_dir)

        self.driver.open()
        if lut_path:
            self.load_lut(lut_path)
        if wfc_path:
            self.driver.load_wfc(wfc_path)
            self.wfc_path = str(Path(wfc_path))
        self.message = "Hardware connected"
        return self.status()

    def disconnect(self) -> None:
        if self.driver is not None:
            self.driver.close()
        self.message = "Hardware disconnected"

    def load_lut(self, path: str | None) -> None:
        if self.driver is None:
            raise RuntimeError("Connect to hardware before loading a LUT.")
        self.driver.load_lut(path)
        self.lut_path = str(Path(path)) if path else None
        self.message = f"Loaded LUT: {self.lut_path or 'default'}"

    def send(self, pattern: np.ndarray) -> None:
        if self.driver is None or not self.driver.created:
            raise RuntimeError("Hardware is not connected.")
        self.driver.set_pattern(pattern)
        self.message = f"Sent pattern {np.asarray(pattern).shape}"

    def clear(self) -> None:
        if self.driver is None or not self.driver.created:
            raise RuntimeError("Hardware is not connected.")
        self.driver.clear_pattern()
        self.message = "Hardware cleared"

    def status(self) -> SLMStatus:
        if self.driver is None:
            return SLMStatus(mode="Hardware", connected=False, message=self.message)
        raw = self.driver.get_status()
        return SLMStatus(
            mode="Hardware",
            connected=bool(raw["created"]),
            width=raw["width"],
            height=raw["height"],
            lut_path=self.lut_path,
            lut_loaded=bool(raw["lut_loaded"]),
            wfc_path=self.wfc_path,
            wfc_loaded=bool(raw["wfc_loaded"]),
            message=self.message,
        )

