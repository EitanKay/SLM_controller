import sys

from src.slm_gui.app import ensure_standard_streams, parse_args


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
