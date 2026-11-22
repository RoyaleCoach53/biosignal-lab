# Scientific methodology and validation protocol

This is a prospective validation protocol. It does not report measurements from
the unavailable v0.2 implementation. The recovered source must be checked against
the actual methods it implements before this document describes released behavior.

## Units and data provenance

Record the input source, license, signal units, sampling rate, channel types,
duration, reference convention, and any scaling performed on import. Separate
EEG, EMG, and auxiliary channels by explicit metadata where available. Check
timestamps against the declared sampling rate and disclose tolerances.

## RMS

For samples x[n], RMS is sqrt(sum(x[n]^2) / N). An unfiltered, zero-offset
sinusoid with peak amplitude A has RMS A / sqrt(2) over an integer number of
cycles. Its mean-square power is A^2 / 2. A mean-removed RMS and a raw RMS are
different measurements and must be named accordingly.

These are analytical targets. For example, A = 10 microvolts gives a theoretical
mean-square power of 50 microvolts squared; A = 100 microvolts gives a theoretical
RMS of approximately 70.710678 microvolts. These are not measured BioSignal results.

## Spectral estimation

For Welch PSD, explicitly record the window array or window convention, segment
length, overlap, FFT length, detrending, one-sided convention, scaling, and
averaging method. With voltage input and density scaling, PSD has units V^2/Hz.
Integration over a band has units V^2. Define integration and band-edge behavior,
including partial bins and adjacent-band boundaries.

Reference: [SciPy Welch documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html).

Match every setting and unit before comparing with MNE-Python. Record absolute
and relative differences and acknowledge shared numerical dependencies. Zero
padding changes the displayed frequency grid, not the underlying information
available in a short recording.

## Filtering

Record filter family, order, cutoffs, sampling rate, coefficients, direction,
padding, and excluded edge samples. Quantify passband attenuation and stopband
behavior. A requested analysis band must be compatible with the measured filter
response, including its transition region.

Forward-backward filtering changes the overall frequency response relative to
one forward pass. Short inputs and boundaries need explicit handling. Assess
EEG and EMG preprocessing separately rather than assuming one default fits both.

References: [SciPy SOS forward-backward filtering](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.sosfiltfilt.html),
[MNE background on filtering](https://mne.tools/stable/auto_tutorials/preprocessing/25_background_filtering.html).

## Sampling, missing data, and quality

Test invalid and nonfinite sampling rates, frequencies at and above Nyquist,
insufficient frequency coverage, irregular timestamps, duplicate timestamps,
gaps, NaNs, infinities, and short or empty signals. No interpolation across a
long gap should occur without a documented policy. Explicitly distinguish
unavailable values from zero power.

For quality detection, test deterministic flatlines, clipping, discontinuities,
and synthetic interference alongside clean controls. Record thresholds, window
sizes, expected flags, and false positives. Synthetic behavior alone does not
establish sensitivity or specificity on human recordings.

## Reporting

Every validation result should identify the source commit, environment, input
hash, parameters, analytical or reference target, tolerance, measured value,
error, and pass/fail outcome. Keep original and processed signal measurements
separate. Publish failures and unresolved concerns as well as successes.
