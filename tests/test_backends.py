import numpy as np
import pytest

from src.slm_gui.backends import SimulatedSLMBackend


def test_simulator_connect_tracks_lut_and_wfc():
    backend = SimulatedSLMBackend()
    status = backend.connect("custom.lut", "black.bmp")

    assert status.connected is True
    assert status.lut_loaded is True
    assert status.wfc_loaded is True
    assert status.lut_path.endswith("custom.lut")
    assert status.wfc_path.endswith("black.bmp")
    assert status.calibration_enabled is True


def test_simulator_connect_loads_default_calibration():
    backend = SimulatedSLMBackend()
    status = backend.connect()

    assert status.connected is True
    assert status.lut_loaded is True
    assert status.wfc_loaded is True
    assert status.lut_path is None
    assert status.wfc_path is None
    assert status.calibration_enabled is True


def test_simulator_load_wfc_tracks_selected_and_default():
    backend = SimulatedSLMBackend()

    backend.load_wfc("custom.bmp")
    status = backend.status()
    assert status.wfc_loaded is True
    assert status.wfc_path.endswith("custom.bmp")

    backend.load_wfc(None)
    status = backend.status()
    assert status.wfc_loaded is True
    assert status.wfc_path is None


def test_simulator_send_requires_connection():
    backend = SimulatedSLMBackend()

    with pytest.raises(RuntimeError, match="not connected"):
        backend.send(np.zeros((512, 512), dtype=np.uint8))


def test_simulator_send_and_clear():
    backend = SimulatedSLMBackend()
    backend.connect()
    pattern = np.ones((512, 512), dtype=np.uint8)

    backend.send(pattern)
    assert backend.last_pattern.shape == (512, 512)
    assert backend.last_pattern.dtype == np.uint8

    backend.clear()
    assert backend.last_pattern.shape == (512, 512)
    assert np.all(backend.last_pattern == 0)
