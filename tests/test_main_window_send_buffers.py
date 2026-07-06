import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QFileDialog, QPushButton

from src.slm_gui.backends import SimulatedSLMBackend
from src.slm_gui.main_window import MainWindow


@pytest.fixture
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def settings(tmp_path):
    data = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    data.clear()
    return data


def test_direct_send_ready_uses_calibrated_grayscale(qt_app, settings):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        window.direct_value16 = np.array([[0, 65535]], dtype=np.uint16)

        window._set_direct_send_ready()

        assert window.send_ready.shape == (1, 2)
        assert window.send_ready.dtype == np.uint8
        np.testing.assert_array_equal(
            window.send_ready, np.array([[0, 255]], dtype=np.uint8)
        )
    finally:
        window.close()


def test_generated_send_ready_uses_calibrated_grayscale_and_keeps_phase16(qt_app, settings):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        phase16 = np.array([[0, 32768, 65535]], dtype=np.uint16)

        window._generation_finished(phase16)

        assert window.current_phase16.dtype == np.uint16
        np.testing.assert_array_equal(window.current_phase16, phase16)
        assert window.send_ready.shape == (1, 3)
        assert window.send_ready.dtype == np.uint8
        np.testing.assert_array_equal(
            window.send_ready, np.array([[0, 128, 255]], dtype=np.uint8)
        )
    finally:
        window.close()


def test_top_bar_only_exposes_clear_and_send_buttons(qt_app, settings):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        button_texts = {button.text() for button in window.findChildren(QPushButton)}

        assert "Clear" in button_texts
        assert "Send to SLM" in button_texts
        assert "Connect" not in button_texts
        assert "Disconnect" not in button_texts
        assert "Load LUT" not in button_texts
        assert "Load WFC" not in button_texts
    finally:
        window.close()


def test_saved_lut_and_wfc_paths_are_restored(qt_app, settings):
    settings.setValue("calibration/lut_path", "saved.lut")
    settings.setValue("calibration/wfc_path", "saved.bmp")

    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        assert window.selected_lut_path == "saved.lut"
        assert window.selected_wfc_path == "saved.bmp"
        assert window.lut_path_edit.text() == "saved.lut"
        assert window.wfc_path_edit.text() == "saved.bmp"
    finally:
        window.close()


class SpyBackend(SimulatedSLMBackend):
    def __init__(self):
        super().__init__()
        self.loaded_luts = []
        self.loaded_wfcs = []

    def load_lut(self, path):
        self.loaded_luts.append(path)
        super().load_lut(path)

    def load_wfc(self, path):
        self.loaded_wfcs.append(path)
        super().load_wfc(path)


def test_browsed_lut_loads_immediately_when_connected(qt_app, settings, monkeypatch):
    window = MainWindow(backend_mode="sim", settings=settings, auto_connect=False)
    try:
        backend = SpyBackend()
        backend.connect()
        window.backend = backend
        monkeypatch.setattr(
            QFileDialog,
            "getOpenFileName",
            lambda *args, **kwargs: ("custom.lut", ""),
        )

        window.browse_lut()

        assert backend.loaded_luts == ["custom.lut"]
        assert settings.value("calibration/lut_path") == "custom.lut"
    finally:
        window.close()


def test_browsed_wfc_loads_immediately_when_connected(qt_app, settings, monkeypatch):
    window = MainWindow(backend_mode="sim", settings=settings, auto_connect=False)
    try:
        backend = SpyBackend()
        backend.connect()
        window.backend = backend
        monkeypatch.setattr(
            QFileDialog,
            "getOpenFileName",
            lambda *args, **kwargs: ("custom.bmp", ""),
        )

        window.browse_wfc()

        assert backend.loaded_wfcs == ["custom.bmp"]
        assert settings.value("calibration/wfc_path") == "custom.bmp"
    finally:
        window.close()


def test_default_lut_and_wfc_clear_settings_and_load_backend_defaults(qt_app, settings):
    settings.setValue("calibration/lut_path", "custom.lut")
    settings.setValue("calibration/wfc_path", "custom.bmp")
    window = MainWindow(backend_mode="sim", settings=settings, auto_connect=False)
    try:
        backend = SpyBackend()
        backend.connect("custom.lut", "custom.bmp")
        window.backend = backend

        window.use_default_lut()
        window.use_default_wfc()

        assert backend.loaded_luts == [None]
        assert backend.loaded_wfcs == [None]
        assert settings.value("calibration/lut_path") is None
        assert settings.value("calibration/wfc_path") is None
        assert window.lut_path_edit.text() == ""
        assert window.wfc_path_edit.text() == ""
    finally:
        window.close()
