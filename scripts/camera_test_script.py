import pylablib as pll

# Adjust this path to wherever Thorlabs installed the DLLs.
# Common possibilities:
# r"C:\Program Files\Thorlabs\Scientific Imaging\ThorImageCAM\bin"
# r"C:\Program Files\Thorlabs\Scientific Imaging\ThorCam"


pll.par["devices/dlls/thorlabs_tlcam"] = (
    r"C:\Program Files\Thorlabs\Scientific Imaging\ThorImageCAM\bin"
)

from pylablib.devices import Thorlabs

print("Connected cameras:")
print(Thorlabs.list_cameras_tlcam())

serial = Thorlabs.list_cameras_tlcam()[0]
cam = Thorlabs.ThorlabsTLCamera(serial=serial)

print("Device info:", cam.get_device_info())
print("Sensor info:", cam.get_sensor_info())
print("Detector size:", cam.get_detector_size())

cam.set_exposure(0.02)  # seconds, so 0.02 = 20 ms
cam.set_trigger_mode("int")

cam.start_acquisition()
frame = cam.snap(timeout=5)

import numpy as np
from PIL import Image

f = frame.astype(np.float32)

# autoscale using actual min/max
f = f - f.min()
f = f / f.max()
img8 = (255 * f).astype(np.uint8)

Image.fromarray(img8).save("test_image_scaled.png")


cam.stop_acquisition()
cam.close()

print(frame.shape, frame.dtype)