# 11 — Open questions and future work

This page is for things that are not solved. Keeping them explicit is better than letting the next student rediscover them.

## Open questions

| Question | Current status | Suggested next step |
|---|---|---|
| How good is the 737 nm LUT? | TODO: validate final result | Compare old/new LUT with grating/vortex/HG tests |
| Is the WFC file meaningful? | Unknown / likely needs verification | Record current WFC, test flatness/order quality |
| What is the best carrier grating period? | Operational but not finalized | Sweep ramp frequency and record order separation/efficiency |
| Can generated HG modes couple into fiber? | Not solved | Review MMF/GRIN/fiber coupling options, then test HG10 first |
| Can camera-feedback holography improve modes? | Future work | Implement measured-output feedback loop |
| What mode-quality metric should be standard? | Not finalized | Choose overlap/fit/correlation metric using raw camera data |
| Is the offline GUI robust on a fresh PC? | Needs final validation | Test packaged zip on a clean lab machine |

## Recommended future projects

### 1. Fiber coupling study

Determine whether generated modes can be coupled into a suitable multimode fiber and how stable the modal content remains.

Minimum useful test:

1. Generate HG10 in open space.
2. Image before fiber.
3. Couple into candidate MMF.
4. Image output.
5. Compare orientation, lobe contrast, and stability.

### 2. Camera-feedback holography

Close the loop:

```text
generate hologram → display → measure output → update hologram → repeat
```

This may improve robustness when the optical system differs from the ideal Fourier model.

### 3. Final calibration benchmark

Create a short standard benchmark that every future LUT must pass:

- grating efficiency check;
- vortex null visibility;
- HG10 lobe separation/contrast;
- repeatability after restart;
- fixed camera settings.

## Handover note to future user

Start simple. If a simple grating does not behave, the problem is almost never the HG algorithm.
