from src.slm_gui.app import parse_args


def test_default_cli_uses_hardware_backend():
    args = parse_args([])

    assert args.sim is False


def test_sim_cli_flag_selects_simulator_backend():
    args = parse_args(["--sim"])

    assert args.sim is True
