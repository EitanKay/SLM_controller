import numpy as np
import matplotlib.pyplot as plt


class HermiteGaussianGenerator:
    """
    Generate Hermite-Gaussian modes on a 2D grid.

    The generated waist-plane field is:

        HG_nm(x,y) = H_n(sqrt(2) x / w0) H_m(sqrt(2) y / w0)
                    exp(-(x^2 + y^2) / w0^2)

    where H_n is the physicists' Hermite polynomial.
    """

    def __init__(
        self,
        shape=(512, 512),
        extent=None,
        pixel_size=None,
        center=None,
        dtype=np.float64,
    ):
        """
        Parameters
        ----------
        shape : tuple[int, int]
            Grid shape as (height, width). For your SLM, use (512, 512).

        extent : tuple[float, float] or None
            Physical size of grid as (height_extent, width_extent).
            Example: for Meadowlark 512 SLM, extent=(7.68e-3, 7.68e-3) meters.
            If None, coordinates are in pixels.

        pixel_size : float or None
            Alternative to extent. Pixel size in physical units.
            Example: 15e-6 meters for the Meadowlark 512 SLM.
            If extent and pixel_size are both None, coordinates are pixel units.

        center : tuple[float, float] or None
            Beam center as (y0, x0), in the same units as the coordinate grid.
            If None, center is at the grid center.

        dtype : numpy dtype
            Floating-point type.
        """
        self.shape = tuple(shape)
        self.height, self.width = self.shape
        self.dtype = dtype

        if extent is not None and pixel_size is not None:
            raise ValueError("Use either extent or pixel_size, not both.")

        if extent is not None:
            y_extent, x_extent = extent
            y = np.linspace(-y_extent / 2, y_extent / 2, self.height, dtype=dtype)
            x = np.linspace(-x_extent / 2, x_extent / 2, self.width, dtype=dtype)

        elif pixel_size is not None:
            y = (np.arange(self.height, dtype=dtype) - (self.height - 1) / 2) * pixel_size
            x = (np.arange(self.width, dtype=dtype) - (self.width - 1) / 2) * pixel_size

        else:
            y = np.arange(self.height, dtype=dtype) - (self.height - 1) / 2
            x = np.arange(self.width, dtype=dtype) - (self.width - 1) / 2

        self.x, self.y = np.meshgrid(x, y)

        if center is not None:
            y0, x0 = center
            self.x = self.x - x0
            self.y = self.y - y0

    @staticmethod
    def hermite_physicists(n, u):
        """
        Physicists' Hermite polynomial H_n(u).

        H_0 = 1
        H_1 = 2u
        H_{n+1} = 2u H_n - 2n H_{n-1}
        """
        if n < 0:
            raise ValueError("Hermite order n must be non-negative.")

        if n == 0:
            return np.ones_like(u)

        if n == 1:
            return 2 * u

        H_nm2 = np.ones_like(u)
        H_nm1 = 2 * u

        for k in range(1, n):
            H_n = 2 * u * H_nm1 - 2 * k * H_nm2
            H_nm2, H_nm1 = H_nm1, H_n

        return H_nm1

    def field(self, n, m, waist, normalize="peak"):
        """
        Generate complex/real HG_nm field at the waist plane.

        Parameters
        ----------
        n, m : int
            HG mode indices. HG_11 means n=1, m=1.

        waist : float
            Beam waist radius w0, in the same units as the grid.
            If using pixel coordinates, waist is in pixels.
            If using meters, waist is in meters.

        normalize : {"peak", "power", None}
            "peak"  : max(abs(field)) = 1
            "power" : sum(abs(field)^2) = 1
            None    : no normalization

        Returns
        -------
        field : np.ndarray
            2D HG field array.
        """
        if waist <= 0:
            raise ValueError("waist must be positive.")

        u = np.sqrt(2) * self.x / waist
        v = np.sqrt(2) * self.y / waist

        Hn = self.hermite_physicists(n, u)
        Hm = self.hermite_physicists(m, v)

        gaussian = np.exp(-(self.x**2 + self.y**2) / waist**2)

        field = Hn * Hm * gaussian

        if normalize == "peak":
            max_abs = np.max(np.abs(field))
            if max_abs > 0:
                field = field / max_abs

        elif normalize == "power":
            power = np.sum(np.abs(field)**2)
            if power > 0:
                field = field / np.sqrt(power)

        elif normalize is None:
            pass

        else:
            raise ValueError("normalize must be 'peak', 'power', or None.")

        return field

    def intensity(self, n, m, waist, normalize="peak"):
        """
        Generate HG intensity: |field|^2.
        """
        E = self.field(n, m, waist, normalize=normalize)
        I = np.abs(E)**2

        if normalize == "peak":
            max_I = np.max(I)
            if max_I > 0:
                I = I / max_I

        return I

    def phase(self, n, m, waist):
        """
        Generate phase of the real HG field.

        At the waist plane, HG modes are real, so the phase is mostly 0 or pi.
        This is useful for making a phase-only approximation on an SLM.
        """
        E = self.field(n, m, waist, normalize="peak")
        return np.angle(E.astype(np.complex128))

    def plot(self, arr, title=None, cmap="RdBu", colorbar=True):
        """
        Visualize a generated field, intensity, or phase.
        """
        plt.figure(figsize=(6, 5))
        im = plt.imshow(arr, origin="lower", cmap=cmap)
        if colorbar:
            plt.colorbar(im)
        if title is not None:
            plt.title(title)
        plt.xlabel("x pixel")
        plt.ylabel("y pixel")
        plt.tight_layout()
        plt.show()

    def plot_mode(self, n, m, waist):
        """
        Convenience function: plot field, intensity, and phase.
        """
        E = self.field(n, m, waist)
        I = np.abs(E)**2
        phi = np.angle(E.astype(np.complex128))

        self.plot(E, title=f"HG_{n}{m} field amplitude", cmap="RdBu")
        self.plot(I, title=f"HG_{n}{m} intensity", cmap="inferno")
        self.plot(phi, title=f"HG_{n}{m} phase", cmap="twilight")

