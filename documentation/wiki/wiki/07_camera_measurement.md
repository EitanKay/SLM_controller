# 07 — Camera and measurement

## Purpose

The camera is the main verification tool for routine operation and LUT calibration. Use it to check diffraction orders, mode shape, saturation, and calibration scans.

## Thorlabs camera driver assumptions

The Python camera wrapper uses `pylablib` and the Thorlabs TLCamera backend.

The DLL path used in current scripts is:

```text
C:\Program Files\Thorlabs\Scientific Imaging\ThorImageCAM\bin
```

The current `CameraDriver` supports:

- exposure time in ms;
- gain;
- optional camera serial;
- `raw16` output for quantitative images;
- `scaled8` output for quick visual inspection.

## Routine camera checklist

Before recording a useful image:

1. Confirm camera is found by the driver.
2. Confirm exposure is not saturating the region of interest.
3. Confirm selected diffraction order is inside the sensor area.
4. Confirm the camera is at the intended plane.
5. Save raw data for analysis, not only screenshots.

## Saturation check

For 16-bit images, check the maximum pixel value. A value near 65535 means saturation.

Record:

| Field | Value |
|---|---|
| Exposure time | TODO ms |
| Gain | TODO |
| Max pixel | TODO |
| ROI | TODO |
| Lens/camera position | TODO |

## Calibration images

The active calibration scan saves images named:

```text
camera_capture_<mirror_value>.tif
```

These should be `raw16` TIFFs. The calibration notebook extracts phase information from the chosen ROI/line cut.

## Camera settings record template

```md
# Camera record

- Date:
- Operator:
- Camera model/serial:
- Exposure:
- Gain:
- ROI/crop:
- Plane observed:
- LUT/WFC:
- Pattern/mode:
- Output files:
- Notes:
```
