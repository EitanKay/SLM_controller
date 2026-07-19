import sys
import types

import numpy as np
import pytest

from src.slm_gui.holography import (
    DEFAULT_GAUSSIAN_WAIST_PX,
    generate_hg_target_uint8,
    generate_input_amplitude,
    generate_phase_uint16,
    gerchberg_saxton,
)


def _legacy_uniform_gs(target, iterations, seed):
    arr = np.asarray(target, dtype=np.float64)
    arr /= arr.max() if arr.max() > 0 else 1.0
    target_amp = np.sqrt(arr)
    rng = np.random.default_rng(seed)
    field_slm = np.exp(
        1j * rng.uniform(0, 2 * np.pi, size=target_amp.shape)
    )

    for _ in range(iterations):
        field_fourier = np.fft.fftshift(np.fft.fft2(field_slm))
        field_fourier = target_amp * np.exp(1j * np.angle(field_fourier))
        field_slm = np.fft.ifft2(np.fft.ifftshift(field_fourier))
        field_slm = np.exp(1j * np.angle(field_slm))

    return np.mod(np.angle(field_slm), 2 * np.pi)


def test_uniform_input_amplitude_is_one_everywhere():
    amplitude = generate_input_amplitude("uniform")

    assert amplitude.shape == (512, 512)
    assert amplitude.dtype == np.float64
    np.testing.assert_array_equal(amplitude, np.ones((512, 512)))


def test_gaussian_input_amplitude_is_centered_symmetric_and_uses_beam_waist():
    waist = 100.0
    amplitude = generate_input_amplitude("gaussian", gaussian_waist_px=waist)

    assert amplitude.shape == (512, 512)
    assert amplitude.max() == pytest.approx(1.0)
    np.testing.assert_allclose(amplitude, np.flipud(amplitude))
    np.testing.assert_allclose(amplitude, np.fliplr(amplitude))

    y, x = 255, 355
    center_radius_squared = 0.5
    sample_radius_squared = (x - 255.5) ** 2 + (y - 255.5) ** 2
    expected_amplitude = np.exp(
        -(sample_radius_squared - center_radius_squared) / waist**2
    )
    assert amplitude[y, x] == pytest.approx(expected_amplitude)


def test_custom_input_amplitude_is_validated_and_preserved():
    custom = np.linspace(0.1, 1.0, 512 * 512, dtype=np.float64).reshape(512, 512)

    amplitude = generate_input_amplitude(
        "custom", custom_input_amplitude=custom
    )

    np.testing.assert_array_equal(amplitude, custom)
    assert amplitude is not custom

    with pytest.raises(ValueError, match="Load a custom"):
        generate_input_amplitude("custom")
    with pytest.raises(ValueError, match="not identically zero"):
        generate_input_amplitude(
            "custom", custom_input_amplitude=np.zeros((512, 512))
        )
    with pytest.raises(ValueError, match="between 0 and 1"):
        generate_input_amplitude(
            "custom", custom_input_amplitude=np.full((512, 512), 2.0)
        )


@pytest.mark.parametrize(
    ("profile", "waist"),
    [
        ("not-a-profile", DEFAULT_GAUSSIAN_WAIST_PX),
        ("gaussian", 0),
        ("gaussian", 2049),
        ("gaussian", np.nan),
    ],
)
def test_invalid_input_profile_settings_raise_value_error(profile, waist):
    with pytest.raises(ValueError):
        generate_input_amplitude(profile, gaussian_waist_px=waist)


def test_gs_output_shape_dtype_and_range():
    target = np.zeros((512, 512), dtype=np.uint8)
    target[240:272, 240:272] = 255

    phase = generate_phase_uint16(target, algorithm="GS", iterations=1, seed=1)

    assert phase.shape == (512, 512)
    assert phase.dtype == np.uint16
    assert phase.min() >= 0
    assert phase.max() <= 65535


def test_default_uniform_gs_matches_legacy_implementation():
    target = np.zeros((512, 512), dtype=np.uint8)
    target[248:264, 248:264] = 255

    expected = _legacy_uniform_gs(target, iterations=2, seed=7)
    actual = gerchberg_saxton(target, iterations=2, seed=7)

    np.testing.assert_array_equal(actual, expected)


def test_gaussian_and_uniform_profiles_generate_different_gs_masks():
    target = np.zeros((512, 512), dtype=np.uint8)
    target[248:264, 248:264] = 255

    uniform = generate_phase_uint16(
        target, algorithm="GS", iterations=2, seed=7, input_profile="uniform"
    )
    gaussian = generate_phase_uint16(
        target,
        algorithm="GS",
        iterations=2,
        seed=7,
        input_profile="gaussian",
        gaussian_waist_px=100,
    )

    assert not np.array_equal(uniform, gaussian)


def test_custom_and_uniform_profiles_generate_different_gs_masks():
    target = np.zeros((512, 512), dtype=np.uint8)
    target[248:264, 248:264] = 255
    custom = np.ones((512, 512), dtype=np.float64)
    custom[:, :256] = 0.25

    uniform = generate_phase_uint16(
        target, algorithm="GS", iterations=2, seed=7, input_profile="uniform"
    )
    custom_phase = generate_phase_uint16(
        target,
        algorithm="GS",
        iterations=2,
        seed=7,
        input_profile="custom",
        custom_input_amplitude=custom,
    )

    assert not np.array_equal(uniform, custom_phase)


def test_wgs_output_shape_dtype_and_range():
    pytest.importorskip("slmsuite")
    target = np.zeros((512, 512), dtype=np.uint8)
    target[252:260, 252:260] = 255

    phase = generate_phase_uint16(target, algorithm="WGS-Kim", iterations=1, seed=1)

    assert phase.shape == (512, 512)
    assert phase.dtype == np.uint16
    assert phase.min() >= 0
    assert phase.max() <= 65535


@pytest.mark.parametrize(
    ("algorithm", "expected_method"),
    [
        ("WGS-Leonardo", "WGS-Leonardo"),
        ("WGS-Kim", "WGS-Kim"),
        ("WGS-Nogrette", "WGS-Nogrette"),
        ("WGS-Wu", "WGS-Wu"),
        ("WGS-tanh", "WGS-tanh"),
    ],
)
def test_wgs_variants_dispatch_to_slmsuite_methods(
    algorithm, expected_method, monkeypatch
):
    calls = []
    constructor_args = {}

    class FakeHologram:
        def __init__(self, target, amp, phase, slm_shape):
            constructor_args.update(
                target=target, amp=amp, phase=phase, slm_shape=slm_shape
            )

        def optimize(self, method, maxiter):
            calls.append((method, maxiter))

        def get_phase(self):
            return np.zeros((512, 512), dtype=np.float64)

    slmsuite = types.ModuleType("slmsuite")
    holography = types.ModuleType("slmsuite.holography")
    algorithms = types.ModuleType("slmsuite.holography.algorithms")
    algorithms.Hologram = FakeHologram
    monkeypatch.setitem(sys.modules, "slmsuite", slmsuite)
    monkeypatch.setitem(sys.modules, "slmsuite.holography", holography)
    monkeypatch.setitem(sys.modules, "slmsuite.holography.algorithms", algorithms)

    target = np.zeros((512, 512), dtype=np.uint8)
    target[252:260, 252:260] = 255

    custom_input = np.linspace(
        0.25, 1.0, 512 * 512, dtype=np.float64
    ).reshape(512, 512)
    phase = generate_phase_uint16(
        target,
        algorithm=algorithm,
        iterations=7,
        seed=1,
        input_profile="custom",
        custom_input_amplitude=custom_input,
    )

    assert phase.shape == (512, 512)
    assert phase.dtype == np.uint16
    assert calls == [(expected_method, 7)]
    np.testing.assert_array_equal(
        constructor_args["amp"],
        custom_input,
    )
    expected_phase = np.random.default_rng(1).uniform(
        0, 2 * np.pi, size=(512, 512)
    )
    np.testing.assert_array_equal(constructor_args["phase"], expected_phase)
    assert constructor_args["slm_shape"] == (512, 512)


def test_wgs_seed_is_reproducible_and_changes_initial_solution():
    pytest.importorskip("slmsuite")
    target = np.zeros((512, 512), dtype=np.uint8)
    target[252:260, 252:260] = 255

    first = generate_phase_uint16(
        target, algorithm="WGS-Leonardo", iterations=1, seed=11
    )
    repeated = generate_phase_uint16(
        target, algorithm="WGS-Leonardo", iterations=1, seed=11
    )
    different = generate_phase_uint16(
        target, algorithm="WGS-Leonardo", iterations=1, seed=12
    )

    np.testing.assert_array_equal(first, repeated)
    assert not np.array_equal(first, different)


def test_unsupported_algorithm_raises_value_error():
    target = np.zeros((512, 512), dtype=np.uint8)

    with pytest.raises(ValueError, match="Unsupported holography algorithm"):
        generate_phase_uint16(target, algorithm="WGS", iterations=1, seed=1)


def test_hg_target_shape_dtype_and_range():
    target = generate_hg_target_uint8(1, 1, waist=80, rotation_degrees=15)

    assert target.shape == (512, 512)
    assert target.dtype == np.uint8
    assert target.min() >= 0
    assert target.max() <= 255
