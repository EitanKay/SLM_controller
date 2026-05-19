"""
used to calibrate the SLM. allows to scan through a range of calibration patterns, 
capture the resulting images, and save them for later analysis.
"""

import sys
import time
from pathlib import Path
from PIL import Image
import numpy as np

# Add project root to sys.path to resolve imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from scripts.calibration.generate_slm_calibration_frames import (
    CalibrationFrameGenerator,
    pack_meadowlark_dvi_16bit_to_rgb
)
from src.slm_512_driver import slm_512_driver
from src.thorcam_camera_driver import CameraDriver


# Configuration parameters for the calibration frame
GRATING_LOW = 0
GRATING_HIGH = 10320
STRIPE_WIDTH_PX = 2
SPLIT_X = 256
GRATING_AXIS = "x"

# Paramaters for the scan
SCAN_STEPS = 256

# Camera parameters
EXPOSURE_TIME_MS = 0.04
DLL_PATH = r"C:\Program Files\Thorlabs\Scientific Imaging\ThorImageCAM\bin"


def capture_calibration_step(mirror_val, generator, slm, camera, out_dir):
    print(f"Capturing image with mirror val: {mirror_val}")
    
    # Generate the pattern for this mirror value
    frame16 = generator.make_frame(
        mirror_value=mirror_val,
        grating_low=GRATING_LOW,
        grating_high=GRATING_HIGH,
        stripe_width_px=STRIPE_WIDTH_PX,
        split_x=SPLIT_X,
        grating_axis=GRATING_AXIS
    )

    # Pack to 24-bit RGB (required by Meadowlark SDK for 16-bit operation)
    frame_rgb = pack_meadowlark_dvi_16bit_to_rgb(frame16)
    pattern_image = Image.fromarray(frame_rgb, mode="RGB")
    
    slm.set_pattern(pattern_image)

    # Give the SLM liquid crystals a moment to stabilize
    time.sleep(0.5)

    # Capture and save using raw16 for true intensity data
    img = camera.get_image(output_format="raw16")
    output_file = out_dir / f"camera_c  apture_{mirror_val:05d}.tif"
    img.save(output_file)
    print(f"Captured image saved to: {output_file}")


def main():
    out_dir = project_root / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    generator = CalibrationFrameGenerator()
    mirror_values = np.linspace(0, 65535, SCAN_STEPS, dtype=np.uint16)

    try:
        # Utilize chained context managers for flat, automatic cleanup
        with slm_512_driver() as slm, CameraDriver(dll_path=DLL_PATH, exposure_time_ms=EXPOSURE_TIME_MS) as camera:
            slm.set_use_calibration(False)
            
            for mirror_val in mirror_values:
                capture_calibration_step(mirror_val, generator, slm, camera, out_dir)
                
            print("Cleaning up SLM...")
            slm.clear_pattern()
            
    except Exception as e:
        print(f"Error during scan: {e}")

    print("Scan Complete")

if __name__ == "__main__":
    main()

