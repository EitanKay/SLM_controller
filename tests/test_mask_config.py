import json

import numpy as np
import pytest

from src.slm_gui.mask_config import (
    CONFIG_EXTENSION,
    CONFIG_FORMAT,
    EmbeddedGrayImage,
    MaskConfigError,
    MaskConfiguration,
    default_config_directory,
    load_mask_configuration,
    save_mask_configuration,
)


def _complete_config() -> MaskConfiguration:
    target = np.arange(512 * 512, dtype=np.uint32).reshape(512, 512).astype(np.uint8)
    beam = np.full((512, 512), 64, dtype=np.uint8)
    beam[100:200, 150:250] = 255
    return MaskConfiguration(
        target_source="file",
        hg_n=3,
        hg_m=4,
        hg_waist=91.5,
        hg_normalize="power",
        hg_rotation=-17.5,
        target_image=EmbeddedGrayImage("source target.png", target),
        algorithm="WGS-Wu",
        iterations=73,
        seed=194,
        input_profile="custom",
        gaussian_waist_px=177.2,
        custom_beam_image=EmbeddedGrayImage("measured beam.tif", beam),
        invert_target=True,
        flip_horizontal=True,
        flip_vertical=False,
        offset_x_wraps=12.125,
        offset_y_wraps=-7.5,
    )


def test_mask_configuration_round_trip_embeds_images_and_adds_extension(tmp_path):
    source = _complete_config()

    saved_path = save_mask_configuration(source, tmp_path / "experiment")
    loaded = load_mask_configuration(saved_path)

    assert saved_path.suffix == CONFIG_EXTENSION
    assert loaded.target_source == source.target_source
    assert loaded.hg_n == source.hg_n
    assert loaded.hg_m == source.hg_m
    assert loaded.hg_waist == pytest.approx(source.hg_waist)
    assert loaded.hg_normalize == source.hg_normalize
    assert loaded.hg_rotation == pytest.approx(source.hg_rotation)
    assert loaded.algorithm == source.algorithm
    assert loaded.iterations == source.iterations
    assert loaded.seed == source.seed
    assert loaded.input_profile == source.input_profile
    assert loaded.gaussian_waist_px == pytest.approx(source.gaussian_waist_px)
    assert loaded.invert_target is True
    assert loaded.flip_horizontal is True
    assert loaded.flip_vertical is False
    assert loaded.offset_x_wraps == pytest.approx(source.offset_x_wraps)
    assert loaded.offset_y_wraps == pytest.approx(source.offset_y_wraps)
    assert loaded.target_image.name == "source target.png"
    assert loaded.custom_beam_image.name == "measured beam.tif"
    np.testing.assert_array_equal(
        loaded.target_image.pixels, source.target_image.pixels
    )
    np.testing.assert_array_equal(
        loaded.custom_beam_image.pixels, source.custom_beam_image.pixels
    )

    document = json.loads(saved_path.read_text(encoding="utf-8"))
    assert document["format"] == CONFIG_FORMAT
    assert document["version"] == 1
    assert document["target"]["file_image"]["encoding"] == "base64-png"
    assert "source target.png" not in document["target"]["file_image"]["data"]


def test_mask_configuration_rejects_corrupt_json_and_unsupported_version(tmp_path):
    corrupt = tmp_path / "corrupt.slmconfig"
    corrupt.write_text("{not-json", encoding="utf-8")
    with pytest.raises(MaskConfigError, match="Could not read configuration"):
        load_mask_configuration(corrupt)

    unsupported = tmp_path / "future.slmconfig"
    unsupported.write_text(
        json.dumps({"format": CONFIG_FORMAT, "version": 99}), encoding="utf-8"
    )
    with pytest.raises(MaskConfigError, match="Unsupported mask configuration version"):
        load_mask_configuration(unsupported)


def test_mask_configuration_requires_active_embedded_assets(tmp_path):
    source = _complete_config()
    without_target = MaskConfiguration(**{**source.__dict__, "target_image": None})
    with pytest.raises(MaskConfigError, match="must include its target image"):
        save_mask_configuration(without_target, tmp_path / "missing-target")

    black_beam = EmbeddedGrayImage(
        "black.png", np.zeros((512, 512), dtype=np.uint8)
    )
    with_black_beam = MaskConfiguration(
        **{**source.__dict__, "custom_beam_image": black_beam}
    )
    with pytest.raises(MaskConfigError, match="cannot be entirely black"):
        save_mask_configuration(with_black_beam, tmp_path / "black-beam")


def test_default_config_directory_uses_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    directory = default_config_directory()

    assert directory == tmp_path / "SLMControl" / "configs"
    assert directory.is_dir()
