SLMControl Offline Package
==========================

How to run
----------
1. Unzip the full SLMControl folder onto the target computer.
2. Open the unzipped folder.
3. Double-click SLMControl.exe.

No Python installation or virtual environment is required for this packaged GUI.

Hardware prerequisites
----------------------
The executable does not include Meadowlark or Thorlabs vendor SDK installers or
vendor hardware drivers.

For hardware mode, install the Meadowlark Blink DVI SDK before running the app.
The expected SDK location is:

    C:\Program Files\Meadowlark Optics\Blink DVI\SDK

Verify this file exists:

    C:\Program Files\Meadowlark Optics\Blink DVI\SDK\Blink_C_wrapper.dll

For camera workflows, install the Thorlabs camera software/drivers used by the
lab computer. The GUI can still start without a camera connected.

Included files
--------------
This package includes the GUI executable, the bundled Python runtime and Python
dependencies, repo LUT files, and black.bmp from slm-files/WFC_files.

It intentionally does not include Meadowlark SDK DLLs, Thorlabs drivers,
installers, generated data, notebooks, or development files.

Troubleshooting
---------------
- If the app does not connect to the SLM, confirm the Meadowlark SDK is installed
  in Program Files and the SLM is connected/configured as expected.
- If Windows blocks the app because it came from another computer, right-click
  the zip or exe, choose Properties, and use Unblock if present.
- If you need to test without hardware, ask the developer for a simulator-mode
  package or launch option.
