# Integrated dependency review

This is a point-in-time automated advisory and compatibility review, not an
independent security certification or a guarantee against unknown vulnerabilities.

The initial final-review scan reported three advisory records for setuptools
81.0.0 (two distinct advisory identifiers). NeuroKit2 0.3.0 and 0.2.13 require
setuptools below 82, which conflicts with the available fixes. Official PyPI
metadata and checksum-verified distributions were inspected. The supported
NeuroKit2 0.2.12 release has no such dependency constraint and no `pkg_resources`
imports. The physiology extra now selects that release; setuptools is 84.2.1,
and the build-system minimum is 84.1. Normal dependency resolution and TLS/hash
verification were retained. Five peripheral integration regressions passed
again with NeuroKit2 0.2.12; `pip check` passed.

The remediated scan examined 124 installed distributions and returned zero known
advisory entries for the 122 distributions it assessed. Two entries were skipped:
the editable project (source reviewed separately) and the official CPU-tagged
PyTorch 2.15.0+cpu wheel, which the PyPI-backed auditor could not identify. A
separate explicitly pinned advisory query for upstream torch 2.15.0 returned
zero entries. That query does not independently audit CPU wheel binary contents,
native bundled components, GPU variants or future versions.

Both initial and remediated reports are preserved alongside the upstream torch
query. New dependencies must receive a fresh review rather than inheriting this
result. The container upgrades pip to at least the locally audited 26.3 before
installation, builds with patched setuptools, runs as UID 10001 and gives the
application a dedicated writable results directory. Final image behavior is
verified separately from advisory metadata.

The ASRpy compatibility investigation rejected an incompatible optional library;
no unverified ASR transformation, vendored patch or disabled verification was
introduced. Physical devices, hostile native-parser fuzzing, independent security
review and a legal review of all bundled notices remain separate acceptance work.
