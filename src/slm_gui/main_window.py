from __future__ import annotations

from pathlib import Path

import numpy as np
from PyQt6.QtCore import QThread, QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.slm_gui.backends import HardwareSLMBackend, SimulatedSLMBackend, SLMBackend
from src.slm_gui.holography import generate_hg_target_uint8
from src.slm_gui.image_ops import (
    ImageValidationError,
    apply_discrete_transform,
    apply_target_transform,
    load_strict_meadowlark_bmp,
    load_target_png,
    save_meadowlark_bmp,
    uint16_to_calibrated_input_uint8,
    uint16_to_preview_uint8,
)
from src.slm_gui.workers import GenerationRequest, HologramWorker


def qpixmap_from_gray(arr: np.ndarray, max_side: int = 360) -> QPixmap:
    arr = np.ascontiguousarray(arr, dtype=np.uint8)
    h, w = arr.shape
    image = QImage(arr.data, w, h, w, QImage.Format.Format_Grayscale8).copy()
    pixmap = QPixmap.fromImage(image)
    return pixmap.scaled(
        max_side,
        max_side,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


class ImagePreview(QLabel):
    def __init__(self, title: str):
        super().__init__(title)
        self.setObjectName("Preview")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 320)
        self.setText(title)

    def set_gray(self, arr: np.ndarray) -> None:
        self.setPixmap(qpixmap_from_gray(arr))

    def reset_text(self, text: str) -> None:
        self.setPixmap(QPixmap())
        self.setText(text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SLM Control")

        self.backend: SLMBackend = SimulatedSLMBackend()
        self.selected_lut_path: str | None = None
        self.selected_wfc_path: str | None = None

        self.direct_value16: np.ndarray | None = None
        self.direct_rgb: np.ndarray | None = None
        self.direct_rotation_turns = 0

        self.original_target: np.ndarray | None = None
        self.current_target: np.ndarray | None = None
        self.current_phase16: np.ndarray | None = None
        self.send_ready: np.ndarray | None = None

        self.worker_thread: QThread | None = None
        self.worker: HologramWorker | None = None

        self.regen_timer = QTimer(self)
        self.regen_timer.setInterval(450)
        self.regen_timer.setSingleShot(True)
        self.regen_timer.timeout.connect(self.generate_mask)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)
        layout.addWidget(self._build_top_bar())
        layout.addWidget(self._build_tabs(), 1)
        self.message_label = QLabel("Ready")
        layout.addWidget(self.message_label)
        self.setCentralWidget(root)
        self._refresh_status()

    def _build_top_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("TopBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)

        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["Simulator", "Hardware"])
        self.backend_combo.currentTextChanged.connect(self._select_backend)

        self.status_pill = QLabel("Disconnected")
        self.status_pill.setObjectName("StatusPill")

        connect_button = QPushButton("Connect")
        connect_button.clicked.connect(self.connect_backend)
        disconnect_button = QPushButton("Disconnect")
        disconnect_button.clicked.connect(self.disconnect_backend)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_slm)
        send_button = QPushButton("Send to SLM")
        send_button.setObjectName("PrimaryButton")
        send_button.clicked.connect(self.send_to_slm)

        layout.addWidget(QLabel("Backend"))
        layout.addWidget(self.backend_combo)
        layout.addWidget(self.status_pill)
        layout.addStretch(1)
        layout.addWidget(connect_button)
        layout.addWidget(disconnect_button)
        layout.addWidget(clear_button)
        layout.addWidget(send_button)
        return frame

    def _build_tabs(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.addTab(self._build_direct_tab(), "Direct Control")
        tabs.addTab(self._build_generation_tab(), "Mask Generation")
        tabs.addTab(self._build_hardware_tab(), "Hardware Settings")
        return tabs

    def _build_direct_tab(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        controls = QGroupBox("Direct BMP")
        form = QVBoxLayout(controls)

        open_button = QPushButton("Open BMP")
        open_button.clicked.connect(self.open_direct_bmp)
        flip_x = QPushButton("Flip Horizontal")
        flip_x.clicked.connect(lambda: self._transform_direct(flip_x=True))
        flip_y = QPushButton("Flip Vertical")
        flip_y.clicked.connect(lambda: self._transform_direct(flip_y=True))
        rotate = QPushButton("Rotate 90")
        rotate.clicked.connect(lambda: self._transform_direct(rotate=True))

        self.direct_path_label = QLabel("No BMP loaded")
        self.direct_path_label.setWordWrap(True)
        form.addWidget(open_button)
        form.addWidget(flip_x)
        form.addWidget(flip_y)
        form.addWidget(rotate)
        form.addSpacing(8)
        form.addWidget(self.direct_path_label)
        form.addStretch(1)

        self.direct_preview = ImagePreview("Phase mask preview")
        layout.addWidget(controls)
        layout.addWidget(self.direct_preview, 1)
        return widget

    def _build_generation_tab(self) -> QWidget:
        widget = QWidget()
        layout = QGridLayout(widget)
        controls = QGroupBox("Target and Algorithm")
        form = QFormLayout(controls)

        upload_button = QPushButton("Open PNG")
        upload_button.clicked.connect(self.open_target_png)
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["WGS", "GS"])
        self.iterations_spin = QSpinBox()
        self.iterations_spin.setRange(1, 500)
        self.iterations_spin.setValue(30)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 999999)
        self.seed_spin.setValue(0)

        self.invert_check = QCheckBox()
        self.flip_x_check = QCheckBox()
        self.flip_y_check = QCheckBox()
        for check in (self.invert_check, self.flip_x_check, self.flip_y_check):
            check.stateChanged.connect(self._target_controls_changed)

        generate_button = QPushButton("Generate Mask")
        generate_button.setObjectName("PrimaryButton")
        generate_button.clicked.connect(self.generate_mask)
        save_button = QPushButton("Save BMP")
        save_button.clicked.connect(self.save_generated_bmp)

        form.addRow(upload_button)
        form.addRow("Algorithm", self.algorithm_combo)
        form.addRow("Iterations", self.iterations_spin)
        form.addRow("Seed", self.seed_spin)
        form.addRow("Invert target", self.invert_check)
        form.addRow("Flip horizontal", self.flip_x_check)
        form.addRow("Flip vertical", self.flip_y_check)
        form.addRow(generate_button)
        form.addRow(save_button)

        hg_box = QGroupBox("TEM / HG Target")
        hg_form = QFormLayout(hg_box)
        self.hg_n_spin = QSpinBox()
        self.hg_n_spin.setRange(0, 20)
        self.hg_m_spin = QSpinBox()
        self.hg_m_spin.setRange(0, 20)
        self.hg_waist_spin = QDoubleSpinBox()
        self.hg_waist_spin.setRange(1.0, 512.0)
        self.hg_waist_spin.setValue(80.0)
        self.hg_waist_spin.setDecimals(1)
        self.hg_norm_combo = QComboBox()
        self.hg_norm_combo.addItems(["peak", "power", "none"])
        self.hg_rotation_spin = QDoubleSpinBox()
        self.hg_rotation_spin.setRange(-180.0, 180.0)
        self.hg_rotation_spin.setDecimals(1)
        self.hg_rotation_spin.setSingleStep(1.0)
        hg_button = QPushButton("Use TEM Target")
        hg_button.clicked.connect(self.use_hg_target)
        hg_form.addRow("n", self.hg_n_spin)
        hg_form.addRow("m", self.hg_m_spin)
        hg_form.addRow("Waist", self.hg_waist_spin)
        hg_form.addRow("Normalize", self.hg_norm_combo)
        hg_form.addRow("Rotation", self.hg_rotation_spin)
        hg_form.addRow(hg_button)

        self.target_preview = ImagePreview("Target preview")
        self.phase_preview = ImagePreview("Generated phase mask")

        layout.addWidget(controls, 0, 0)
        layout.addWidget(hg_box, 1, 0)
        layout.addWidget(self.target_preview, 0, 1, 2, 1)
        layout.addWidget(self.phase_preview, 0, 2, 2, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        return widget

    def _build_hardware_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        box = QGroupBox("LUT and WFC")
        form = QGridLayout(box)

        self.lut_path_edit = QLineEdit()
        self.lut_path_edit.setReadOnly(True)
        self.wfc_path_edit = QLineEdit()
        self.wfc_path_edit.setReadOnly(True)

        browse_lut = QPushButton("Browse LUT")
        browse_lut.clicked.connect(self.browse_lut)
        load_lut = QPushButton("Load LUT")
        load_lut.clicked.connect(self.load_selected_lut)
        default_lut = QPushButton("Use Default LUT")
        default_lut.clicked.connect(self.use_default_lut)
        browse_wfc = QPushButton("Browse WFC")
        browse_wfc.clicked.connect(self.browse_wfc)
        load_wfc = QPushButton("Load WFC")
        load_wfc.clicked.connect(self.load_selected_wfc)
        default_wfc = QPushButton("Use Default WFC")
        default_wfc.clicked.connect(self.use_default_wfc)

        self.lut_status_label = QLabel("LUT: default / not loaded")
        self.wfc_status_label = QLabel("WFC: default / not loaded")
        self.calibration_status_label = QLabel("Calibration: disabled")

        form.addWidget(QLabel("LUT"), 0, 0)
        form.addWidget(self.lut_path_edit, 0, 1)
        form.addWidget(browse_lut, 0, 2)
        form.addWidget(load_lut, 0, 3)
        form.addWidget(default_lut, 0, 4)
        form.addWidget(QLabel("WFC"), 1, 0)
        form.addWidget(self.wfc_path_edit, 1, 1)
        form.addWidget(browse_wfc, 1, 2)
        form.addWidget(load_wfc, 1, 3)
        form.addWidget(default_wfc, 1, 4)
        form.addWidget(self.lut_status_label, 2, 1, 1, 4)
        form.addWidget(self.wfc_status_label, 3, 1, 1, 4)
        form.addWidget(self.calibration_status_label, 4, 1, 1, 4)
        form.setColumnStretch(1, 1)

        layout.addWidget(box)
        layout.addStretch(1)
        return widget

    def _select_backend(self, name: str) -> None:
        try:
            self.backend.disconnect()
        except Exception:
            pass
        self.backend = HardwareSLMBackend() if name == "Hardware" else SimulatedSLMBackend()
        self._refresh_status()

    def connect_backend(self) -> None:
        try:
            self.backend.connect(self.selected_lut_path, self.selected_wfc_path)
        except Exception as exc:
            self._show_error("Connection failed", str(exc))
        self._refresh_status()

    def disconnect_backend(self) -> None:
        try:
            self.backend.disconnect()
        except Exception as exc:
            self._show_error("Disconnect failed", str(exc))
        self._refresh_status()

    def clear_slm(self) -> None:
        try:
            self.backend.clear()
        except Exception as exc:
            self._show_error("Clear failed", str(exc))
        self._refresh_status()

    def send_to_slm(self) -> None:
        if self.send_ready is None:
            self._show_error("Nothing to send", "Load or generate a phase mask first.")
            return
        try:
            self.backend.send(self.send_ready)
        except Exception as exc:
            self._show_error("Send failed", str(exc))
        self._refresh_status()

    def browse_lut(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose LUT", "", "LUT files (*.lut)")
        if not path:
            return
        self.selected_lut_path = path
        self.lut_path_edit.setText(path)
        self._refresh_status()

    def browse_wfc(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose WFC", "", "Bitmap files (*.bmp);;All files (*.*)"
        )
        if not path:
            return
        self.selected_wfc_path = path
        self.wfc_path_edit.setText(path)
        self._refresh_status()

    def load_selected_lut(self) -> None:
        try:
            self.backend.load_lut(self.selected_lut_path)
        except Exception as exc:
            self._show_error("LUT load failed", str(exc))
        self._refresh_status()

    def use_default_lut(self) -> None:
        self.selected_lut_path = None
        self.lut_path_edit.clear()
        try:
            if self.backend.status().connected:
                self.backend.load_lut(None)
        except Exception as exc:
            self._show_error("Default LUT load failed", str(exc))
        self._refresh_status()

    def load_selected_wfc(self) -> None:
        try:
            self.backend.load_wfc(self.selected_wfc_path)
        except Exception as exc:
            self._show_error("WFC load failed", str(exc))
        self._refresh_status()

    def use_default_wfc(self) -> None:
        self.selected_wfc_path = None
        self.wfc_path_edit.clear()
        try:
            if self.backend.status().connected:
                self.backend.load_wfc(None)
        except Exception as exc:
            self._show_error("Default WFC load failed", str(exc))
        self._refresh_status()

    def open_direct_bmp(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open SLM BMP", "", "BMP files (*.bmp)")
        if not path:
            return
        try:
            value16, _rgb = load_strict_meadowlark_bmp(path)
        except ImageValidationError as exc:
            self._show_error("Invalid BMP", str(exc))
            return

        self.direct_value16 = value16
        self.direct_rgb = None
        self.direct_rotation_turns = 0
        self.direct_path_label.setText(str(Path(path)))
        self._set_direct_send_ready()
        self._set_message("Loaded direct BMP")

    def _transform_direct(
        self, flip_x: bool = False, flip_y: bool = False, rotate: bool = False
    ) -> None:
        if self.direct_value16 is None:
            return
        if rotate:
            self.direct_rotation_turns = (self.direct_rotation_turns + 1) % 4
        self.direct_value16 = apply_discrete_transform(
            self.direct_value16,
            flip_x=flip_x,
            flip_y=flip_y,
            rotate_quarter_turns=1 if rotate else 0,
        )
        self._set_direct_send_ready()

    def _set_direct_send_ready(self) -> None:
        if self.direct_value16 is None:
            return
        self.direct_rgb = None
        self.send_ready = uint16_to_calibrated_input_uint8(self.direct_value16)
        self.direct_preview.set_gray(uint16_to_preview_uint8(self.direct_value16))

    def open_target_png(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open target PNG", "", "PNG files (*.png)")
        if not path:
            return
        try:
            self.original_target = load_target_png(path)
        except ImageValidationError as exc:
            self._show_error("Invalid PNG", str(exc))
            return
        self._update_target_from_controls()
        self._set_message("Loaded target PNG")

    def _target_controls_changed(self) -> None:
        self._update_target_from_controls()
        if self.current_target is not None:
            self.regen_timer.start()

    def _update_target_from_controls(self) -> None:
        if self.original_target is None:
            return
        self.current_target = apply_target_transform(
            self.original_target,
            invert=self.invert_check.isChecked(),
            flip_x=self.flip_x_check.isChecked(),
            flip_y=self.flip_y_check.isChecked(),
        )
        self.target_preview.set_gray(self.current_target)

    def use_hg_target(self) -> None:
        try:
            target = generate_hg_target_uint8(
                self.hg_n_spin.value(),
                self.hg_m_spin.value(),
                self.hg_waist_spin.value(),
                normalize=self.hg_norm_combo.currentText(),
                rotation_degrees=self.hg_rotation_spin.value(),
            )
        except Exception as exc:
            self._show_error("TEM generation failed", str(exc))
            return
        self.original_target = target
        self._update_target_from_controls()
        self.regen_timer.start()

    def generate_mask(self) -> None:
        if self.current_target is None:
            self._show_error("No target", "Open a PNG or generate a TEM target first.")
            return
        if self.worker_thread is not None:
            self._set_message("Generation already running")
            return

        request = GenerationRequest(
            target=self.current_target.copy(),
            algorithm=self.algorithm_combo.currentText(),
            iterations=self.iterations_spin.value(),
            seed=self.seed_spin.value(),
        )
        self.worker_thread = QThread(self)
        self.worker = HologramWorker(request)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._generation_finished)
        self.worker.failed.connect(self._generation_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._generation_thread_finished)
        self.worker_thread.start()
        self._set_message("Generating phase mask...")

    def _generation_finished(self, phase16: object) -> None:
        self.current_phase16 = np.asarray(phase16, dtype=np.uint16)
        self.send_ready = uint16_to_calibrated_input_uint8(self.current_phase16)
        self.phase_preview.set_gray(uint16_to_preview_uint8(self.current_phase16))
        self._set_message("Generated phase mask")

    def _generation_failed(self, message: str) -> None:
        self._show_error("Generation failed", message)

    def _generation_thread_finished(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
        if self.worker_thread is not None:
            self.worker_thread.deleteLater()
        self.worker = None
        self.worker_thread = None

    def save_generated_bmp(self) -> None:
        if self.current_phase16 is None:
            self._show_error("Nothing to save", "Generate a phase mask first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Meadowlark BMP", "phase_mask.bmp", "BMP files (*.bmp)"
        )
        if not path:
            return
        try:
            save_meadowlark_bmp(self.current_phase16, path)
        except Exception as exc:
            self._show_error("Save failed", str(exc))
            return
        self._set_message(f"Saved {path}")

    def _refresh_status(self) -> None:
        status = self.backend.status()
        state = "Connected" if status.connected else "Disconnected"
        if status.mode == "Simulator" and status.connected:
            state = "Simulator"
        self.status_pill.setText(f"{status.mode}: {state}")
        self.lut_status_label.setText(
            f"LUT: {'loaded' if status.lut_loaded else 'not loaded'}"
            f" ({status.lut_path or 'default'})"
        )
        self.wfc_status_label.setText(
            f"WFC: {'loaded' if status.wfc_loaded else 'not loaded'}"
            f" ({status.wfc_path or 'default'})"
        )
        self.calibration_status_label.setText(
            f"Calibration: {'enabled' if status.calibration_enabled else 'disabled'}"
        )
        self._set_message(status.message or state)

    def _set_message(self, text: str) -> None:
        self.message_label.setText(text)

    def _show_error(self, title: str, message: str) -> None:
        self.message_label.setText(f"{title}: {message}")
        QMessageBox.warning(self, title, message)
