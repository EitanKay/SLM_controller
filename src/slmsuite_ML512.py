"""
Wrapper for Meadowlark Blink DVI 512x512 SLM to work with slmsuite.
"""

from slmsuite.hardware.slms.slm import SLM
from slm_512_driver import slm_512_driver
import numpy as np

class ML512(SLM):
    """
    slmsuite wrapper for the Meadowlark Blink DVI 512x512 SLM.
    """

    def __init__(
        self,
        sdk_dir=None,
        bitdepth=8,
        wav_um=1,
        pitch_um=(15.0, 15.0), # Ensure these are correct for your specific hardware
        **kwargs
    ):
        """
        Initialize the ML512 SLM wrapper.
        
        Parameters
        ----------
        sdk_dir : str or None
            Path to the Blink DVI SDK directory.
        bitdepth : int
            Depth of SLM pixel well in bits. Defaults to 8.
        wav_um : float
            Wavelength of operation in microns. Defaults to 1.
        pitch_um : (float, float)
            Pixel pitch in microns. Defaults to 15 um square.
        **kwargs
            Additional arguments passed to slmsuite.hardware.slms.slm.SLM.
        """
        # Initialize the custom driver and open the hardware connection
        self.hardware = slm_512_driver(sdk_dir=sdk_dir)
        width, height = self.hardware.open()

        # Instantiate the slmsuite SLM superclass
        super().__init__(
            (width, height),
            bitdepth=bitdepth,
            wav_um=wav_um,
            pitch_um=pitch_um,
            **kwargs
        )

        # Zero the display array initially
        self.set_phase(None)

    def close(self):
        """Close the SLM hardware and delete related objects."""
        if hasattr(self, "hardware") and self.hardware is not None:
            self.hardware.close()
        super().close()

    def _set_phase_hw(self, display, execute=True, block=True, **kwargs):
        """
        Hardware-specific implementation to write data to the SLM.
        
        This method is called automatically by `self.set_phase()` after 
        phase values have been modulo-wrapped and converted to an 8-bit display array.
        """
        if execute:
            self.hardware.set_pattern(display)

    def load_lut(self, lut_path=None):
        """
        Load a LUT file via the underlying SLM driver.
        """
        self.hardware.load_lut(lut_path)

    def load_wfc(self, wfc_path=None):
        """
        Load a Wavefront Correction file via the underlying SLM driver.
        """
        self.hardware.load_wfc(wfc_path)
        
    def set_use_calibration(self, enabled):
        """
        Enable or disable calibration in the underlying SLM driver.
        """
        self.hardware.set_use_calibration(enabled)
