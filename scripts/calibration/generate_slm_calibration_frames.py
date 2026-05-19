# generate_slm_calibration_frames.py

from pathlib import Path
import argparse
import csv

import numpy as np
from PIL import Image


SLM_W = 512
SLM_H = 512
MAX16 = 65535


class CalibrationFrameGenerator:
    """
    Class-based API for SLM calibration frame generation.

    This generator creates uint16 phase frames (as numpy arrays) and can
    optionally save them as Meadowlark-compatible 24-bit BMP files.

    Example:
        from calibration.generate_slm_calibration_frames import CalibrationFrameGenerator

        gen = CalibrationFrameGenerator()
        frames, metadata = gen.generate_constant_mirror_scan_arrays(
            n_frames=16,
            scan_start=40000,
            scan_stop=50000,
            mirror_value=32768,
            grating_low=0,
            stripe_width_px=8,
        )
    """

    def __init__(self, slm_width=SLM_W, slm_height=SLM_H):
        self.slm_width = int(slm_width)
        self.slm_height = int(slm_height)

        if self.slm_width <= 0 or self.slm_height <= 0:
            raise ValueError("slm_width and slm_height must be positive")

    @staticmethod
    def clamp16(x):
        return np.uint16(np.clip(np.round(x), 0, MAX16))

    @staticmethod
    def linspace16(start, stop, n):
        return CalibrationFrameGenerator.clamp16(np.linspace(start, stop, n))

    @staticmethod
    def pack_meadowlark_dvi_16bit_to_rgb(value16_img):
        """
        Meadowlark DVI 16-bit packing:
            Green = 8 most significant bits
            Red   = 8 least significant bits
            Blue  = ignored / 0

        PIL uses RGB order.
        """
        value16_img = value16_img.astype(np.uint16)

        red_lsb = (value16_img & 0x00FF).astype(np.uint8)
        green_msb = ((value16_img >> 8) & 0x00FF).astype(np.uint8)
        blue = np.zeros_like(red_lsb, dtype=np.uint8)

        rgb = np.dstack([red_lsb, green_msb, blue])
        return rgb

    @staticmethod
    def save_bmp_24bit(frame16, path):
        rgb = CalibrationFrameGenerator.pack_meadowlark_dvi_16bit_to_rgb(frame16)
        img = Image.fromarray(rgb, mode="RGB")
        img.save(path, format="BMP")

    def make_square_grating(self, width, height, low, high, stripe_width_px, axis="x"):
        """
        Square-wave grating.

        axis="x": vertical stripes, changing along x.
        axis="y": horizontal stripes, changing along y.
        """
        width = int(width)
        height = int(height)
        low = int(self.clamp16(low))
        high = int(self.clamp16(high))

        if width < 0 or height < 0:
            raise ValueError("width and height must be non-negative")

        if stripe_width_px <= 0:
            raise ValueError("stripe_width_px must be positive")

        if axis == "x":
            coord = np.arange(width)
            stripes = ((coord // stripe_width_px) % 2).astype(bool)
            row = np.where(stripes, high, low).astype(np.uint16)
            grating = np.tile(row, (height, 1))
        elif axis == "y":
            coord = np.arange(height)
            stripes = ((coord // stripe_width_px) % 2).astype(bool)
            col = np.where(stripes, high, low).astype(np.uint16)
            grating = np.tile(col[:, None], (1, width))
        else:
            raise ValueError("axis must be 'x' or 'y'")

        return grating

    def make_frame(
        self,
        mirror_value,
        grating_low,
        grating_high,
        stripe_width_px,
        split_x=256,
        grating_axis="x",
    ):
        """
        Build one uint16 calibration frame (shape: [slm_height, slm_width]).

        Left side [0:split_x] is constant mirror value.
        Right side [split_x:] is a square grating.
        """
        split_x = int(split_x)
        if split_x < 0 or split_x > self.slm_width:
            raise ValueError(f"split_x must be in [0, {self.slm_width}]")

        frame = np.zeros((self.slm_height, self.slm_width), dtype=np.uint16)
        mirror_value = int(self.clamp16(mirror_value))
        frame[:, :split_x] = mirror_value

        rhs_w = self.slm_width - split_x
        if rhs_w > 0:
            rhs = self.make_square_grating(
                width=rhs_w,
                height=self.slm_height,
                low=grating_low,
                high=grating_high,
                stripe_width_px=stripe_width_px,
                axis=grating_axis,
            )
            frame[:, split_x:] = rhs

        return frame

    @staticmethod
    def _validate_n_frames(n_frames):
        if n_frames <= 0:
            raise ValueError("n_frames must be positive")

    @staticmethod
    def _constant_mirror_filename(index, grating_high):
        return f"{index:03d}_constMirror_gratingHigh_{int(grating_high):05d}.bmp"

    @staticmethod
    def _constant_grating_filename(index, mirror_value):
        return f"{index:03d}_constGrating_mirror_{int(mirror_value):05d}.bmp"

    def generate_constant_mirror_scan_arrays(
        self,
        n_frames,
        scan_start,
        scan_stop,
        mirror_value=32768,
        grating_low=0,
        stripe_width_px=8,
        split_x=256,
        grating_axis="x",
    ):
        """
        Mode A (in-memory):
        Keep mirror constant, scan grating_high from scan_start to scan_stop.

        Returns:
            frames: np.ndarray, shape (n_frames, slm_height, slm_width), dtype uint16
            metadata: list[dict], one row per frame
        """
        self._validate_n_frames(n_frames)
        if scan_start > scan_stop:
            raise ValueError("scan_start must be <= scan_stop")

        values = self.linspace16(scan_start, scan_stop, n_frames)
        frames = np.empty((n_frames, self.slm_height, self.slm_width), dtype=np.uint16)
        metadata = []

        for i, grating_high in enumerate(values):
            grating_high_int = int(grating_high)
            frame = self.make_frame(
                mirror_value=mirror_value,
                grating_low=grating_low,
                grating_high=grating_high_int,
                stripe_width_px=stripe_width_px,
                split_x=split_x,
                grating_axis=grating_axis,
            )
            frames[i] = frame

            metadata.append(
                {
                    "index": i,
                    "filename": self._constant_mirror_filename(i, grating_high_int),
                    "mode": "constant_mirror_scan_grating_contrast",
                    "mirror_value": int(mirror_value),
                    "scan_start": int(scan_start),
                    "scan_stop": int(scan_stop),
                    "grating_low": int(grating_low),
                    "grating_high": grating_high_int,
                    "stripe_width_px": int(stripe_width_px),
                    "split_x": int(split_x),
                    "grating_axis": grating_axis,
                }
            )

        return frames, metadata

    def generate_constant_grating_scan_arrays(
        self,
        n_frames,
        scan_stop,
        grating_low=0,
        grating_high=65535,
        stripe_width_px=8,
        split_x=256,
        grating_axis="x",
    ):
        """
        Mode B (in-memory):
        Keep grating constant, scan mirror value from 0 to scan_stop.

        Returns:
            frames: np.ndarray, shape (n_frames, slm_height, slm_width), dtype uint16
            metadata: list[dict], one row per frame
        """
        self._validate_n_frames(n_frames)

        values = self.linspace16(0, scan_stop, n_frames)
        frames = np.empty((n_frames, self.slm_height, self.slm_width), dtype=np.uint16)
        metadata = []

        for i, mirror_value in enumerate(values):
            mirror_value_int = int(mirror_value)
            frame = self.make_frame(
                mirror_value=mirror_value_int,
                grating_low=grating_low,
                grating_high=grating_high,
                stripe_width_px=stripe_width_px,
                split_x=split_x,
                grating_axis=grating_axis,
            )
            frames[i] = frame

            metadata.append(
                {
                    "index": i,
                    "filename": self._constant_grating_filename(i, mirror_value_int),
                    "mode": "constant_grating_scan_mirror",
                    "mirror_value": mirror_value_int,
                    "grating_low": int(grating_low),
                    "grating_high": int(grating_high),
                    "stripe_width_px": int(stripe_width_px),
                    "split_x": int(split_x),
                    "grating_axis": grating_axis,
                }
            )

        return frames, metadata

    def generate_constant_mirror_scan(
        self,
        out_dir,
        n_frames,
        scan_start,
        scan_stop,
        mirror_value=32768,
        grating_low=0,
        stripe_width_px=8,
        split_x=256,
        grating_axis="x",
    ):
        """
        Mode A (disk output):
        Save BMP frames and metadata.csv to out_dir.
        """
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        frames, metadata = self.generate_constant_mirror_scan_arrays(
            n_frames=n_frames,
            scan_start=scan_start,
            scan_stop=scan_stop,
            mirror_value=mirror_value,
            grating_low=grating_low,
            stripe_width_px=stripe_width_px,
            split_x=split_x,
            grating_axis=grating_axis,
        )

        for frame, row in zip(frames, metadata):
            self.save_bmp_24bit(frame, out_dir / row["filename"])

        write_metadata(out_dir / "metadata.csv", metadata)
        return frames, metadata

    def generate_constant_grating_scan(
        self,
        out_dir,
        n_frames,
        scan_stop,
        grating_low=0,
        grating_high=65535,
        stripe_width_px=8,
        split_x=256,
        grating_axis="x",
    ):
        """
        Mode B (disk output):
        Save BMP frames and metadata.csv to out_dir.
        """
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        frames, metadata = self.generate_constant_grating_scan_arrays(
            n_frames=n_frames,
            scan_stop=scan_stop,
            grating_low=grating_low,
            grating_high=grating_high,
            stripe_width_px=stripe_width_px,
            split_x=split_x,
            grating_axis=grating_axis,
        )

        for frame, row in zip(frames, metadata):
            self.save_bmp_24bit(frame, out_dir / row["filename"])

        write_metadata(out_dir / "metadata.csv", metadata)
        return frames, metadata


def write_metadata(path, rows):
    if not rows:
        return

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


_DEFAULT_GENERATOR = CalibrationFrameGenerator()


def clamp16(x):
    return CalibrationFrameGenerator.clamp16(x)


def pack_meadowlark_dvi_16bit_to_rgb(value16_img):
    return CalibrationFrameGenerator.pack_meadowlark_dvi_16bit_to_rgb(value16_img)


def make_square_grating(width, height, low, high, stripe_width_px, axis="x"):
    return _DEFAULT_GENERATOR.make_square_grating(
        width=width,
        height=height,
        low=low,
        high=high,
        stripe_width_px=stripe_width_px,
        axis=axis,
    )


def make_frame(
    mirror_value,
    grating_low,
    grating_high,
    stripe_width_px,
    split_x=256,
    grating_axis="x",
):
    return _DEFAULT_GENERATOR.make_frame(
        mirror_value=mirror_value,
        grating_low=grating_low,
        grating_high=grating_high,
        stripe_width_px=stripe_width_px,
        split_x=split_x,
        grating_axis=grating_axis,
    )


def save_bmp_24bit(frame16, path):
    return CalibrationFrameGenerator.save_bmp_24bit(frame16, path)


def linspace16(start, stop, n):
    return CalibrationFrameGenerator.linspace16(start, stop, n)


def generate_constant_mirror_scan(
    out_dir,
    n_frames,
    scan_start,
    scan_stop,
    mirror_value=32768,
    grating_low=0,
    stripe_width_px=8,
    split_x=256,
    grating_axis="x",
):
    return _DEFAULT_GENERATOR.generate_constant_mirror_scan(
        out_dir=out_dir,
        n_frames=n_frames,
        scan_start=scan_start,
        scan_stop=scan_stop,
        mirror_value=mirror_value,
        grating_low=grating_low,
        stripe_width_px=stripe_width_px,
        split_x=split_x,
        grating_axis=grating_axis,
    )


def generate_constant_grating_scan(
    out_dir,
    n_frames,
    scan_stop,
    grating_low=0,
    grating_high=65535,
    stripe_width_px=8,
    split_x=256,
    grating_axis="x",
):
    return _DEFAULT_GENERATOR.generate_constant_grating_scan(
        out_dir=out_dir,
        n_frames=n_frames,
        scan_stop=scan_stop,
        grating_low=grating_low,
        grating_high=grating_high,
        stripe_width_px=stripe_width_px,
        split_x=split_x,
        grating_axis=grating_axis,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate Meadowlark 512x512 DVI 16-bit calibration BMP frames."
    )

    parser.add_argument(
        "--mode",
        choices=["constant_mirror", "constant_grating"],
        required=True,
        help="Which calibration frame series to generate.",
    )

    parser.add_argument(
        "--out",
        type=str,
        default="slm_calibration_frames",
        help="Output folder.",
    )

    parser.add_argument(
        "--n",
        type=int,
        default=16,
        help="Number of calibration frames.",
    )

    parser.add_argument(
        "--scan-start",
        type=int,
        default=0,
        help="Lower end of scan range for constant_mirror mode.",
    )

    parser.add_argument(
        "--scan-stop",
        type=int,
        default=65535,
        help="Upper end of scan range.",
    )

    parser.add_argument(
        "--mirror",
        type=int,
        default=32768,
        help="Mirror brightness for constant_mirror mode.",
    )

    parser.add_argument(
        "--grating-low",
        type=int,
        default=0,
        help="Low value of the binary grating.",
    )

    parser.add_argument(
        "--grating-high",
        type=int,
        default=65535,
        help="High value of the binary grating for constant_grating mode.",
    )

    parser.add_argument(
        "--stripe-width",
        type=int,
        default=8,
        help="Stripe width in pixels.",
    )

    parser.add_argument(
        "--split-x",
        type=int,
        default=256,
        help="x pixel where left mirror region ends and right grating region begins.",
    )

    parser.add_argument(
        "--axis",
        choices=["x", "y"],
        default="x",
        help="'x' gives vertical stripes; 'y' gives horizontal stripes.",
    )

    args = parser.parse_args()
    out_dir = Path(args.out)

    if args.n <= 0:
        raise ValueError("--n must be positive")

    if args.mode == "constant_mirror" and args.scan_start > args.scan_stop:
        raise ValueError("--scan-start must be <= --scan-stop for constant_mirror mode")

    if args.mode == "constant_mirror":
        generate_constant_mirror_scan(
            out_dir=out_dir,
            n_frames=args.n,
            scan_start=args.scan_start,
            scan_stop=args.scan_stop,
            mirror_value=args.mirror,
            grating_low=args.grating_low,
            stripe_width_px=args.stripe_width,
            split_x=args.split_x,
            grating_axis=args.axis,
        )
    elif args.mode == "constant_grating":
        generate_constant_grating_scan(
            out_dir=out_dir,
            n_frames=args.n,
            scan_stop=args.scan_stop,
            grating_low=args.grating_low,
            grating_high=args.grating_high,
            stripe_width_px=args.stripe_width,
            split_x=args.split_x,
            grating_axis=args.axis,
        )

    print(f"Done. Wrote frames to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
