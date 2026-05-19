"""
A simple script that tests integration between slm, camera and frame generation.
"""

import sys
import time
from pathlib import Path
from PIL import Image

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

def main():
    print("Generating calibration frame...")
    generator = CalibrationFrameGenerator()
    
    # Generate a constant mirror frame with a grating on the right
    frame16 = generator.make_frame(
        mirror_value=32768,
        grating_low=32768,
        grating_high=65535,
        stripe_width_px=2,
        split_x=256,
        grating_axis="x"
    )
    
    # Pack to 24-bit RGB (required by Meadowlark SDK for 16-bit operation)
    frame_rgb = pack_meadowlark_dvi_16bit_to_rgb(frame16)
    pattern_image = Image.fromarray(frame_rgb, mode="RGB")
    
    print("Connecting to SLM...")
    slm = slm_512_driver()
    try:
        slm.open()
        # Important: Disable calibration for direct 16-bit pattern passing
        slm.set_use_calibration(False) 
        
        print("Setting pattern on SLM...")
        slm.set_pattern(pattern_image)
        
        # Give the SLM liquid crystals a moment to stabilize
        time.sleep(0.5)
        
        print("Connecting to Camera...")
        camera = CameraDriver(
            exposure_time_ms=01.0,
            dll_path=r"C:\Program Files\Thorlabs\Scientific Imaging\ThorImageCAM\bin"
        )
        
        with camera:
            print("Capturing image...")
            img = camera.get_image(output_format="scaled8")
            
            output_file = "camera_capture.png"
            img.save(output_file)
            print(f"Captured image saved to: {output_file}")
            
    finally:
        print("Cleaning up SLM...")
        slm.clear_pattern()
        slm.close()
        print("Integration test complete.")

if __name__ == "__main__":
    main()