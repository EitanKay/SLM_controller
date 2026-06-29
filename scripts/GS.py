import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from tqdm import tqdm

def load_target_image(path, size=(512, 512), invert=False):
    """Load image as normalized target amplitude."""
    img = Image.open(path).convert("L").resize(size, Image.Resampling.LANCZOS)
    arr = np.array(img, dtype=np.float64)

    if invert:
        arr = 255 - arr

    arr /= arr.max() if arr.max() > 0 else 1.0

    # GS usually works with target amplitude, not intensity
    target_amp = np.sqrt(arr)
    return target_amp


def gerchberg_saxton(target_amp, iterations=100, seed=0):
    """
    Phase-only GS hologram for a Fourier-plane target.

    Returns:
        phase_mask    : SLM phase in [0, 2pi)
        farfield_amp  : simulated far-field amplitude
        farfield_int  : simulated far-field intensity
    """
    rng = np.random.default_rng(seed)

    ny, nx = target_amp.shape

    # Start with constant amplitude + random phase in SLM plane
    field_slm = np.exp(1j * rng.uniform(0, 2*np.pi, size=(ny, nx)))

    for _ in tqdm(range(iterations)):
        # Forward propagate to Fourier plane
        field_fourier = np.fft.fftshift(np.fft.fft2(field_slm))
        phase_fourier = np.angle(field_fourier)

        # Enforce target amplitude in Fourier plane
        field_fourier = target_amp * np.exp(1j * phase_fourier)

        # Back propagate to SLM plane
        field_slm = np.fft.ifft2(np.fft.ifftshift(field_fourier))

        # Enforce phase-only constraint in SLM plane
        field_slm = np.exp(1j * np.angle(field_slm))

    # Final outputs
    field_fourier = np.fft.fftshift(np.fft.fft2(field_slm))
    farfield_amp = np.abs(field_fourier)
    farfield_int = farfield_amp**2
    farfield_int /= farfield_int.max() if farfield_int.max() > 0 else 1.0

    phase_mask = np.mod(np.angle(field_slm), 2*np.pi)
    return phase_mask, farfield_amp, farfield_int


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


if __name__ == "__main__":
    # ---- settings ----
    image_path = "color_test.png"   # put your image here
    size = (512,512) #(1280, 1024)           # match your SLM active area
    blink_size = (512, 512)
    iterations = 50
    invert = True    # set True if target is black-on-white and you want white-on-black

    # ---- run GS ----
    target_amp = load_target_image(image_path, size=size, invert=invert)
    phase_mask, _, sim_int = gerchberg_saxton(target_amp, iterations=iterations)

    # Convert for SLM output
    phase_u16 = phase_to_uint16(phase_mask)

    # Save 16-bit phase mask
    Image.fromarray(phase_u16).save("gs_phase_mask.png")

    # save the simulated far-field intensity for inspection
    sim_int_u8 = np.uint8(np.round(sim_int * 255))
    Image.fromarray(sim_int_u8).save("gs_simulated_intensity.png")


    # Also save an 8-bit preview for inspection
    phase_preview = np.uint8(np.round(phase_mask * 255 / (2*np.pi)))
    Image.fromarray(phase_preview).save("gs_phase_preview.png")

    # Save Meadowlark Blink DVI compatible BMP
    if phase_u16.shape != blink_size:
        phase_img = Image.fromarray(phase_u16)
        phase_u16_blink = np.array(
            phase_img.resize(blink_size, Image.Resampling.NEAREST),
            dtype=np.uint16
        )
    else:
        phase_u16_blink = phase_u16

    blink_bmp_path = "gs_phase_mask_blink_dvi.bmp"
    save_blink_dvi_bmp(phase_u16_blink, blink_bmp_path)

    print(
        "Saved: gs_phase_mask.png, gs_simulated_intensity.png, "
        "gs_phase_preview.png, gs_phase_mask_blink_dvi.bmp "
        f"(BMP shape: {phase_u16_blink.shape})"
    )

    # ---- display ----
    plt.figure(figsize=(12, 4))

    plt.subplot(1, 3, 1)
    plt.title("Target amplitude")
    plt.imshow(target_amp, cmap="gray")
    plt.axis("off")

    plt.subplot(1, 3, 2)
    plt.title("Simulated far-field intensity")
    plt.imshow(sim_int, cmap="gray")
    plt.axis("off")

    plt.subplot(1, 3, 3)
    plt.title("Phase mask preview")
    plt.imshow(phase_mask, cmap="hsv")
    plt.axis("off")

    plt.tight_layout()
    plt.show()
