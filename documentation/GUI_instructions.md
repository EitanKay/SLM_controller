# SLMControl GUI

## Mask Generation

The Mask Generation controls are grouped into collapsible **Target**, **Control**,
and **Algorithm** sections. Target and Control start open; Algorithm starts closed.

Algorithm → Input beam supports:

- **Uniform (plane wave)** for a constant field amplitude.
- **Gaussian** for a modeled Gaussian field with a configurable waist.
- **Custom** for a measured or modeled 512×512 image. The image is converted to
  grayscale and its 0–255 values are mapped directly to field amplitude 0–1. An
  entirely black image is not valid.

Loading a custom beam does not generate immediately. Press **Apply** or **Generate
Mask** after choosing it.

## Saved Configurations

Use **Save Config** and **Load Config** under Control to store or restore all Target,
Control, and Algorithm values. The default folder is
`%LOCALAPPDATA%\SLMControl\configs`.

The `.slmconfig` file embeds file-based target and custom-beam images, so the source
images do not need to remain at their original paths. Loading a valid configuration
applies it and schedules one mask generation. Hardware calibration settings and
generated BMP masks are not part of the configuration.
