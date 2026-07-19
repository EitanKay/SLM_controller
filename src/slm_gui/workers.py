from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from src.slm_gui.holography import (
    DEFAULT_GAUSSIAN_WAIST_PX,
    generate_phase_uint16,
)


@dataclass(frozen=True)
class GenerationRequest:
    target: np.ndarray
    algorithm: str
    iterations: int
    seed: int
    input_profile: str = "uniform"
    gaussian_waist_px: float = DEFAULT_GAUSSIAN_WAIST_PX
    custom_input_amplitude: np.ndarray | None = None


class HologramWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, request: GenerationRequest):
        super().__init__()
        self.request = request

    @pyqtSlot()
    def run(self) -> None:
        try:
            phase = generate_phase_uint16(
                self.request.target,
                algorithm=self.request.algorithm,
                iterations=self.request.iterations,
                seed=self.request.seed,
                input_profile=self.request.input_profile,
                gaussian_waist_px=self.request.gaussian_waist_px,
                custom_input_amplitude=self.request.custom_input_amplitude,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(phase)
