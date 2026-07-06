from __future__ import annotations

import argparse
import sys

from PyQt6.QtWidgets import QApplication

from src.slm_gui.main_window import MainWindow


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
        QFrame#TopBar, QGroupBox {
            background: #ffffff;
            border: 1px solid #d7dce2;
            border-radius: 8px;
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
    args = parse_args(argv)
    qt_argv = [sys.argv[0]] if argv is not None else sys.argv
    app = QApplication(qt_argv)
    apply_style(app)
    window = MainWindow(backend_mode="sim" if args.sim else "hardware")
    window.resize(1180, 780)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
