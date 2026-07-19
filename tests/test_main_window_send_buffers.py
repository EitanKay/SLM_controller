import os

import numpy as np
import pytest
from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QPushButton, QTabWidget

from src.slm_gui.backends import SimulatedSLMBackend
from src.slm_gui.image_ops import load_strict_meadowlark_bmp
from src.slm_gui.main_window import CollapsibleSection, MainWindow


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
        self.sent_patterns = []

    def load_lut(self, path):
        self.loaded_luts.append(path)
        super().load_lut(path)

    def load_wfc(self, path):
        self.loaded_wfcs.append(path)
        super().load_wfc(path)

    def send(self, pattern):
        self.sent_patterns.append(np.asarray(pattern).copy())
        super().send(pattern)


def test_mask_generation_tab_is_first(qt_app, settings):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        tabs = window.findChild(QTabWidget)

        assert tabs.tabText(0) == "Mask Generation"
        assert tabs.tabText(1) == "Direct Control"
        assert tabs.tabText(2) == "Hardware Settings"
    finally:
        window.close()


def test_generation_tab_exposes_new_panels_and_removes_tem_button(qt_app, settings):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        sections = window.findChildren(CollapsibleSection)
        section_titles = [section.title() for section in sections]
        button_texts = {button.text() for button in window.findChildren(QPushButton)}

        assert section_titles == ["Target", "Control", "Algorithm"]
        assert "Use TEM Target" not in button_texts
        assert "Apply" in button_texts
        assert "Load Image" in button_texts
        assert "Load Config" in button_texts
        assert "Save Config" in button_texts
    finally:
        window.close()


def test_generation_sections_have_expected_defaults_and_toggle(qt_app, settings):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        assert window.target_section.is_expanded()
        assert window.control_section.is_expanded()
        assert not window.algorithm_section.is_expanded()
        assert not window.target_section.content_widget.isHidden()
        assert not window.control_section.content_widget.isHidden()
        assert window.algorithm_section.content_widget.isHidden()

        window.algorithm_section.header_button.click()

        assert window.algorithm_section.is_expanded()
        assert not window.algorithm_section.content_widget.isHidden()
    finally:
        window.close()


def test_config_buttons_are_side_by_side(qt_app, settings):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        buttons = {button.text(): button for button in window.findChildren(QPushButton)}
        load_button = buttons["Load Config"]
        save_button = buttons["Save Config"]

        assert load_button.parent() is save_button.parent()
        assert isinstance(load_button.parent().layout(), QHBoxLayout)
    finally:
        window.close()


def test_default_generation_target_is_tem_hg_without_generating_mask(qt_app, settings):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        assert window.target_source_combo.currentText() == "TEM/HG"
        assert window.algorithm_combo.currentText() == "WGS-Leonardo"
        assert window.input_profile_combo.currentData() == "uniform"
        assert window.gaussian_waist_spin.value() == pytest.approx(140.8)
        assert not window.gaussian_waist_spin.isEnabled()
        assert window.gaussian_waist_label.isHidden()
        assert window.gaussian_waist_spin.isHidden()
        assert window.offset_x_spin.minimum() == -500.0
        assert window.offset_x_spin.maximum() == 500.0
        assert window.offset_y_spin.minimum() == -500.0
        assert window.offset_y_spin.maximum() == 500.0
        assert window.current_target is not None
        assert window.base_phase16 is None
        assert window.send_ready is None
        assert not window.regen_timer.isActive()
    finally:
        window.close()


def test_target_source_switch_uses_loaded_file_target(qt_app, settings):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        file_target = np.full((512, 512), 77, dtype=np.uint8)
        window.file_target = file_target

        window.target_source_combo.setCurrentText("from file")

        assert window.target_stack.currentIndex() == 1
        np.testing.assert_array_equal(window.current_target, file_target)
        assert window.regen_timer.isActive()
    finally:
        window.close()


def test_algorithm_changes_wait_for_apply_but_control_changes_schedule_generation(
    qt_app, settings
):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        window.regen_timer.stop()

        window.algorithm_combo.setCurrentText("GS")
        assert not window.regen_timer.isActive()

        window.input_profile_combo.setCurrentText("Gaussian")
        window.gaussian_waist_spin.setValue(125.0)
        assert window.gaussian_waist_spin.isEnabled()
        assert not window.gaussian_waist_label.isHidden()
        assert not window.gaussian_waist_spin.isHidden()
        assert not window.regen_timer.isActive()

        window.invert_check.setChecked(True)
        assert window.regen_timer.isActive()
    finally:
        window.close()


def test_custom_input_beam_loads_without_automatic_generation(
    qt_app, settings, monkeypatch, tmp_path
):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        rgb = np.zeros((512, 512, 3), dtype=np.uint8)
        rgb[..., 1] = 255
        image_path = tmp_path / "measured-beam.png"
        Image.fromarray(rgb, mode="RGB").save(image_path)
        monkeypatch.setattr(
            QFileDialog,
            "getOpenFileName",
            lambda *args, **kwargs: (str(image_path), ""),
        )
        window.input_profile_combo.setCurrentText("Custom")
        window.regen_timer.stop()

        window.open_custom_input_image()

        assert not window.custom_input_row_label.isHidden()
        assert not window.custom_input_widget.isHidden()
        assert window.custom_input_name == "measured-beam.png"
        assert window.custom_input_amplitude.shape == (512, 512)
        assert window.custom_input_amplitude[0, 0] == pytest.approx(150 / 255)
        assert not window.regen_timer.isActive()
    finally:
        window.close()


def test_custom_input_beam_must_be_loaded_before_generation(
    qt_app, settings, monkeypatch
):
    window = MainWindow(backend_mode="sim", settings=settings)
    errors = []
    try:
        monkeypatch.setattr(window, "_show_error", lambda title, message: errors.append((title, message)))
        window.input_profile_combo.setCurrentText("Custom")

        window.generate_mask()

        assert errors == [("No input beam", "Load a custom input beam image first.")]
        assert window.worker_thread is None
    finally:
        window.close()


def test_input_beam_settings_are_persisted(qt_app, settings):
    first = MainWindow(backend_mode="sim", settings=settings)
    try:
        first.input_profile_combo.setCurrentText("Gaussian")
        first.gaussian_waist_spin.setValue(173.5)
    finally:
        first.close()

    restored = MainWindow(backend_mode="sim", settings=settings)
    try:
        assert restored.input_profile_combo.currentData() == "gaussian"
        assert restored.gaussian_waist_spin.value() == pytest.approx(173.5)
        assert restored.gaussian_waist_spin.isEnabled()
        assert not restored.gaussian_waist_label.isHidden()
        assert not restored.gaussian_waist_spin.isHidden()
    finally:
        restored.close()


def test_invalid_saved_input_beam_settings_fall_back_to_defaults(qt_app, settings):
    settings.setValue("generation/input_profile", "invalid")
    settings.setValue("generation/gaussian_waist_px", "not-a-number")

    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        assert window.input_profile_combo.currentData() == "uniform"
        assert window.gaussian_waist_spin.value() == pytest.approx(140.8)
        assert not window.gaussian_waist_spin.isEnabled()
        assert window.gaussian_waist_label.isHidden()
        assert window.gaussian_waist_spin.isHidden()
    finally:
        window.close()


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


def test_generation_finished_sends_offset_adjusted_final_mask(qt_app, settings):
    window = MainWindow(backend_mode="sim", settings=settings, auto_connect=False)
    try:
        backend = SpyBackend()
        backend.connect()
        window.backend = backend
        window.offset_x_spin.setValue(1.0)

        window._generation_finished(np.zeros((2, 4), dtype=np.uint16))

        assert window.base_phase16[0, 1] == 0
        assert window.final_phase16[0, 1] == 16384
        np.testing.assert_array_equal(
            backend.sent_patterns[-1],
            np.array([[0, 64, 128, 191], [0, 64, 128, 191]], dtype=np.uint8),
        )
    finally:
        window.close()


def test_save_generated_bmp_uses_base_phase_not_offset_final(
    qt_app, settings, monkeypatch, tmp_path
):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        out_path = tmp_path / "phase.bmp"
        base = np.zeros((512, 512), dtype=np.uint16)
        base[:, 1] = 1234
        window.base_phase16 = base
        window.offset_x_spin.setValue(1.0)
        window._apply_final_phase(auto_send=False)
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            lambda *args, **kwargs: (str(out_path), ""),
        )

        window.save_generated_bmp()
        saved, _rgb = load_strict_meadowlark_bmp(out_path)

        np.testing.assert_array_equal(saved, base)
    finally:
        window.close()


def test_generation_config_round_trip_restores_all_controls_and_embedded_images(
    qt_app, settings, monkeypatch, tmp_path
):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        window.config_directory = tmp_path / "configs"
        target = np.arange(512 * 512, dtype=np.uint32).reshape(512, 512).astype(np.uint8)
        beam_pixels = np.full((512, 512), 51, dtype=np.uint8)
        beam_pixels[100:200, 100:200] = 204
        window.file_target = target.copy()
        window.file_target_name = "target-source.png"
        window.target_source_combo.setCurrentText("from file")
        window.hg_n_spin.setValue(3)
        window.hg_m_spin.setValue(5)
        window.hg_waist_spin.setValue(92.5)
        window.hg_norm_combo.setCurrentText("power")
        window.hg_rotation_spin.setValue(-22.5)
        window.algorithm_combo.setCurrentText("WGS-Wu")
        window.iterations_spin.setValue(81)
        window.seed_spin.setValue(901)
        window.input_profile_combo.setCurrentText("Custom")
        window.gaussian_waist_spin.setValue(188.5)
        window.custom_input_amplitude = beam_pixels.astype(np.float64) / 255.0
        window.custom_input_name = "beam-source.tif"
        window.invert_check.setChecked(True)
        window.flip_x_check.setChecked(True)
        window.flip_y_check.setChecked(False)
        window.offset_x_spin.setValue(11.25)
        window.offset_y_spin.setValue(-9.5)

        chosen_save = tmp_path / "configs" / "experiment"
        save_dialog_initial_paths = []

        def choose_save(*args, **kwargs):
            save_dialog_initial_paths.append(args[2])
            return str(chosen_save), ""

        monkeypatch.setattr(QFileDialog, "getSaveFileName", choose_save)
        window.save_generation_config()
        saved_path = chosen_save.with_suffix(".slmconfig")

        assert save_dialog_initial_paths == [
            str(window.config_directory / "mask_config.slmconfig")
        ]
        assert saved_path.is_file()

        window.target_source_combo.setCurrentText("TEM/HG")
        window.hg_n_spin.setValue(0)
        window.algorithm_combo.setCurrentText("GS")
        window.iterations_spin.setValue(2)
        window.input_profile_combo.setCurrentText("Uniform (plane wave)")
        window.file_target = None
        window.custom_input_amplitude = None
        window.invert_check.setChecked(False)
        window.flip_x_check.setChecked(False)
        window.offset_x_spin.setValue(0)
        window.offset_y_spin.setValue(0)

        monkeypatch.setattr(
            QFileDialog,
            "getOpenFileName",
            lambda *args, **kwargs: (str(saved_path), ""),
        )
        generation_requests = []
        monkeypatch.setattr(
            window, "_schedule_generation", lambda: generation_requests.append(True)
        )

        window.load_generation_config()

        assert generation_requests == [True]
        assert window.target_source_combo.currentText() == "from file"
        assert window.hg_n_spin.value() == 3
        assert window.hg_m_spin.value() == 5
        assert window.hg_waist_spin.value() == pytest.approx(92.5)
        assert window.hg_norm_combo.currentText() == "power"
        assert window.hg_rotation_spin.value() == pytest.approx(-22.5)
        assert window.algorithm_combo.currentText() == "WGS-Wu"
        assert window.iterations_spin.value() == 81
        assert window.seed_spin.value() == 901
        assert window.input_profile_combo.currentData() == "custom"
        assert window.gaussian_waist_spin.value() == pytest.approx(188.5)
        assert window.invert_check.isChecked()
        assert window.flip_x_check.isChecked()
        assert not window.flip_y_check.isChecked()
        assert window.offset_x_spin.value() == pytest.approx(11.25)
        assert window.offset_y_spin.value() == pytest.approx(-9.5)
        assert window.file_target_name == "target-source.png"
        assert window.custom_input_name == "beam-source.tif"
        np.testing.assert_array_equal(window.file_target, target)
        np.testing.assert_array_equal(
            np.uint8(np.rint(window.custom_input_amplitude * 255)), beam_pixels
        )
    finally:
        window.close()


def test_invalid_generation_config_does_not_change_current_state(
    qt_app, settings, monkeypatch, tmp_path
):
    window = MainWindow(backend_mode="sim", settings=settings)
    errors = []
    try:
        window.config_directory = tmp_path
        invalid_path = tmp_path / "invalid.slmconfig"
        invalid_path.write_text('{"format": "SLMControl mask configuration", "version": 99}')
        window.algorithm_combo.setCurrentText("GS")
        window.iterations_spin.setValue(17)
        window.regen_timer.stop()
        monkeypatch.setattr(
            QFileDialog,
            "getOpenFileName",
            lambda *args, **kwargs: (str(invalid_path), ""),
        )
        monkeypatch.setattr(
            window, "_show_error", lambda title, message: errors.append((title, message))
        )

        window.load_generation_config()

        assert window.algorithm_combo.currentText() == "GS"
        assert window.iterations_spin.value() == 17
        assert not window.regen_timer.isActive()
        assert errors and errors[0][0] == "Invalid configuration"
        assert "Unsupported mask configuration version" in errors[0][1]
    finally:
        window.close()


def test_generate_while_busy_queues_latest_request(qt_app, settings):
    window = MainWindow(backend_mode="sim", settings=settings)
    try:
        window.worker_thread = object()

        window.generate_mask()

        assert window.pending_regeneration is True
    finally:
        window.worker_thread = None
        window.close()
