from __future__ import annotations

import warnings

import numpy as np

from src.hermite_gaussian_generator import HermiteGaussianGenerator
from src.slm_gui.image_ops import (
    SLM_SHAPE,
    normalize_to_uint8,
    phase_radians_to_uint16,
    rotate_float_image,
)


DEFAULT_GAUSSIAN_WAIST_PX = 140.8
MIN_GAUSSIAN_WAIST_PX = 1.0
MAX_GAUSSIAN_WAIST_PX = 2048.0
INPUT_PROFILES = ("uniform", "gaussian", "custom")


def generate_input_amplitude(
    profile: str = "uniform",
    gaussian_waist_px: float = DEFAULT_GAUSSIAN_WAIST_PX,
    custom_input_amplitude: np.ndarray | None = None,
) -> np.ndarray:
    """Build the modeled SLM-plane field amplitude for hologram generation."""
    profile_key = str(profile).strip().lower()
    if profile_key not in INPUT_PROFILES:
        raise ValueError(
            f"Unsupported input profile: {profile!r}. "
            f"Choose one of {', '.join(INPUT_PROFILES)}."
        )

    if profile_key == "uniform":
        return np.ones(SLM_SHAPE, dtype=np.float64)

    if profile_key == "custom":
        if custom_input_amplitude is None:
            raise ValueError("Load a custom input beam image first.")
        amplitude = _validated_input_amplitude(custom_input_amplitude)
        if amplitude.max() > 1.0:
            raise ValueError("Custom input amplitude values must be between 0 and 1.")
        return amplitude.copy()

    try:
        waist = float(gaussian_waist_px)
    except (TypeError, ValueError) as exc:
        raise ValueError("Gaussian beam waist must be a number in pixels.") from exc
    if not np.isfinite(waist) or not (
        MIN_GAUSSIAN_WAIST_PX <= waist <= MAX_GAUSSIAN_WAIST_PX
    ):
        raise ValueError(
            "Gaussian beam waist must be between "
            f"{MIN_GAUSSIAN_WAIST_PX:g} and {MAX_GAUSSIAN_WAIST_PX:g} pixels."
        )

    ny, nx = SLM_SHAPE
    yy, xx = np.indices(SLM_SHAPE, dtype=np.float64)
    cx = (nx - 1) / 2
    cy = (ny - 1) / 2
    radius_squared = (xx - cx) ** 2 + (yy - cy) ** 2
    amplitude = np.exp(-radius_squared / waist**2)
    amplitude /= amplitude.max()
    return amplitude


def _validated_input_amplitude(input_amp: np.ndarray | None) -> np.ndarray:
    if input_amp is None:
        return generate_input_amplitude("uniform")

    amplitude = np.asarray(input_amp, dtype=np.float64)
    if amplitude.shape != SLM_SHAPE:
        raise ValueError(
            f"Expected input amplitude shape {SLM_SHAPE}, got {amplitude.shape}."
        )
    if not np.all(np.isfinite(amplitude)):
        raise ValueError("Input amplitude must contain only finite values.")
    if np.any(amplitude < 0) or amplitude.max() <= 0:
        raise ValueError("Input amplitude must be non-negative and not identically zero.")
    return amplitude


def _initial_phase(shape: tuple[int, int], seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.uniform(0, 2 * np.pi, size=shape)


def target_uint8_to_amplitude(target: np.ndarray) -> np.ndarray:
    arr = np.asarray(target, dtype=np.float64)
    if arr.shape != SLM_SHAPE:
        raise ValueError(f"Expected target shape {SLM_SHAPE}, got {arr.shape}.")
    arr /= arr.max() if arr.max() > 0 else 1.0
    return np.sqrt(arr)


def gerchberg_saxton(
    target: np.ndarray,
    iterations: int = 100,
    seed: int = 0,
    input_amp: np.ndarray | None = None,
) -> np.ndarray:
    target_amp = target_uint8_to_amplitude(target)
    input_amp = _validated_input_amplitude(input_amp)
    ny, nx = target_amp.shape
    phase = _initial_phase((ny, nx), seed)
    field_slm = input_amp * np.exp(1j * phase)

    for _ in range(int(iterations)):
        field_fourier = np.fft.fftshift(np.fft.fft2(field_slm))
        field_fourier = target_amp * np.exp(1j * np.angle(field_fourier))
        field_slm = np.fft.ifft2(np.fft.ifftshift(field_fourier))
        field_slm = input_amp * np.exp(1j * np.angle(field_slm))

    return np.mod(np.angle(field_slm), 2 * np.pi)


SLMSUITE_WGS_METHODS = {
    "WGS-LEONARDO": "WGS-Leonardo",
    "WGS-KIM": "WGS-Kim",
    "WGS-NOGRETTE": "WGS-Nogrette",
    "WGS-WU": "WGS-Wu",
    "WGS-TANH": "WGS-tanh",
}


class SlmsuiteUnavailableError(RuntimeError):
    pass


def weighted_gerchberg_saxton(
    target: np.ndarray,
    iterations: int = 30,
    seed: int = 0,
    input_amp: np.ndarray | None = None,
) -> np.ndarray:
    try:
        return weighted_gerchberg_saxton_slmsuite(
            target,
            iterations=iterations,
            method="WGS-Kim",
            seed=seed,
            input_amp=input_amp,
        )
    except SlmsuiteUnavailableError:
        return weighted_gerchberg_saxton_numpy(
            target, iterations=iterations, seed=seed, input_amp=input_amp
        )


def weighted_gerchberg_saxton_slmsuite(
    target: np.ndarray,
    iterations: int = 30,
    method: str = "WGS-Kim",
    seed: int = 0,
    input_amp: np.ndarray | None = None,
) -> np.ndarray:
    try:
        from slmsuite.holography.algorithms import Hologram
    except ImportError as exc:
        raise SlmsuiteUnavailableError(
            f"{method} requires slmsuite. Install slmsuite or choose GS."
        ) from exc

    target_amp = target_uint8_to_amplitude(target)
    input_amp = _validated_input_amplitude(input_amp)
    phase = _initial_phase(SLM_SHAPE, seed)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        hologram = Hologram(
            target=target_amp,
            amp=input_amp,
            phase=phase,
            slm_shape=SLM_SHAPE,
        )
        hologram.optimize(method=method, maxiter=int(iterations))
        phase = hologram.get_phase()
    return np.mod(np.asarray(phase, dtype=np.float64), 2 * np.pi)


def weighted_gerchberg_saxton_numpy(
    target: np.ndarray,
    iterations: int = 30,
    seed: int = 0,
    input_amp: np.ndarray | None = None,
) -> np.ndarray:
    """Small NumPy WGS fallback for environments where slmsuite cannot import."""
    target_amp = target_uint8_to_amplitude(target)
    input_amp = _validated_input_amplitude(input_amp)
    ny, nx = target_amp.shape
    phase = _initial_phase((ny, nx), seed)
    field_slm = input_amp * np.exp(1j * phase)
    weights = np.ones_like(target_amp)
    signal = target_amp > 0
    eps = 1e-12

    for _ in range(int(iterations)):
        field_fourier = np.fft.fftshift(np.fft.fft2(field_slm))
        current_amp = np.abs(field_fourier)
        if np.any(signal):
            current_norm = current_amp / (current_amp[signal].mean() + eps)
            target_norm = target_amp / (target_amp[signal].mean() + eps)
            weights[signal] *= target_norm[signal] / (current_norm[signal] + eps)
            weights = np.clip(weights, 0.05, 20.0)

        enforced_amp = target_amp * weights
        field_fourier = enforced_amp * np.exp(1j * np.angle(field_fourier))
        field_slm = np.fft.ifft2(np.fft.ifftshift(field_fourier))
        field_slm = input_amp * np.exp(1j * np.angle(field_slm))

    return np.mod(np.angle(field_slm), 2 * np.pi)


def generate_phase_uint16(
    target: np.ndarray,
    algorithm: str = "WGS-Leonardo",
    iterations: int = 30,
    seed: int = 0,
    input_profile: str = "uniform",
    gaussian_waist_px: float = DEFAULT_GAUSSIAN_WAIST_PX,
    custom_input_amplitude: np.ndarray | None = None,
) -> np.ndarray:
    input_amp = generate_input_amplitude(
        profile=input_profile,
        gaussian_waist_px=gaussian_waist_px,
        custom_input_amplitude=custom_input_amplitude,
    )
    algorithm = algorithm.upper()
    if algorithm == "GS":
        phase = gerchberg_saxton(
            target,
            iterations=iterations,
            seed=seed,
            input_amp=input_amp,
        )
    elif algorithm in SLMSUITE_WGS_METHODS:
        method = SLMSUITE_WGS_METHODS[algorithm]
        try:
            phase = weighted_gerchberg_saxton_slmsuite(
                target,
                iterations=iterations,
                method=method,
                seed=seed,
                input_amp=input_amp,
            )
        except SlmsuiteUnavailableError:
            if method != "WGS-Kim":
                raise
            phase = weighted_gerchberg_saxton_numpy(
                target,
                iterations=iterations,
                seed=seed,
                input_amp=input_amp,
            )
    else:
        raise ValueError(f"Unsupported holography algorithm: {algorithm}")
    return phase_radians_to_uint16(phase)


def generate_hg_target_uint8(
    n: int,
    m: int,
    waist: float,
    normalize: str = "peak",
    rotation_degrees: float = 0.0,
) -> np.ndarray:
    generator = HermiteGaussianGenerator(shape=SLM_SHAPE)
    intensity = generator.intensity(
        int(n), int(m), float(waist), normalize=None if normalize == "none" else normalize
    )
    rotated = rotate_float_image(intensity, rotation_degrees)
    return normalize_to_uint8(rotated)
