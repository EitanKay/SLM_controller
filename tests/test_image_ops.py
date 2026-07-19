from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from src.slm_gui.image_ops import (
    ImageValidationError,
    apply_discrete_transform,
    apply_phase_offset_wraps,
    apply_target_transform,
    load_input_beam_image,
    load_strict_meadowlark_bmp,
    load_target_image,
    load_target_png,
    pack_meadowlark_dvi_16bit_to_rgb,
    phase_radians_to_uint16,
    uint16_to_calibrated_input_uint8,
    unpack_meadowlark_dvi_rgb_to_16bit,
)


def test_meadowlark_pack_unpack_round_trip():
    value16 = np.array([[0, 1, 255], [256, 1024, 65535]], dtype=np.uint16)
    rgb = pack_meadowlark_dvi_16bit_to_rgb(value16)

    assert rgb.dtype == np.uint8
    assert np.all(rgb[..., 2] == 0)
    np.testing.assert_array_equal(unpack_meadowlark_dvi_rgb_to_16bit(rgb), value16)


def test_strict_bmp_validation_accepts_packed_rgb(tmp_path: Path):
    value16 = np.arange(512 * 512, dtype=np.uint16).reshape(512, 512)
    rgb = pack_meadowlark_dvi_16bit_to_rgb(value16)
    path = tmp_path / "mask.bmp"
    Image.fromarray(rgb, mode="RGB").save(path, format="BMP")

    loaded16, loaded_rgb = load_strict_meadowlark_bmp(path)

    np.testing.assert_array_equal(loaded16, value16)
    np.testing.assert_array_equal(loaded_rgb, rgb)


def test_strict_bmp_validation_rejects_blue_channel(tmp_path: Path):
    rgb = np.zeros((512, 512, 3), dtype=np.uint8)
    rgb[0, 0, 2] = 1
    path = tmp_path / "bad.bmp"
    Image.fromarray(rgb, mode="RGB").save(path, format="BMP")

    with pytest.raises(ImageValidationError, match="blue channel"):
        load_strict_meadowlark_bmp(path)


def test_png_validation_requires_512_square(tmp_path: Path):
    path = tmp_path / "target.png"
    Image.fromarray(np.zeros((128, 512), dtype=np.uint8), mode="L").save(path)

    with pytest.raises(ImageValidationError, match="Expected 512x512 PNG"):
        load_target_png(path)


def test_general_target_image_loader_accepts_pil_readable_images(tmp_path: Path):
    arr = np.full((512, 512, 3), [10, 20, 30], dtype=np.uint8)
    path = tmp_path / "target.jpg"
    Image.fromarray(arr, mode="RGB").save(path)

    loaded = load_target_image(path)

    assert loaded.shape == (512, 512)
    assert loaded.dtype == np.uint8


def test_general_target_image_loader_rejects_wrong_size(tmp_path: Path):
    path = tmp_path / "target.tif"
    Image.fromarray(np.zeros((64, 512), dtype=np.uint8), mode="L").save(path)

    with pytest.raises(ImageValidationError, match="Expected 512x512 image"):
        load_target_image(path)


def test_input_beam_loader_converts_rgb_to_normalized_grayscale(tmp_path: Path):
    rgb = np.zeros((512, 512, 3), dtype=np.uint8)
    rgb[..., 0] = 255
    path = tmp_path / "beam.png"
    Image.fromarray(rgb, mode="RGB").save(path)

    amplitude = load_input_beam_image(path)

    assert amplitude.shape == (512, 512)
    assert amplitude.dtype == np.float64
    assert amplitude.min() == pytest.approx(76 / 255)
    assert amplitude.max() == pytest.approx(76 / 255)


def test_input_beam_loader_rejects_wrong_size_and_all_black(tmp_path: Path):
    wrong_size = tmp_path / "wrong.png"
    Image.fromarray(np.ones((64, 512), dtype=np.uint8), mode="L").save(wrong_size)
    with pytest.raises(ImageValidationError, match="Expected 512x512 image"):
        load_input_beam_image(wrong_size)

    black = tmp_path / "black.png"
    Image.fromarray(np.zeros((512, 512), dtype=np.uint8), mode="L").save(black)
    with pytest.raises(ImageValidationError, match="entirely black"):
        load_input_beam_image(black)


def test_transforms_flip_rotate_and_invert():
    arr = np.array([[0, 1], [2, 3]], dtype=np.uint8)

    np.testing.assert_array_equal(
        apply_discrete_transform(arr, flip_x=True), np.array([[1, 0], [3, 2]])
    )
    np.testing.assert_array_equal(
        apply_discrete_transform(arr, flip_y=True), np.array([[2, 3], [0, 1]])
    )
    np.testing.assert_array_equal(
        apply_discrete_transform(arr, rotate_quarter_turns=1),
        np.array([[1, 3], [0, 2]]),
    )
    np.testing.assert_array_equal(
        apply_target_transform(arr, invert=True), np.array([[255, 254], [253, 252]])
    )


def test_phase_radians_to_uint16_wraps_phase():
    phase = np.array([[0, np.pi], [2 * np.pi, -np.pi]], dtype=np.float64)
    value16 = phase_radians_to_uint16(phase)

    assert value16[0, 0] == 0
    assert 32767 <= value16[0, 1] <= 32768
    assert value16[1, 0] == 0
    assert 32767 <= value16[1, 1] <= 32768


def test_apply_phase_offset_wraps_adds_modulo_ramps():
    phase = np.zeros((2, 4), dtype=np.uint16)

    shifted = apply_phase_offset_wraps(phase, offset_x_wraps=1.0, offset_y_wraps=-1.0)

    np.testing.assert_array_equal(
        shifted,
        np.array(
            [
                [0, 16384, 32768, 49152],
                [32768, 49152, 0, 16384],
            ],
            dtype=np.uint16,
        ),
    )


def test_uint16_to_calibrated_input_uint8_scales_full_range():
    value16 = np.array([[0, 32768, 65535]], dtype=np.uint16)
    calibrated = uint16_to_calibrated_input_uint8(value16)

    assert calibrated.dtype == np.uint8
    np.testing.assert_array_equal(calibrated, np.array([[0, 128, 255]], dtype=np.uint8))
    assert calibrated.flags.c_contiguous
