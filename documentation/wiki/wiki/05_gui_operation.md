# 05 — GUI operation

## Routine workflow

```text
choose desired mode → generate phase mask → send to SLM → select diffraction order → verify with camera
```

The GUI-centered workflow is intended to avoid manually editing mask scripts during routine operation.

## Launch modes

Hardware:

```powershell
.\scripts\run_gui.ps1
```

Simulator:

```powershell
.\scripts\run_gui_sim.ps1
```

## Basic GUI checklist

1. Choose mode family, e.g. HG/TEM.
2. Set indices and beam waist.
3. Set rotation/normalization if relevant.
4. Add linear ramp/carrier if order selection is needed.
5. Generate the mask.
6. Inspect the displayed target/mask preview.
7. Send to SLM.
8. Move/align the desired diffraction order to the iris.
9. Verify camera image.

## Practical rules

- Do not trust a complex mode until a linear ramp behaves correctly.
- Always know whether you are looking at the zero order or the selected diffraction order.
- If the output looks like a spot when expecting a donut/HG mode, check order selection before changing the algorithm.
- Keep camera exposure fixed when comparing modes, unless you record the change.

## What the GUI can reasonably do

- Generate phase masks.
- Send masks to the SLM through the Python driver.
- Support simulator/hardware workflows.
- Provide a practical interface for routine mode generation.

## What the GUI cannot prove by itself

- That the LUT is correct.
- That the optical output has the intended phase.
- That the selected diffraction order is isolated.
- That the camera is not saturated.
- That a generated intensity pattern is suitable for fiber coupling.

## Add screenshot

Place a screenshot here:

```text
diagrams/gui_overview_annotated.png
```

Suggested labels:

1. Mode family selector.
2. Mode parameters.
3. Ramp/order-selection controls.
4. Generate mask button.
5. Send to SLM button.
6. Preview: target and encoded phase mask.
