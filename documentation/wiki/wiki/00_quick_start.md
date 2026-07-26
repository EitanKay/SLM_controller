# 00 — Quick start

Goal: verify that the SLM, software, laser path, Fourier lens, and camera are basically working by displaying a simple grating and observing a shifted diffraction order.

This page is intentionally short. Use it before trying HG modes, vortex beams, or holograms.

## Before turning anything on

- Follow the lab laser-safety procedure.
- Verify that beam height and beam path are safe and terminated.
- Make sure the SLM active area is not exposed to unnecessary dust or contact.
- Confirm that the correct computer/display configuration is being used.
- Confirm which LUT/WFC should be loaded for the wavelength in use.

## Startup checklist

1. Turn on the control PC.
2. Turn on the Meadowlark DVI controller.
3. Turn on the laser at low power.
4. Open the SLM controller repo on the lab PC.
5. Run the hardware setup check:

   ```powershell
   .\.venv\Scripts\python.exe scripts\check_hardware_setup.py
   ```

6. Launch the GUI:

   ```powershell
   .\scripts\run_gui.ps1
   ```

7. Display the simplest test mask first:

   - flat mask, then
   - linear ramp / blazed grating.

8. Look at the Fourier plane with the camera or a safe viewing method.

## Expected result

For a flat mask:

- most light remains in the zero order;
- pixel-grid diffraction may still be visible;
- the camera should not be saturated.

For a linear ramp / blazed grating:

- the desired order shifts away from the zero order;
- additional weaker diffraction orders may be visible;
- use the iris to select the desired order.

## If nothing useful happens

Do not start debugging HG modes yet. Work in this order:

1. Confirm laser and camera are working without relying on the SLM.
2. Confirm that the SLM is recognized as the correct display / hardware target.
3. Confirm image dimensions and encoding.
4. Confirm polarization.
5. Confirm a simple ramp shifts the diffraction order.
6. Confirm the camera is at the Fourier plane and not saturated.

## Shutdown checklist

1. Clear the SLM pattern or display a safe blank/flat pattern.
2. Stop acquisition in the camera software/GUI.
3. Close the GUI.
4. Turn off or reduce the laser according to lab procedure.
5. Turn off the SLM controller if the setup will not be used.
6. Cover the SLM aperture if appropriate.
