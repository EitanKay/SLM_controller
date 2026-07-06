import sys
import types

import numpy as np
import pytest

from src.slm_gui.holography import generate_hg_target_uint8, generate_phase_uint16


def test_gs_output_shape_dtype_and_range():
    target = np.zeros((512, 512), dtype=np.uint8)
    target[240:272, 240:272] = 255

    phase = generate_phase_uint16(target, algorithm="GS", iterations=1, seed=1)

    assert phase.shape == (512, 512)
    assert phase.dtype == np.uint16
    assert phase.min() >= 0
    assert phase.max() <= 65535


def test_wgs_output_shape_dtype_and_range():
    pytest.importorskip("slmsuite")
    target = np.zeros((512, 512), dtype=np.uint8)
    target[252:260, 252:260] = 255

    phase = generate_phase_uint16(target, algorithm="WGS-Kim", iterations=1, seed=1)

    assert phase.shape == (512, 512)
    assert phase.dtype == np.uint16
    assert phase.min() >= 0
    assert phase.max() <= 65535


@pytest.mark.parametrize(
    ("algorithm", "expected_method"),
    [
        ("WGS-Leonardo", "WGS-Leonardo"),
        ("WGS-Kim", "WGS-Kim"),
        ("WGS-Nogrette", "WGS-Nogrette"),
        ("WGS-Wu", "WGS-Wu"),
        ("WGS-tanh", "WGS-tanh"),
    ],
)
def test_wgs_variants_dispatch_to_slmsuite_methods(
    algorithm, expected_method, monkeypatch
):
    calls = []

    class FakeHologram:
        def __init__(self, target, slm_shape):
            self.target = target
            self.slm_shape = slm_shape

        def optimize(self, method, maxiter):
            calls.append((method, maxiter))

        def get_phase(self):
            return np.zeros((512, 512), dtype=np.float64)

    slmsuite = types.ModuleType("slmsuite")
    holography = types.ModuleType("slmsuite.holography")
    algorithms = types.ModuleType("slmsuite.holography.algorithms")
    algorithms.Hologram = FakeHologram
    monkeypatch.setitem(sys.modules, "slmsuite", slmsuite)
    monkeypatch.setitem(sys.modules, "slmsuite.holography", holography)
    monkeypatch.setitem(sys.modules, "slmsuite.holography.algorithms", algorithms)

    target = np.zeros((512, 512), dtype=np.uint8)
    target[252:260, 252:260] = 255

    phase = generate_phase_uint16(target, algorithm=algorithm, iterations=7, seed=1)

    assert phase.shape == (512, 512)
    assert phase.dtype == np.uint16
    assert calls == [(expected_method, 7)]


def test_unsupported_algorithm_raises_value_error():
    target = np.zeros((512, 512), dtype=np.uint8)

    with pytest.raises(ValueError, match="Unsupported holography algorithm"):
        generate_phase_uint16(target, algorithm="WGS", iterations=1, seed=1)


def test_hg_target_shape_dtype_and_range():
    target = generate_hg_target_uint8(1, 1, waist=80, rotation_degrees=15)

    assert target.shape == (512, 512)
    assert target.dtype == np.uint8
    assert target.min() >= 0
    assert target.max() <= 255
