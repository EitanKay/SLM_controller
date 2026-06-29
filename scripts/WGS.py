import sys
import numpy as np
from PIL import Image
import warnings

warnings.filterwarnings('ignore', category=UserWarning)

try:
    from slmsuite.holography.algorithms import Hologram
except ImportError:
    print("Error: slmsuite is not installed. Please install it to use this script.")
    sys.exit(1)

def load_target_image(path, size=(512, 512), invert=False):
    """Load image as normalized target amplitude."""
    img = Image.open(path).convert("L").resize(size, Image.Resampling.LANCZOS)
    arr = np.array(img, dtype=np.float64)

    if invert:
        arr = 255 - arr

    arr /= arr.max() if arr.max() > 0 else 1.0

    target_amp = np.sqrt(arr)
    return target_amp

def phase_to_uint16(phase_mask):
    """Map phase [0, 2pi) to uint16 [0, 65535]."""
    return np.uint16(np.round(phase_mask * 65535 / (2*np.pi)))

def save_blink_dvi_bmp(phase_u16, path):
    phase_u16 = np.asarray(phase_u16, dtype=np.uint16)
    r = (phase_u16 & 0xFF).astype(np.uint8)
    g = (phase_u16 >> 8).astype(np.uint8)
    b = np.zeros_like(r, dtype=np.uint8)
    rgb = np.dstack([r, g, b])
    Image.fromarray(rgb, mode="RGB").save(path, format="BMP")

def WGS(slm_shape, target_amp, maxiter=30):
    hologram = Hologram(target=target_amp, slm_shape=slm_shape)
    hologram.optimize(method="WGS-Kim", maxiter=maxiter)
    return hologram.get_phase()

def WGS_on_file(input_path, output_path, slm_shape=(512, 512), maxiter=30):
    target_amp = load_target_image(input_path, size=(slm_shape[1], slm_shape[0]), invert=False)
    phase = WGS(slm_shape=slm_shape, target_amp=target_amp, maxiter=maxiter)
    phase_u16 = phase_to_uint16(phase)
    save_blink_dvi_bmp(phase_u16, output_path)


def main():
    if len(sys.argv) != 3:
        print("Usage: python WGS.py <input.png> <out.bmp>")
        sys.exit(1)

    input_file = sys.argv[1]
    out_file = sys.argv[2]
    
    slm_shape = (512, 512)
    
    WGS_on_file(input_file, out_file, slm_shape=slm_shape, maxiter=30)
    
    print(f"Mask saved to {out_file}.")

if __name__ == '__main__':
    main()
