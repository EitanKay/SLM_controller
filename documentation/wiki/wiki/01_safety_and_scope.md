# 01 — Safety, scope, and non-negotiable warnings

## Safety

This wiki does not replace lab laser-safety training. Treat the SLM setup as an active laser experiment, not just a computer display.

Minimum reminders:

- Use correct laser goggles for the wavelength in use.
- Keep beams horizontal and at a controlled height.
- Use beam blocks and avoid open beam paths.
- Do not put reflective tools, jewelry, phones, or watches near the beam.
- Do not inspect beams directly.
- Reduce laser power during alignment when possible.

## Device-care warnings

- Do not touch the SLM coverglass.
- Do not clean the SLM casually.
- Do not use acetone on the SLM.
- Do not use pressurized air/nitrogen on the SLM head; bond wires can be damaged.
- Keep the aperture covered when the SLM is not in use, if the current mount allows it.

## Scope of the current system

This system is intended for open-space spatial beam shaping and camera-based verification.

Currently documented as routine / semi-routine:

- displaying phase masks;
- beam steering with a linear phase ramp;
- selecting diffraction orders with an iris;
- generating approximate HG/TEM modes;
- camera-based output verification;
- measuring/calibrating a wavelength-specific LUT.

Currently **not** treated as solved:

- robust fiber coupling of generated modes;
- closed-loop camera-feedback holography;
- transferable calibration to a new wavelength or new optical layout;
- arbitrary complex-field generation without restrictions.

## Wavelength and LUT dependence

The LUT is not a decoration. It determines how input pixel values map to SLM drive values and therefore to optical phase.

Do not assume that:

- a LUT measured at 635 nm is valid at 737 nm;
- a LUT measured with one polarization/temperature/optical path is valid after major changes;
- a mask that looks numerically correct produces the intended optical phase response;
- the zero order will disappear.

Before an important experiment, record:

| Field | Value |
|---|---|
| Date | TODO |
| Wavelength | TODO |
| LUT file | TODO |
| WFC file | TODO |
| Laser power at SLM | TODO |
| Polarization setting | TODO |
| Camera exposure/gain | TODO |
| Git commit | TODO |
| Validation pattern | TODO |
| Validation result | TODO |
