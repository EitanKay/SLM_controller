import numpy as np
import pytest

pytest.importorskip("PyQt6")

from src.slm_gui import workers


def test_hologram_worker_propagates_input_beam_settings(monkeypatch):
    calls = []
    expected_phase = np.zeros((512, 512), dtype=np.uint16)

    def fake_generate_phase_uint16(target, **kwargs):
        calls.append((target.copy(), kwargs))
        return expected_phase

    monkeypatch.setattr(workers, "generate_phase_uint16", fake_generate_phase_uint16)
    target = np.full((512, 512), 17, dtype=np.uint8)
    custom_input = np.linspace(
        0.1, 1.0, 512 * 512, dtype=np.float64
    ).reshape(512, 512)
    request = workers.GenerationRequest(
        target=target,
        algorithm="WGS-Leonardo",
        iterations=23,
        seed=91,
        input_profile="custom",
        gaussian_waist_px=123.4,
        custom_input_amplitude=custom_input,
    )
    worker = workers.HologramWorker(request)
    finished = []
    worker.finished.connect(finished.append)

    worker.run()

    assert len(calls) == 1
    called_target, kwargs = calls[0]
    np.testing.assert_array_equal(called_target, target)
    called_custom_input = kwargs.pop("custom_input_amplitude")
    assert kwargs == {
        "algorithm": "WGS-Leonardo",
        "iterations": 23,
        "seed": 91,
        "input_profile": "custom",
        "gaussian_waist_px": 123.4,
    }
    assert called_custom_input is custom_input
    assert len(finished) == 1
    assert finished[0] is expected_phase
