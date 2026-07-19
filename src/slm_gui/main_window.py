from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
from PyQt6.QtCore import QSettings, QSignalBlocker, QThread, QTimer, Qt
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
    QScrollArea,
    QSpinBox,
    QDoubleSpinBox,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.slm_gui.backends import HardwareSLMBackend, SimulatedSLMBackend, SLMBackend
from src.slm_gui.holography import (
    DEFAULT_GAUSSIAN_WAIST_PX,
    MAX_GAUSSIAN_WAIST_PX,
    MIN_GAUSSIAN_WAIST_PX,
    generate_hg_target_uint8,
)
from src.slm_gui.image_ops import (
    ImageValidationError,
    apply_discrete_transform,
    apply_target_transform,
    load_strict_meadowlark_bmp,
    load_input_beam_image,
    load_target_image,
    load_target_png,
    save_meadowlark_bmp,
    apply_phase_offset_wraps,
    uint16_to_calibrated_input_uint8,
    uint16_to_preview_uint8,
)
from src.slm_gui.mask_config import (
    CONFIG_EXTENSION,
    EmbeddedGrayImage,
    MaskConfigError,
    MaskConfiguration,
    SUPPORTED_ALGORITHMS,
    default_config_directory,
    load_mask_configuration,
    save_mask_configuration,
)
from src.slm_gui.workers import GenerationRequest, HologramWorker

SETTINGS_ORG = "SLM"
SETTINGS_APP = "SLMControl"
LUT_SETTING_KEY = "calibration/lut_path"
WFC_SETTING_KEY = "calibration/wfc_path"
INPUT_PROFILE_SETTING_KEY = "generation/input_profile"
GAUSSIAN_WAIST_SETTING_KEY = "generation/gaussian_waist_px"
GS_ALGORITHMS = list(SUPPORTED_ALGORITHMS)


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


class CollapsibleSection(QFrame):
    def __init__(self, title: str, *, expanded: bool):
        super().__init__()
        self.setObjectName("CollapsibleSection")
        self._title = title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header_button = QToolButton()
        self.header_button.setObjectName("CollapsibleHeader")
        self.header_button.setText(title)
        self.header_button.setCheckable(True)
        self.header_button.setChecked(expanded)
        self.header_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.header_button.toggled.connect(self.set_expanded)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("CollapsibleContent")
        layout.addWidget(self.header_button)
        layout.addWidget(self.content_widget)
        self.set_expanded(expanded)

    def title(self) -> str:
        return self._title

    def set_content_layout(self, content_layout: QFormLayout | QVBoxLayout) -> None:
        content_layout.setContentsMargins(12, 8, 12, 12)
        self.content_widget.setLayout(content_layout)

    def is_expanded(self) -> bool:
        return self.header_button.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        if self.header_button.isChecked() != expanded:
            self.header_button.setChecked(expanded)
        self.header_button.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self.content_widget.setVisible(expanded)


class MainWindow(QMainWindow):
    def __init__(
        self,
        backend_mode: Literal["hardware", "sim"] = "hardware",
        settings: QSettings | None = None,
        auto_connect: bool = True,
    ):
        super().__init__()
        self.setWindowTitle("SLM Control")

        self.settings = settings or QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.backend_mode = backend_mode
        self.backend: SLMBackend = (
            SimulatedSLMBackend() if backend_mode == "sim" else HardwareSLMBackend()
        )
        self.selected_lut_path = self._settings_path(LUT_SETTING_KEY)
        self.selected_wfc_path = self._settings_path(WFC_SETTING_KEY)
        self.config_directory = default_config_directory(create=False)

        self.direct_value16: np.ndarray | None = None
        self.direct_rgb: np.ndarray | None = None
        self.direct_rotation_turns = 0

        self.original_target: np.ndarray | None = None
        self.current_target: np.ndarray | None = None
        self.file_target: np.ndarray | None = None
        self.file_target_name: str | None = None
        self.custom_input_amplitude: np.ndarray | None = None
        self.custom_input_name: str | None = None
        self.base_phase16: np.ndarray | None = None
        self.final_phase16: np.ndarray | None = None
        self.current_phase16: np.ndarray | None = None
        self.send_ready: np.ndarray | None = None
        self.pending_regeneration = False

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
        self._sync_calibration_path_fields()
        self._set_target_from_hg(schedule_generation=False)
        self._refresh_status()
        if auto_connect:
            self._auto_connect_backend()

    def _build_top_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("TopBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)

        self.status_pill = QLabel("Disconnected")
        self.status_pill.setObjectName("StatusPill")

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_slm)
        send_button = QPushButton("Send to SLM")
        send_button.setObjectName("PrimaryButton")
        send_button.clicked.connect(self.send_to_slm)

        layout.addWidget(self.status_pill)
        layout.addStretch(1)
        layout.addWidget(clear_button)
        layout.addWidget(send_button)
        return frame

    def _build_tabs(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.addTab(self._build_generation_tab(), "Mask Generation")
        tabs.addTab(self._build_direct_tab(), "Direct Control")
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

        self.target_section = CollapsibleSection("Target", expanded=True)
        target_layout = QVBoxLayout()
        self.target_section.set_content_layout(target_layout)
        self.target_source_combo = QComboBox()
        self.target_source_combo.addItems(["TEM/HG", "from file"])
        self.target_source_combo.currentIndexChanged.connect(self._target_source_changed)
        target_layout.addWidget(self.target_source_combo)

        self.target_stack = QStackedWidget()
        hg_widget = QWidget()
        hg_form = QFormLayout(hg_widget)
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
        hg_form.addRow("n", self.hg_n_spin)
        hg_form.addRow("m", self.hg_m_spin)
        hg_form.addRow("Waist", self.hg_waist_spin)
        hg_form.addRow("Normalize", self.hg_norm_combo)
        hg_form.addRow("Rotation", self.hg_rotation_spin)

        file_widget = QWidget()
        file_layout = QVBoxLayout(file_widget)
        upload_button = QPushButton("Load Image")
        upload_button.clicked.connect(self.open_target_image)
        self.file_target_label = QLabel("No image loaded")
        self.file_target_label.setWordWrap(True)
        file_layout.addWidget(upload_button)
        file_layout.addWidget(self.file_target_label)
        file_layout.addStretch(1)

        self.target_stack.addWidget(hg_widget)
        self.target_stack.addWidget(file_widget)
        target_layout.addWidget(self.target_stack)

        for widget_to_watch in (
            self.hg_n_spin,
            self.hg_m_spin,
            self.hg_waist_spin,
            self.hg_norm_combo,
            self.hg_rotation_spin,
        ):
            if isinstance(widget_to_watch, QComboBox):
                widget_to_watch.currentIndexChanged.connect(self._hg_controls_changed)
            else:
                widget_to_watch.valueChanged.connect(self._hg_controls_changed)

        self.control_section = CollapsibleSection("Control", expanded=True)
        control_form = QFormLayout()
        self.control_section.set_content_layout(control_form)
        self.invert_check = QCheckBox()
        self.flip_x_check = QCheckBox()
        self.flip_y_check = QCheckBox()
        for check in (self.invert_check, self.flip_x_check, self.flip_y_check):
            check.stateChanged.connect(self._target_controls_changed)
        self.offset_x_spin = QDoubleSpinBox()
        self.offset_x_spin.setRange(-500.0, 500.0)
        self.offset_x_spin.setDecimals(3)
        self.offset_x_spin.setSingleStep(0.1)
        self.offset_y_spin = QDoubleSpinBox()
        self.offset_y_spin.setRange(-500.0, 500.0)
        self.offset_y_spin.setDecimals(3)
        self.offset_y_spin.setSingleStep(0.1)
        self.offset_x_spin.valueChanged.connect(self._offset_controls_changed)
        self.offset_y_spin.valueChanged.connect(self._offset_controls_changed)

        generate_button = QPushButton("Generate Mask")
        generate_button.setObjectName("PrimaryButton")
        generate_button.clicked.connect(self.generate_mask)
        save_button = QPushButton("Save BMP")
        save_button.clicked.connect(self.save_generated_bmp)
        config_buttons = QWidget()
        config_buttons_layout = QHBoxLayout(config_buttons)
        config_buttons_layout.setContentsMargins(0, 0, 0, 0)
        config_buttons_layout.setSpacing(8)
        load_config_button = QPushButton("Load Config")
        load_config_button.clicked.connect(self.load_generation_config)
        save_config_button = QPushButton("Save Config")
        save_config_button.clicked.connect(self.save_generation_config)
        config_buttons_layout.addWidget(load_config_button)
        config_buttons_layout.addWidget(save_config_button)

        control_form.addRow("Invert target", self.invert_check)
        control_form.addRow("Flip horizontal", self.flip_x_check)
        control_form.addRow("Flip vertical", self.flip_y_check)
        control_form.addRow("Offset x (2pi wraps)", self.offset_x_spin)
        control_form.addRow("Offset y (2pi wraps)", self.offset_y_spin)
        control_form.addRow(generate_button)
        control_form.addRow(save_button)
        control_form.addRow(config_buttons)

        self.algorithm_section = CollapsibleSection("Algorithm", expanded=False)
        algorithm_form = QFormLayout()
        self.algorithm_section.set_content_layout(algorithm_form)
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(GS_ALGORITHMS)
        self.algorithm_combo.setCurrentText("WGS-Leonardo")
        self.iterations_spin = QSpinBox()
        self.iterations_spin.setRange(1, 500)
        self.iterations_spin.setValue(30)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 999999)
        self.seed_spin.setValue(0)
        self.input_profile_combo = QComboBox()
        self.input_profile_combo.addItem("Uniform (plane wave)", "uniform")
        self.input_profile_combo.addItem("Gaussian", "gaussian")
        self.input_profile_combo.addItem("Custom", "custom")
        profile_index = self.input_profile_combo.findData(self._saved_input_profile())
        self.input_profile_combo.setCurrentIndex(max(profile_index, 0))
        self.gaussian_waist_spin = QDoubleSpinBox()
        self.gaussian_waist_spin.setRange(
            MIN_GAUSSIAN_WAIST_PX, MAX_GAUSSIAN_WAIST_PX
        )
        self.gaussian_waist_spin.setValue(self._saved_gaussian_waist())
        self.gaussian_waist_spin.setDecimals(1)
        self.gaussian_waist_spin.setSingleStep(1.0)
        self.gaussian_waist_spin.setSuffix(" px")
        self.gaussian_waist_spin.setToolTip(
            "Gaussian field amplitude A(r)=exp(-r^2/w^2), so the intensity is "
            "I(r)=exp(-2r^2/w^2) and its statistical sigma is w/2."
        )
        self.custom_input_widget = QWidget()
        custom_input_layout = QVBoxLayout(self.custom_input_widget)
        custom_input_layout.setContentsMargins(0, 0, 0, 0)
        custom_input_layout.setSpacing(4)
        load_input_button = QPushButton("Load Image")
        load_input_button.clicked.connect(self.open_custom_input_image)
        self.custom_input_label = QLabel("No image loaded")
        self.custom_input_label.setWordWrap(True)
        custom_input_layout.addWidget(load_input_button)
        custom_input_layout.addWidget(self.custom_input_label)
        apply_algorithm = QPushButton("Apply")
        apply_algorithm.clicked.connect(self.generate_mask)

        algorithm_form.addRow("Algorithm", self.algorithm_combo)
        algorithm_form.addRow("Iterations", self.iterations_spin)
        algorithm_form.addRow("Seed", self.seed_spin)
        algorithm_form.addRow("Input beam", self.input_profile_combo)
        self.gaussian_waist_label = QLabel("Gaussian waist w")
        algorithm_form.addRow(self.gaussian_waist_label, self.gaussian_waist_spin)
        self.custom_input_row_label = QLabel("Custom image")
        algorithm_form.addRow(self.custom_input_row_label, self.custom_input_widget)
        algorithm_form.addRow(apply_algorithm)
        self.input_profile_combo.currentIndexChanged.connect(
            self._input_profile_changed
        )
        self.gaussian_waist_spin.valueChanged.connect(
            self._gaussian_waist_changed
        )
        self._sync_input_profile_controls()

        self.target_preview = ImagePreview("Target preview")
        self.phase_preview = ImagePreview("Generated phase mask")

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.target_section)
        left_layout.addWidget(self.control_section)
        left_layout.addWidget(self.algorithm_section)
        left_layout.addStretch(1)

        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setFrameShape(QFrame.Shape.NoFrame)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        controls_scroll.setWidget(left)
        controls_scroll.setMinimumWidth(360)

        layout.addWidget(controls_scroll, 0, 0)
        layout.addWidget(self.target_preview, 0, 1)
        layout.addWidget(self.phase_preview, 0, 2)
        layout.setColumnMinimumWidth(0, 360)
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
        default_lut = QPushButton("Use Default LUT")
        default_lut.clicked.connect(self.use_default_lut)
        browse_wfc = QPushButton("Browse WFC")
        browse_wfc.clicked.connect(self.browse_wfc)
        default_wfc = QPushButton("Use Default WFC")
        default_wfc.clicked.connect(self.use_default_wfc)

        self.lut_status_label = QLabel("LUT: default / not loaded")
        self.wfc_status_label = QLabel("WFC: default / not loaded")
        self.calibration_status_label = QLabel("Calibration: disabled")

        form.addWidget(QLabel("LUT"), 0, 0)
        form.addWidget(self.lut_path_edit, 0, 1)
        form.addWidget(browse_lut, 0, 2)
        form.addWidget(default_lut, 0, 3)
        form.addWidget(QLabel("WFC"), 1, 0)
        form.addWidget(self.wfc_path_edit, 1, 1)
        form.addWidget(browse_wfc, 1, 2)
        form.addWidget(default_wfc, 1, 3)
        form.addWidget(self.lut_status_label, 2, 1, 1, 3)
        form.addWidget(self.wfc_status_label, 3, 1, 1, 3)
        form.addWidget(self.calibration_status_label, 4, 1, 1, 3)
        form.setColumnStretch(1, 1)

        layout.addWidget(box)
        layout.addStretch(1)
        return widget

    def _settings_path(self, key: str) -> str | None:
        value = self.settings.value(key, "", str)
        return value or None

    def _save_settings_path(self, key: str, path: str | None) -> None:
        if path:
            self.settings.setValue(key, path)
        else:
            self.settings.remove(key)
        self.settings.sync()

    def _saved_input_profile(self) -> str:
        profile = str(
            self.settings.value(INPUT_PROFILE_SETTING_KEY, "uniform") or ""
        ).strip().lower()
        return profile if profile in {"uniform", "gaussian"} else "uniform"

    def _saved_gaussian_waist(self) -> float:
        value = self.settings.value(
            GAUSSIAN_WAIST_SETTING_KEY, DEFAULT_GAUSSIAN_WAIST_PX
        )
        try:
            waist = float(value)
        except (TypeError, ValueError):
            return DEFAULT_GAUSSIAN_WAIST_PX
        if not np.isfinite(waist) or not (
            MIN_GAUSSIAN_WAIST_PX <= waist <= MAX_GAUSSIAN_WAIST_PX
        ):
            return DEFAULT_GAUSSIAN_WAIST_PX
        return waist

    def _current_input_profile(self) -> str:
        return str(self.input_profile_combo.currentData())

    def _sync_input_profile_controls(self) -> None:
        use_gaussian = self._current_input_profile() == "gaussian"
        use_custom = self._current_input_profile() == "custom"
        self.gaussian_waist_label.setVisible(use_gaussian)
        self.gaussian_waist_spin.setVisible(use_gaussian)
        self.gaussian_waist_spin.setEnabled(use_gaussian)
        self.custom_input_row_label.setVisible(use_custom)
        self.custom_input_widget.setVisible(use_custom)
        self.custom_input_widget.setEnabled(use_custom)

    def _input_profile_changed(self) -> None:
        self._sync_input_profile_controls()
        profile = self._current_input_profile()
        if profile in {"uniform", "gaussian"}:
            self.settings.setValue(INPUT_PROFILE_SETTING_KEY, profile)
            self.settings.sync()

    def _gaussian_waist_changed(self, value: float) -> None:
        self.settings.setValue(GAUSSIAN_WAIST_SETTING_KEY, float(value))
        self.settings.sync()

    def _sync_calibration_path_fields(self) -> None:
        self.lut_path_edit.setText(self.selected_lut_path or "")
        self.wfc_path_edit.setText(self.selected_wfc_path or "")

    def _auto_connect_backend(self) -> None:
        if self.backend_mode == "sim":
            self.connect_backend(show_errors=True)
            return

        while True:
            try:
                self.backend.connect(self.selected_lut_path, self.selected_wfc_path)
            except Exception as exc:
                self._refresh_status()
                self.message_label.setText(f"Hardware not connected: {exc}")
                choice = QMessageBox.warning(
                    self,
                    "Connection failed",
                    f"Could not connect to the SLM hardware.\n\n{exc}\n\n"
                    "Connect the device and press Retry.",
                    QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Retry,
                )
                if choice == QMessageBox.StandardButton.Retry:
                    continue
                self.message_label.setText(
                    "Hardware not connected. Connect the device and restart or "
                    "retry by reopening the app."
                )
                return
            self._refresh_status()
            return

    def connect_backend(self, show_errors: bool = True) -> None:
        try:
            self.backend.connect(self.selected_lut_path, self.selected_wfc_path)
        except Exception as exc:
            if show_errors:
                self._show_error("Connection failed", str(exc))
            else:
                self._set_message(f"Connection failed: {exc}")
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
        self._save_settings_path(LUT_SETTING_KEY, path)
        self.lut_path_edit.setText(path)
        self.load_selected_lut()

    def browse_wfc(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose WFC", "", "Bitmap files (*.bmp);;All files (*.*)"
        )
        if not path:
            return
        self.selected_wfc_path = path
        self._save_settings_path(WFC_SETTING_KEY, path)
        self.wfc_path_edit.setText(path)
        self.load_selected_wfc()

    def load_selected_lut(self) -> None:
        if not self.backend.status().connected:
            self._refresh_status()
            self._set_message("LUT selected; it will load on the next connection.")
            return
        try:
            self.backend.load_lut(self.selected_lut_path)
        except Exception as exc:
            self._show_error("LUT load failed", str(exc))
        self._refresh_status()

    def use_default_lut(self) -> None:
        self.selected_lut_path = None
        self._save_settings_path(LUT_SETTING_KEY, None)
        self.lut_path_edit.clear()
        pending_message = False
        try:
            if self.backend.status().connected:
                self.backend.load_lut(None)
            else:
                pending_message = True
        except Exception as exc:
            self._show_error("Default LUT load failed", str(exc))
        self._refresh_status()
        if pending_message:
            self._set_message("Default LUT selected; it will load on the next connection.")

    def load_selected_wfc(self) -> None:
        if not self.backend.status().connected:
            self._refresh_status()
            self._set_message("WFC selected; it will load on the next connection.")
            return
        try:
            self.backend.load_wfc(self.selected_wfc_path)
        except Exception as exc:
            self._show_error("WFC load failed", str(exc))
        self._refresh_status()

    def use_default_wfc(self) -> None:
        self.selected_wfc_path = None
        self._save_settings_path(WFC_SETTING_KEY, None)
        self.wfc_path_edit.clear()
        pending_message = False
        try:
            if self.backend.status().connected:
                self.backend.load_wfc(None)
            else:
                pending_message = True
        except Exception as exc:
            self._show_error("Default WFC load failed", str(exc))
        self._refresh_status()
        if pending_message:
            self._set_message("Default WFC selected; it will load on the next connection.")

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

    def open_target_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open target image", "", "Image files (*.*)"
        )
        if not path:
            return
        try:
            self.file_target = load_target_image(path)
        except ImageValidationError as exc:
            self._show_error("Invalid target image", str(exc))
            return
        self.file_target_name = Path(path).name
        self.file_target_label.setText(str(Path(path)))
        if self.target_source_combo.currentText() == "from file":
            self._set_target_from_file(schedule_generation=True)
        else:
            self.target_source_combo.setCurrentText("from file")
        self._set_message("Loaded target image")

    def open_custom_input_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open input beam image", "", "Image files (*.*)"
        )
        if not path:
            return
        try:
            amplitude = load_input_beam_image(path)
        except ImageValidationError as exc:
            self._show_error("Invalid input beam image", str(exc))
            return
        self.custom_input_amplitude = amplitude
        self.custom_input_name = Path(path).name
        self.custom_input_label.setText(str(Path(path)))
        self._set_message("Loaded custom input beam; press Apply or Generate Mask")

    def _target_source_changed(self) -> None:
        self.target_stack.setCurrentIndex(self.target_source_combo.currentIndex())
        if self.target_source_combo.currentText() == "TEM/HG":
            self._set_target_from_hg(schedule_generation=True)
            return
        self._set_target_from_file(schedule_generation=True)

    def _target_controls_changed(self) -> None:
        self._update_target_from_controls()
        if self.current_target is not None:
            self._clear_generated_phase()
            self._schedule_generation()

    def _offset_controls_changed(self) -> None:
        if self.worker_thread is not None:
            self.pending_regeneration = True
            self._set_message("Generation running; queued latest settings")
            return
        if self.base_phase16 is not None:
            self._apply_final_phase(auto_send=True)
            return
        if self.current_target is not None:
            self._schedule_generation()

    def _hg_controls_changed(self) -> None:
        if self.target_source_combo.currentText() != "TEM/HG":
            return
        self._set_target_from_hg(schedule_generation=True)

    def _set_target_from_hg(self, schedule_generation: bool) -> None:
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
        self._clear_generated_phase()
        if schedule_generation:
            self._schedule_generation()

    def _set_target_from_file(self, schedule_generation: bool) -> None:
        if self.file_target is None:
            self.original_target = None
            self.current_target = None
            self.target_preview.reset_text("Target preview")
            self._clear_generated_phase()
            self._set_message("Load an image target")
            return
        self.original_target = self.file_target
        self._update_target_from_controls()
        self._clear_generated_phase()
        if schedule_generation:
            self._schedule_generation()

    def _schedule_generation(self) -> None:
        if self.worker_thread is not None:
            self.pending_regeneration = True
            self._set_message("Generation running; queued latest settings")
            return
        self.regen_timer.start()

    def _clear_generated_phase(self) -> None:
        self.base_phase16 = None
        self.final_phase16 = None
        self.current_phase16 = None
        self.send_ready = None
        self.phase_preview.reset_text("Generated phase mask")

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
        self._set_target_from_hg(schedule_generation=True)

    def generate_mask(self) -> None:
        if self.current_target is None:
            self._show_error("No target", "Choose TEM/HG or load an image target first.")
            return
        input_profile = self._current_input_profile()
        if input_profile == "custom" and self.custom_input_amplitude is None:
            self._show_error(
                "No input beam", "Load a custom input beam image first."
            )
            return
        if self.worker_thread is not None:
            self.pending_regeneration = True
            self._set_message("Generation running; queued latest settings")
            return

        request = GenerationRequest(
            target=self.current_target.copy(),
            algorithm=self.algorithm_combo.currentText(),
            iterations=self.iterations_spin.value(),
            seed=self.seed_spin.value(),
            input_profile=input_profile,
            gaussian_waist_px=self.gaussian_waist_spin.value(),
            custom_input_amplitude=(
                self.custom_input_amplitude.copy()
                if input_profile == "custom"
                and self.custom_input_amplitude is not None
                else None
            ),
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
        self.base_phase16 = np.asarray(phase16, dtype=np.uint16)
        self._apply_final_phase(auto_send=not self.pending_regeneration)
        self._set_message("Generated phase mask")

    def _apply_final_phase(self, auto_send: bool) -> None:
        if self.base_phase16 is None:
            return
        self.final_phase16 = apply_phase_offset_wraps(
            self.base_phase16,
            offset_x_wraps=self.offset_x_spin.value(),
            offset_y_wraps=self.offset_y_spin.value(),
        )
        self.current_phase16 = self.final_phase16
        self.send_ready = uint16_to_calibrated_input_uint8(self.final_phase16)
        self.phase_preview.set_gray(uint16_to_preview_uint8(self.final_phase16))
        if auto_send:
            self._auto_send_generated_mask()

    def _auto_send_generated_mask(self) -> None:
        if self.send_ready is None or not self.backend.status().connected:
            return
        try:
            self.backend.send(self.send_ready)
        except Exception as exc:
            self._show_error("Auto-send failed", str(exc))
        self._refresh_status()

    def _generation_failed(self, message: str) -> None:
        self._show_error("Generation failed", message)

    def _generation_thread_finished(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
        if self.worker_thread is not None:
            self.worker_thread.deleteLater()
        self.worker = None
        self.worker_thread = None
        if self.pending_regeneration:
            self.pending_regeneration = False
            self.generate_mask()

    def _current_mask_configuration(self) -> MaskConfiguration:
        target_image = None
        if self.file_target is not None:
            target_image = EmbeddedGrayImage(
                name=self.file_target_name or "target.png",
                pixels=self.file_target.copy(),
            )

        custom_beam_image = None
        if self.custom_input_amplitude is not None:
            custom_beam_image = EmbeddedGrayImage(
                name=self.custom_input_name or "input_beam.png",
                pixels=np.uint8(
                    np.rint(np.clip(self.custom_input_amplitude, 0.0, 1.0) * 255)
                ),
            )

        return MaskConfiguration(
            target_source=(
                "tem_hg"
                if self.target_source_combo.currentText() == "TEM/HG"
                else "file"
            ),
            hg_n=self.hg_n_spin.value(),
            hg_m=self.hg_m_spin.value(),
            hg_waist=self.hg_waist_spin.value(),
            hg_normalize=self.hg_norm_combo.currentText(),
            hg_rotation=self.hg_rotation_spin.value(),
            target_image=target_image,
            algorithm=self.algorithm_combo.currentText(),
            iterations=self.iterations_spin.value(),
            seed=self.seed_spin.value(),
            input_profile=self._current_input_profile(),
            gaussian_waist_px=self.gaussian_waist_spin.value(),
            custom_beam_image=custom_beam_image,
            invert_target=self.invert_check.isChecked(),
            flip_horizontal=self.flip_x_check.isChecked(),
            flip_vertical=self.flip_y_check.isChecked(),
            offset_x_wraps=self.offset_x_spin.value(),
            offset_y_wraps=self.offset_y_spin.value(),
        )

    def save_generation_config(self) -> None:
        try:
            self.config_directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._show_error("Configuration folder unavailable", str(exc))
            return
        suggested_path = self.config_directory / f"mask_config{CONFIG_EXTENSION}"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save mask configuration",
            str(suggested_path),
            f"SLM configuration (*{CONFIG_EXTENSION})",
        )
        if not path:
            return
        try:
            saved_path = save_mask_configuration(
                self._current_mask_configuration(), path
            )
        except (MaskConfigError, OSError) as exc:
            self._show_error("Save configuration failed", str(exc))
            return
        self._set_message(f"Saved configuration {saved_path}")

    def load_generation_config(self) -> None:
        try:
            self.config_directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._show_error("Configuration folder unavailable", str(exc))
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load mask configuration",
            str(self.config_directory),
            f"SLM configuration (*{CONFIG_EXTENSION})",
        )
        if not path:
            return
        try:
            config = load_mask_configuration(path)
        except MaskConfigError as exc:
            self._show_error("Invalid configuration", str(exc))
            return

        self._apply_mask_configuration(config)
        if self.worker_thread is None:
            self._set_message(f"Loaded configuration {path}")

    def _apply_mask_configuration(self, config: MaskConfiguration) -> None:
        controls = (
            self.target_source_combo,
            self.hg_n_spin,
            self.hg_m_spin,
            self.hg_waist_spin,
            self.hg_norm_combo,
            self.hg_rotation_spin,
            self.algorithm_combo,
            self.iterations_spin,
            self.seed_spin,
            self.input_profile_combo,
            self.gaussian_waist_spin,
            self.invert_check,
            self.flip_x_check,
            self.flip_y_check,
            self.offset_x_spin,
            self.offset_y_spin,
        )
        blockers = [QSignalBlocker(control) for control in controls]
        try:
            self.target_source_combo.setCurrentText(
                "TEM/HG" if config.target_source == "tem_hg" else "from file"
            )
            self.hg_n_spin.setValue(config.hg_n)
            self.hg_m_spin.setValue(config.hg_m)
            self.hg_waist_spin.setValue(config.hg_waist)
            self.hg_norm_combo.setCurrentText(config.hg_normalize)
            self.hg_rotation_spin.setValue(config.hg_rotation)
            self.algorithm_combo.setCurrentText(config.algorithm)
            self.iterations_spin.setValue(config.iterations)
            self.seed_spin.setValue(config.seed)
            profile_index = self.input_profile_combo.findData(config.input_profile)
            self.input_profile_combo.setCurrentIndex(profile_index)
            self.gaussian_waist_spin.setValue(config.gaussian_waist_px)
            self.invert_check.setChecked(config.invert_target)
            self.flip_x_check.setChecked(config.flip_horizontal)
            self.flip_y_check.setChecked(config.flip_vertical)
            self.offset_x_spin.setValue(config.offset_x_wraps)
            self.offset_y_spin.setValue(config.offset_y_wraps)
        finally:
            for blocker in blockers:
                blocker.unblock()

        if config.target_image is None:
            self.file_target = None
            self.file_target_name = None
            self.file_target_label.setText("No image loaded")
        else:
            self.file_target = config.target_image.pixels.copy()
            self.file_target_name = config.target_image.name
            self.file_target_label.setText(f"Embedded: {config.target_image.name}")

        if config.custom_beam_image is None:
            self.custom_input_amplitude = None
            self.custom_input_name = None
            self.custom_input_label.setText("No image loaded")
        else:
            self.custom_input_amplitude = (
                config.custom_beam_image.pixels.astype(np.float64) / 255.0
            )
            self.custom_input_name = config.custom_beam_image.name
            self.custom_input_label.setText(
                f"Embedded: {config.custom_beam_image.name}"
            )

        self.target_stack.setCurrentIndex(self.target_source_combo.currentIndex())
        self._sync_input_profile_controls()
        if config.input_profile in {"uniform", "gaussian"}:
            self.settings.setValue(INPUT_PROFILE_SETTING_KEY, config.input_profile)
        self.settings.setValue(
            GAUSSIAN_WAIST_SETTING_KEY, float(config.gaussian_waist_px)
        )
        self.settings.sync()

        if config.target_source == "tem_hg":
            self._set_target_from_hg(schedule_generation=False)
        else:
            self._set_target_from_file(schedule_generation=False)
        self._schedule_generation()

    def save_generated_bmp(self) -> None:
        if self.base_phase16 is None:
            self._show_error("Nothing to save", "Generate a phase mask first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Meadowlark BMP", "phase_mask.bmp", "BMP files (*.bmp)"
        )
        if not path:
            return
        try:
            save_meadowlark_bmp(self.base_phase16, path)
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
