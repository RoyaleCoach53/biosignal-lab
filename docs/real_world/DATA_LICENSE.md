# Data attribution and publication boundaries

The derived reports and figure contain information from the
[PhysioNet EEG Motor Movement/Imagery Dataset 1.0.0](https://physionet.org/content/eegmmidb/1.0.0/),
available under the [Open Data Commons Attribution License v1.0](https://physionet.org/content/eegmmidb/view-license/1.0.0/).
Dataset citation: Schalk, G. (2009), DOI [10.13026/C28G6P](https://doi.org/10.13026/C28G6P).
Instrumentation citation: Schalk et al. (2004), BCI2000, IEEE TBME 51(6):1034–1043.

Code and synthetic fixtures are MIT licensed. Human recordings retain their
dataset terms; this repository does not relicense them. The license URI and
dataset attribution accompany machine-readable reports and the report figure.

Raw EDFs, annotation streams and personal EDF header fields are not redistributed.
Download scripts fetch only the pinned official subset, into an outside-repository
cache, after explicit `--download`. Hashes establish byte identity, not consent,
hardware accuracy, signal quality or physiological validity. Future datasets must
be separately checked for access and redistribution terms before use.
