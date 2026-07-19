from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


SLM_SHAPE = (512, 512)
SLM_SIZE = (512, 512)
MAX16 = 65535


class ImageValidationError(ValueError):
    """Raised when an input image is not valid for the SLM GUI."""


def pack_meadowlark_dvi_16bit_to_rgb(value16_img: np.ndarray) -> np.ndarray:
    value16_img = np.asarray(value16_img, dtype=np.uint16)
    red_lsb = (value16_img & 0x00FF).astype(np.uint8)
    green_msb = ((value16_img >> 8) & 0x00FF).astype(np.uint8)
    blue = np.zeros_like(red_lsb, dtype=np.uint8)
    return np.dstack([red_lsb, green_msb, blue])


def unpack_meadowlark_dvi_rgb_to_16bit(rgb: np.ndarray) -> np.ndarray:
    rgb = np.asarray(rgb)
    if rgb.ndim != 3 or rgb.shape[2] < 3:
        raise ImageValidationError("Expected an RGB image.")
    red_lsb = rgb[..., 0].astype(np.uint16)
    green_msb = rgb[..., 1].astype(np.uint16)
    return (green_msb << 8) | red_lsb


def phase_radians_to_uint16(phase: np.ndarray) -> np.ndarray:
    phase = np.mod(np.asarray(phase, dtype=np.float64), 2 * np.pi)
    return np.uint16(np.round(phase * MAX16 / (2 * np.pi)))


def uint16_to_preview_uint8(value16_img: np.ndarray) -> np.ndarray:
    value16_img = np.asarray(value16_img, dtype=np.uint16)
    return np.uint8(np.round(value16_img.astype(np.float64) * 255 / MAX16))


def uint16_to_calibrated_input_uint8(value16_img: np.ndarray) -> np.ndarray:
    value16_img = np.asarray(value16_img, dtype=np.uint16)
    return np.ascontiguousarray(
        np.uint8(np.round(value16_img.astype(np.float64) * 255 / MAX16))
    )


def normalize_to_uint8(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float64)
    arr = arr - np.nanmin(arr)
    peak = np.nanmax(arr)
    if peak > 0:
        arr = arr / peak
    return np.uint8(np.round(np.clip(arr, 0, 1) * 255))


def load_strict_meadowlark_bmp(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    path = Path(path)
    if path.suffix.lower() != ".bmp":
        raise ImageValidationError("Direct control accepts .bmp files only.")

    with Image.open(path) as img:
        if img.size != SLM_SIZE:
            raise ImageValidationError(
                f"Expected 512x512 BMP, got {img.size[0]}x{img.size[1]}."
            )
        if img.mode != "RGB":
            raise ImageValidationError(
                f"Expected 24-bit RGB BMP, got image mode {img.mode!r}."
            )
        rgb = np.array(img, dtype=np.uint8)

    if np.any(rgb[..., 2] != 0):
        raise ImageValidationError(
            "Expected Meadowlark packed BMP with blue channel set to zero."
        )

    value16 = unpack_meadowlark_dvi_rgb_to_16bit(rgb)
    return value16, rgb


def load_target_png(path: str | Path) -> np.ndarray:
    path = Path(path)
    if path.suffix.lower() != ".png":
        raise ImageValidationError("Mask generation accepts .png files only.")

    with Image.open(path) as img:
        if img.size != SLM_SIZE:
            raise ImageValidationError(
                f"Expected 512x512 PNG, got {img.size[0]}x{img.size[1]}."
            )
        gray = img.convert("L")
        return np.array(gray, dtype=np.uint8)


def load_target_image(path: str | Path) -> np.ndarray:
    path = Path(path)
    try:
        with Image.open(path) as img:
            if img.size != SLM_SIZE:
                raise ImageValidationError(
                    f"Expected 512x512 image, got {img.size[0]}x{img.size[1]}."
                )
            gray = img.convert("L")
            return np.array(gray, dtype=np.uint8)
    except ImageValidationError:
        raise
    except Exception as exc:
        raise ImageValidationError(f"Could not open target image: {exc}") from exc


def load_input_beam_image(path: str | Path) -> np.ndarray:
    path = Path(path)
    try:
        with Image.open(path) as img:
            if img.size != SLM_SIZE:
                raise ImageValidationError(
                    f"Expected 512x512 image, got {img.size[0]}x{img.size[1]}."
                )
            gray = np.array(img.convert("L"), dtype=np.uint8)
    except ImageValidationError:
        raise
    except Exception as exc:
        raise ImageValidationError(f"Could not open input beam image: {exc}") from exc

    if gray.max() == 0:
        raise ImageValidationError("Input beam image cannot be entirely black.")
    return np.ascontiguousarray(gray, dtype=np.float64) / 255.0


def apply_discrete_transform(
    arr: np.ndarray,
    flip_x: bool = False,
    flip_y: bool = False,
    rotate_quarter_turns: int = 0,
) -> np.ndarray:
    out = np.asarray(arr)
    if flip_x:
        out = np.fliplr(out)
    if flip_y:
        out = np.flipud(out)
    turns = int(rotate_quarter_turns) % 4
    if turns:
        out = np.rot90(out, turns)
    return np.ascontiguousarray(out)


def apply_target_transform(
    arr: np.ndarray,
    invert: bool = False,
    flip_x: bool = False,
    flip_y: bool = False,
) -> np.ndarray:
    out = np.asarray(arr, dtype=np.uint8)
    if invert:
        out = 255 - out
    return apply_discrete_transform(out, flip_x=flip_x, flip_y=flip_y)


def apply_phase_offset_wraps(
    value16_img: np.ndarray,
    offset_x_wraps: float = 0.0,
    offset_y_wraps: float = 0.0,
) -> np.ndarray:
    value16_img = np.asarray(value16_img, dtype=np.uint16)
    height, width = value16_img.shape
    x_ramp = np.linspace(0.0, float(offset_x_wraps), width, endpoint=False)
    y_ramp = np.linspace(0.0, float(offset_y_wraps), height, endpoint=False)[:, None]
    ramp16 = np.rint((x_ramp + y_ramp) * (MAX16 + 1)).astype(np.int64)
    return np.mod(value16_img.astype(np.int64) + ramp16, MAX16 + 1).astype(np.uint16)


def rotate_float_image(arr: np.ndarray, angle_degrees: float) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float64)
    if abs(float(angle_degrees)) < 1e-9:
        return np.ascontiguousarray(arr)

    try:
        from scipy.ndimage import rotate
    except ImportError as exc:
        raise RuntimeError("SciPy is required for arbitrary-angle TEM rotation.") from exc

    rotated = rotate(
        arr,
        angle=float(angle_degrees),
        reshape=False,
        order=1,
        mode="constant",
        cval=0.0,
        prefilter=False,
    )
    return np.ascontiguousarray(rotated)


def save_meadowlark_bmp(value16_img: np.ndarray, path: str | Path) -> None:
    rgb = pack_meadowlark_dvi_16bit_to_rgb(value16_img)
    Image.fromarray(rgb, mode="RGB").save(path, format="BMP")
