# 09 — Troubleshooting

Format: symptom → likely causes → checks → corrective action.

## No response on SLM / output unchanged

Likely causes:

- GUI is in simulator mode.
- Meadowlark SDK missing or wrong path.
- SLM is not configured as the correct DVI/second display.
- Controller is off or disconnected.
- Pattern is displayed on the main monitor instead of the SLM.

Checks:

- Run `scripts/check_hardware_setup.py`.
- Verify `Blink_C_wrapper.dll` exists in the expected SDK path.
- Check display settings.
- Try flat mask then obvious grating.

Corrective action:

- Re-run setup script.
- Fix SDK installation/path.
- Reconnect DVI/controller cables.
- Restart GUI and controller.

## Image appears incorrect / bar appears / software crashes

Likely causes:

- image size is not 512×512;
- image encoding is not Meadowlark-compatible;
- wrong RGB packing;
- using an old file/folder in the vendor GUI.

Checks:

- Confirm dimensions are 512×512.
- Confirm 24-bit BMP/RGB packing if using manual BMPs.
- Confirm green = MSB, red = LSB, blue ignored/zero for 16-bit DVI images.

Corrective action:

- Regenerate the test pattern with the project scripts.
- Restart the software if a too-large image crashed it.

## Vortex mask gives a spot, not a donut

Likely causes:

- looking at zero order;
- no carrier grating / wrong order selected;
- iris not selecting the desired order;
- camera not at the intended plane;
- LUT not giving full 2π phase;
- beam not centered on vortex singularity;
- saturation hides central null.

Checks:

1. Display only a linear ramp.
2. Find shifted first order.
3. Place iris on that order.
4. Add vortex phase on top of the carrier.
5. Reduce exposure.

Corrective action:

- Re-align order selection.
- Recenter beam/mask.
- Validate LUT.

## HG/TEM mode shape looks wrong

Likely causes:

- wrong order selected;
- beam waist parameter mismatch;
- beam too small or clipped on SLM;
- wrong normalization/rotation;
- input beam not Gaussian enough;
- LUT/polarization issue.

Checks:

- Reproduce HG10 before HG11 or higher modes.
- Save target, phase mask, raw camera image, and crop.
- Compare with fixed exposure.

Corrective action:

- Tune waist slowly.
- Recenter input beam.
- Check polarization and LUT.

## Too many diffraction orders / messy laser-show pattern

Likely causes:

- carrier/ramp frequency too high;
- pixel-grid diffraction visible;
- no spatial filtering;
- camera sees multiple orders at once.

Checks:

- Use a slower ramp.
- Move to Fourier plane.
- Close iris around a single order.

Corrective action:

- Reduce carrier frequency.
- Improve iris placement.
- Increase separation only as much as needed.

## Camera saturated

Likely causes:

- exposure too long;
- gain too high;
- laser power too high;
- zero order entering ROI.

Checks:

- Inspect max pixel value in raw16 image.
- Reduce exposure and compare.

Corrective action:

- Reduce exposure/gain/power.
- Block or move zero order.
- Record new settings.

## Calibration scan fails

Likely causes:

- Meadowlark SDK unavailable;
- ThorImageCAM DLL path wrong;
- camera not found;
- old capture directory/file permissions issue;
- ROI not visible in notebook.

Checks:

- Run hardware setup check.
- Confirm camera serial is found.
- Confirm `results/current` is writable.
- Confirm `camera_capture_*.tif` files were created.

Corrective action:

- Fix DLL paths.
- Reinstall or unblock vendor runtimes.
- Re-run scan at safe exposure.

## New LUT does not improve output

Likely causes:

- calibration measured wrong optical signal;
- camera saturated;
- ROI chosen incorrectly;
- phase unwrap/fit failed;
- LUT installed in wrong folder;
- GUI still using old LUT;
- calibration state mismatch.

Checks:

- Inspect notebook plots.
- Check monotonicity of inverse LUT.
- Verify file loaded by GUI/driver.
- Validate with a simple grating and vortex before complex modes.

Corrective action:

- Redo scan with better ROI/exposure.
- Give LUT a meaningful filename.
- Record optical validation before using it.

## SLM becomes primary monitor on boot

Likely causes:

- Windows display configuration picked the SLM/controller as primary.

Corrective action:

- Shut down.
- Disconnect the Meadowlark DVI system from the graphics card.
- Boot with only the normal monitor.
- Fix display arrangement.
- Reconnect SLM/controller.
