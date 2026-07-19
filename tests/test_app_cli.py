import argparse
import sys

from src.slm_gui import app as gui_app
from src.slm_gui.app import configure_windows_dpi_awareness, ensure_standard_streams, parse_args


def test_default_cli_uses_hardware_backend():
    args = parse_args([])

    assert args.sim is False


def test_sim_cli_flag_selects_simulator_backend():
    args = parse_args(["--sim"])

    assert args.sim is True


def test_ensure_standard_streams_recovers_from_windowed_none_streams(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    ensure_standard_streams()

    assert sys.stdout is not None
    assert sys.stderr is not None
    assert hasattr(sys.stdout, "write")
    assert hasattr(sys.stderr, "write")


def test_dpi_configuration_is_a_noop_off_windows(monkeypatch):
    monkeypatch.setattr(gui_app.sys, "platform", "linux")

    configure_windows_dpi_awareness()


def test_main_configures_dpi_before_creating_qapplication(monkeypatch):
    events = []

    class FakeApplication:
        def __init__(self, _argv):
            events.append("qapplication")

        def exec(self):
            return 0

    class FakeWindow:
        def __init__(self, **_kwargs):
            events.append("window")

        def resize(self, *_args):
            return None

        def show(self):
            return None

    monkeypatch.setattr(gui_app, "ensure_standard_streams", lambda: None)
    monkeypatch.setattr(
        gui_app, "parse_args", lambda _argv: argparse.Namespace(sim=True)
    )
    monkeypatch.setattr(
        gui_app, "configure_windows_dpi_awareness", lambda: events.append("dpi")
    )
    monkeypatch.setattr(gui_app, "QApplication", FakeApplication)
    monkeypatch.setattr(gui_app, "apply_style", lambda _app: None)
    monkeypatch.setattr(gui_app, "MainWindow", FakeWindow)

    assert gui_app.main(["--sim"]) == 0
    assert events == ["dpi", "qapplication", "window"]
