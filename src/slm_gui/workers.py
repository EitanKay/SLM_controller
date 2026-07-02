from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from src.slm_gui.holography import generate_phase_uint16


@dataclass(frozen=True)
class GenerationRequest:
    target: np.ndarray
    algorithm: str
    iterations: int
    seed: int


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
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(phase)

