from __future__ import annotations

import base64
import binascii
import io
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from src.slm_gui.holography import (
    MAX_GAUSSIAN_WAIST_PX,
    MIN_GAUSSIAN_WAIST_PX,
)
from src.slm_gui.image_ops import SLM_SHAPE


CONFIG_EXTENSION = ".slmconfig"
CONFIG_FORMAT = "SLMControl mask configuration"
CONFIG_VERSION = 1
SUPPORTED_ALGORITHMS = (
    "GS",
    "WGS-Leonardo",
    "WGS-Kim",
    "WGS-Nogrette",
    "WGS-Wu",
    "WGS-tanh",
)
TARGET_SOURCES = ("tem_hg", "file")
INPUT_PROFILES = ("uniform", "gaussian", "custom")
HG_NORMALIZATIONS = ("peak", "power", "none")


class MaskConfigError(ValueError):
    """Raised when a mask configuration cannot be read or validated."""


@dataclass(frozen=True)
class EmbeddedGrayImage:
    name: str
    pixels: np.ndarray


@dataclass(frozen=True)
class MaskConfiguration:
    target_source: str
    hg_n: int
    hg_m: int
    hg_waist: float
    hg_normalize: str
    hg_rotation: float
    target_image: EmbeddedGrayImage | None
    algorithm: str
    iterations: int
    seed: int
    input_profile: str
    gaussian_waist_px: float
    custom_beam_image: EmbeddedGrayImage | None
    invert_target: bool
    flip_horizontal: bool
    flip_vertical: bool
    offset_x_wraps: float
    offset_y_wraps: float


def default_config_directory(*, create: bool = True) -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    directory = base / "SLMControl" / "configs"
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_config_extension(path: str | Path) -> Path:
    config_path = Path(path)
    if config_path.suffix.lower() != CONFIG_EXTENSION:
        config_path = Path(f"{config_path}{CONFIG_EXTENSION}")
    return config_path


def _validated_gray_image(
    image: EmbeddedGrayImage | None,
    field_name: str,
    *,
    reject_black: bool = False,
) -> EmbeddedGrayImage | None:
    if image is None:
        return None
    if not isinstance(image, EmbeddedGrayImage):
        raise MaskConfigError(f"{field_name} must be an embedded image or null.")

    pixels = np.asarray(image.pixels)
    if pixels.shape != SLM_SHAPE:
        raise MaskConfigError(
            f"{field_name} must be 512x512, got {pixels.shape}."
        )
    if not np.issubdtype(pixels.dtype, np.number):
        raise MaskConfigError(f"{field_name} must contain numeric grayscale values.")
    pixels_float = np.asarray(pixels, dtype=np.float64)
    if not np.all(np.isfinite(pixels_float)) or np.any(pixels_float < 0) or np.any(
        pixels_float > 255
    ):
        raise MaskConfigError(f"{field_name} grayscale values must be between 0 and 255.")
    pixels_uint8 = np.ascontiguousarray(np.rint(pixels_float), dtype=np.uint8)
    if reject_black and pixels_uint8.max() == 0:
        raise MaskConfigError(f"{field_name} cannot be entirely black.")

    name = Path(str(image.name or "image.png")).name or "image.png"
    return EmbeddedGrayImage(name=name, pixels=pixels_uint8)


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MaskConfigError(f"{field_name} must be a JSON object.")
    return value


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise MaskConfigError(f"{field_name} must be true or false.")
    return value


def _require_int(value: Any, field_name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MaskConfigError(f"{field_name} must be an integer.")
    if not minimum <= value <= maximum:
        raise MaskConfigError(
            f"{field_name} must be between {minimum} and {maximum}."
        )
    return value


def _require_float(
    value: Any, field_name: str, minimum: float, maximum: float
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MaskConfigError(f"{field_name} must be a number.")
    numeric = float(value)
    if not np.isfinite(numeric) or not minimum <= numeric <= maximum:
        raise MaskConfigError(
            f"{field_name} must be between {minimum:g} and {maximum:g}."
        )
    return numeric


def _require_choice(value: Any, field_name: str, choices: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in choices:
        raise MaskConfigError(
            f"{field_name} must be one of {', '.join(choices)}."
        )
    return value


def _encode_image(image: EmbeddedGrayImage | None) -> dict[str, str] | None:
    if image is None:
        return None
    buffer = io.BytesIO()
    Image.fromarray(image.pixels).save(buffer, format="PNG")
    return {
        "name": image.name,
        "encoding": "base64-png",
        "data": base64.b64encode(buffer.getvalue()).decode("ascii"),
    }


def _decode_image(
    value: Any, field_name: str, *, reject_black: bool = False
) -> EmbeddedGrayImage | None:
    if value is None:
        return None
    image_data = _require_mapping(value, field_name)
    if image_data.get("encoding") != "base64-png":
        raise MaskConfigError(f"{field_name} uses an unsupported encoding.")
    name = image_data.get("name")
    encoded = image_data.get("data")
    if not isinstance(name, str) or not name.strip():
        raise MaskConfigError(f"{field_name}.name must be a non-empty string.")
    if not isinstance(encoded, str):
        raise MaskConfigError(f"{field_name}.data must be base64 text.")

    try:
        raw = base64.b64decode(encoded, validate=True)
        with Image.open(io.BytesIO(raw)) as source:
            if source.size != (SLM_SHAPE[1], SLM_SHAPE[0]):
                raise MaskConfigError(
                    f"{field_name} must be 512x512, got "
                    f"{source.size[0]}x{source.size[1]}."
                )
            pixels = np.array(source.convert("L"), dtype=np.uint8)
    except MaskConfigError:
        raise
    except (binascii.Error, OSError, ValueError) as exc:
        raise MaskConfigError(f"{field_name} does not contain a valid PNG image.") from exc

    return _validated_gray_image(
        EmbeddedGrayImage(name=name, pixels=pixels),
        field_name,
        reject_black=reject_black,
    )


def validate_mask_configuration(config: MaskConfiguration) -> MaskConfiguration:
    target_source = _require_choice(
        config.target_source, "target.source", TARGET_SOURCES
    )
    input_profile = _require_choice(
        config.input_profile, "algorithm.input_beam.profile", INPUT_PROFILES
    )
    target_image = _validated_gray_image(config.target_image, "target.file_image")
    custom_beam_image = _validated_gray_image(
        config.custom_beam_image,
        "algorithm.input_beam.custom_image",
        reject_black=True,
    )
    if target_source == "file" and target_image is None:
        raise MaskConfigError("A file target configuration must include its target image.")
    if input_profile == "custom" and custom_beam_image is None:
        raise MaskConfigError("A custom input beam configuration must include its image.")

    return MaskConfiguration(
        target_source=target_source,
        hg_n=_require_int(config.hg_n, "target.hg.n", 0, 20),
        hg_m=_require_int(config.hg_m, "target.hg.m", 0, 20),
        hg_waist=_require_float(config.hg_waist, "target.hg.waist", 1.0, 512.0),
        hg_normalize=_require_choice(
            config.hg_normalize, "target.hg.normalize", HG_NORMALIZATIONS
        ),
        hg_rotation=_require_float(
            config.hg_rotation, "target.hg.rotation", -180.0, 180.0
        ),
        target_image=target_image,
        algorithm=_require_choice(
            config.algorithm, "algorithm.name", SUPPORTED_ALGORITHMS
        ),
        iterations=_require_int(config.iterations, "algorithm.iterations", 1, 500),
        seed=_require_int(config.seed, "algorithm.seed", 0, 999999),
        input_profile=input_profile,
        gaussian_waist_px=_require_float(
            config.gaussian_waist_px,
            "algorithm.input_beam.gaussian_waist_px",
            MIN_GAUSSIAN_WAIST_PX,
            MAX_GAUSSIAN_WAIST_PX,
        ),
        custom_beam_image=custom_beam_image,
        invert_target=_require_bool(config.invert_target, "control.invert_target"),
        flip_horizontal=_require_bool(
            config.flip_horizontal, "control.flip_horizontal"
        ),
        flip_vertical=_require_bool(config.flip_vertical, "control.flip_vertical"),
        offset_x_wraps=_require_float(
            config.offset_x_wraps, "control.offset_x_wraps", -500.0, 500.0
        ),
        offset_y_wraps=_require_float(
            config.offset_y_wraps, "control.offset_y_wraps", -500.0, 500.0
        ),
    )


def mask_configuration_to_dict(config: MaskConfiguration) -> dict[str, Any]:
    config = validate_mask_configuration(config)
    return {
        "format": CONFIG_FORMAT,
        "version": CONFIG_VERSION,
        "target": {
            "source": config.target_source,
            "hg": {
                "n": config.hg_n,
                "m": config.hg_m,
                "waist": config.hg_waist,
                "normalize": config.hg_normalize,
                "rotation": config.hg_rotation,
            },
            "file_image": _encode_image(config.target_image),
        },
        "algorithm": {
            "name": config.algorithm,
            "iterations": config.iterations,
            "seed": config.seed,
            "input_beam": {
                "profile": config.input_profile,
                "gaussian_waist_px": config.gaussian_waist_px,
                "custom_image": _encode_image(config.custom_beam_image),
            },
        },
        "control": {
            "invert_target": config.invert_target,
            "flip_horizontal": config.flip_horizontal,
            "flip_vertical": config.flip_vertical,
            "offset_x_wraps": config.offset_x_wraps,
            "offset_y_wraps": config.offset_y_wraps,
        },
    }


def mask_configuration_from_dict(document: Any) -> MaskConfiguration:
    root = _require_mapping(document, "configuration")
    if root.get("format") != CONFIG_FORMAT:
        raise MaskConfigError("This is not an SLMControl mask configuration file.")
    version = root.get("version")
    if version != CONFIG_VERSION:
        raise MaskConfigError(
            f"Unsupported mask configuration version {version!r}; "
            f"expected version {CONFIG_VERSION}."
        )

    target = _require_mapping(root.get("target"), "target")
    hg = _require_mapping(target.get("hg"), "target.hg")
    algorithm = _require_mapping(root.get("algorithm"), "algorithm")
    input_beam = _require_mapping(
        algorithm.get("input_beam"), "algorithm.input_beam"
    )
    control = _require_mapping(root.get("control"), "control")

    try:
        config = MaskConfiguration(
            target_source=target["source"],
            hg_n=hg["n"],
            hg_m=hg["m"],
            hg_waist=hg["waist"],
            hg_normalize=hg["normalize"],
            hg_rotation=hg["rotation"],
            target_image=_decode_image(target.get("file_image"), "target.file_image"),
            algorithm=algorithm["name"],
            iterations=algorithm["iterations"],
            seed=algorithm["seed"],
            input_profile=input_beam["profile"],
            gaussian_waist_px=input_beam["gaussian_waist_px"],
            custom_beam_image=_decode_image(
                input_beam.get("custom_image"),
                "algorithm.input_beam.custom_image",
                reject_black=True,
            ),
            invert_target=control["invert_target"],
            flip_horizontal=control["flip_horizontal"],
            flip_vertical=control["flip_vertical"],
            offset_x_wraps=control["offset_x_wraps"],
            offset_y_wraps=control["offset_y_wraps"],
        )
    except KeyError as exc:
        raise MaskConfigError(f"Missing required configuration field: {exc.args[0]}.") from exc
    return validate_mask_configuration(config)


def save_mask_configuration(config: MaskConfiguration, path: str | Path) -> Path:
    destination = ensure_config_extension(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = mask_configuration_to_dict(config)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(document, temporary, indent=2)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, destination)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    return destination


def load_mask_configuration(path: str | Path) -> MaskConfiguration:
    try:
        with Path(path).open("r", encoding="utf-8") as source:
            document = json.load(source)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MaskConfigError(f"Could not read configuration: {exc}") from exc
    return mask_configuration_from_dict(document)
