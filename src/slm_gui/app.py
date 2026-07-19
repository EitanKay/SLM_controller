from __future__ import annotations

import argparse
import ctypes
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.slm_gui.main_window import MainWindow


class _NullTextStream:
    def write(self, _text: str) -> int:
        return 0

    def flush(self) -> None:
        return None


_LOG_HANDLE = None


def configure_windows_dpi_awareness() -> None:
    """Set process DPI awareness before Qt or the Blink SDK creates a window."""
    if sys.platform != "win32":
        return

    try:
        # Windows 10+: per-monitor-v2 handles mixed-DPI monitor arrangements best.
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except (AttributeError, OSError):
        pass

    try:
        # Windows 8.1+: PROCESS_PER_MONITOR_DPI_AWARE.
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:
            return
    except (AttributeError, OSError):
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def ensure_standard_streams() -> None:
    global _LOG_HANDLE
    if sys.stdout is not None and sys.stderr is not None:
        return

    try:
        log_dir = Path.home() / "AppData" / "Local" / "SLMControl"
        log_dir.mkdir(parents=True, exist_ok=True)
        _LOG_HANDLE = open(log_dir / "SLMControl.log", "a", encoding="utf-8", buffering=1)
        stream = _LOG_HANDLE
    except Exception:
        stream = _NullTextStream()

    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


def apply_style(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(
        """
        QWidget {
            background: #f6f7f9;
            color: #18202a;
            font-family: Segoe UI, Arial, sans-serif;
            font-size: 10pt;
        }
        QMainWindow, QTabWidget::pane {
            background: #f6f7f9;
        }
        QFrame#TopBar, QFrame#CollapsibleSection, QGroupBox {
            background: #ffffff;
            border: 1px solid #d7dce2;
            border-radius: 8px;
        }
        QToolButton#CollapsibleHeader {
            background: transparent;
            border: none;
            border-radius: 8px;
            padding: 10px 12px;
            font-weight: 600;
            text-align: left;
        }
        QToolButton#CollapsibleHeader:hover {
            background: #eef4ff;
        }
        QGroupBox {
            margin-top: 14px;
            padding: 12px;
            font-weight: 600;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
        QPushButton {
            background: #ffffff;
            border: 1px solid #cbd3dc;
            border-radius: 6px;
            padding: 7px 11px;
            min-height: 22px;
        }
        QPushButton:hover {
            background: #eef4ff;
            border-color: #8cb4ff;
        }
        QPushButton:pressed {
            background: #dce9ff;
        }
        QPushButton#PrimaryButton {
            background: #1d4ed8;
            border-color: #1d4ed8;
            color: #ffffff;
            font-weight: 600;
        }
        QPushButton#PrimaryButton:hover {
            background: #2563eb;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background: #ffffff;
            border: 1px solid #cbd3dc;
            border-radius: 6px;
            padding: 5px 7px;
            min-height: 22px;
        }
        QLabel#Preview {
            background: #101820;
            border: 1px solid #2e3b4a;
            border-radius: 8px;
        }
        QLabel#StatusPill {
            background: #e8edf4;
            border-radius: 10px;
            padding: 4px 9px;
            font-weight: 600;
        }
        """
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SLM Control GUI")
    parser.add_argument(
        "--sim",
        action="store_true",
        help="use the simulator backend instead of hardware",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ensure_standard_streams()
    args = parse_args(argv)
    qt_argv = [sys.argv[0]] if argv is not None else sys.argv
    configure_windows_dpi_awareness()
    app = QApplication(qt_argv)
    apply_style(app)
    window = MainWindow(backend_mode="sim" if args.sim else "hardware")
    window.resize(1180, 780)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
