from __future__ import annotations

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


def main() -> int:
    app = QApplication(sys.argv)
    apply_style(app)
    window = MainWindow()
    window.resize(1180, 780)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

