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


def target_uint8_to_amplitude(target: np.ndarray) -> np.ndarray:
    arr = np.asarray(target, dtype=np.float64)
    if arr.shape != SLM_SHAPE:
        raise ValueError(f"Expected target shape {SLM_SHAPE}, got {arr.shape}.")
    arr /= arr.max() if arr.max() > 0 else 1.0
    return np.sqrt(arr)


def gerchberg_saxton(
    target: np.ndarray, iterations: int = 100, seed: int = 0
) -> np.ndarray:
    target_amp = target_uint8_to_amplitude(target)
    rng = np.random.default_rng(seed)
    ny, nx = target_amp.shape
    field_slm = np.exp(1j * rng.uniform(0, 2 * np.pi, size=(ny, nx)))

    for _ in range(int(iterations)):
        field_fourier = np.fft.fftshift(np.fft.fft2(field_slm))
        field_fourier = target_amp * np.exp(1j * np.angle(field_fourier))
        field_slm = np.fft.ifft2(np.fft.ifftshift(field_fourier))
        field_slm = np.exp(1j * np.angle(field_slm))

    return np.mod(np.angle(field_slm), 2 * np.pi)


def weighted_gerchberg_saxton(
    target: np.ndarray, iterations: int = 30, seed: int = 0
) -> np.ndarray:
    try:
        from slmsuite.holography.algorithms import Hologram
    except Exception:
        return weighted_gerchberg_saxton_numpy(target, iterations=iterations, seed=seed)

    target_amp = target_uint8_to_amplitude(target)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        hologram = Hologram(target=target_amp, slm_shape=SLM_SHAPE)
        hologram.optimize(method="WGS-Kim", maxiter=int(iterations))
        phase = hologram.get_phase()
    return np.mod(np.asarray(phase, dtype=np.float64), 2 * np.pi)


def weighted_gerchberg_saxton_numpy(
    target: np.ndarray, iterations: int = 30, seed: int = 0
) -> np.ndarray:
    """Small NumPy WGS fallback for environments where slmsuite cannot import."""
    target_amp = target_uint8_to_amplitude(target)
    rng = np.random.default_rng(seed)
    ny, nx = target_amp.shape
    field_slm = np.exp(1j * rng.uniform(0, 2 * np.pi, size=(ny, nx)))
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
        field_slm = np.exp(1j * np.angle(field_slm))

    return np.mod(np.angle(field_slm), 2 * np.pi)


def generate_phase_uint16(
    target: np.ndarray,
    algorithm: str = "WGS",
    iterations: int = 30,
    seed: int = 0,
) -> np.ndarray:
    algorithm = algorithm.upper()
    if algorithm == "GS":
        phase = gerchberg_saxton(target, iterations=iterations, seed=seed)
    elif algorithm == "WGS":
        phase = weighted_gerchberg_saxton(target, iterations=iterations, seed=seed)
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
