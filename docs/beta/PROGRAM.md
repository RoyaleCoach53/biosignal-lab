# Five-person independent beta program

Protocol **BETA-1.0**, designed 2026-11-23. Status: **planned; zero participants
enrolled and zero independent sessions completed**. Maintainer/CI execution is
engineering evidence and never fills an independent tester slot. No clinical or
patient study, compensation, endorsement or successful adoption is claimed.

## Questions and recruitment

Can five people install the selected build, complete the synthetic exercise,
explain units/warnings and reproduce the public-EEG checks without maintainer
coding help? What blocks them? Recruit adults who did not implement these changes,
ideally from different teaching/research settings. Five is a small convenience
usability sample, not a representative survey or scientific validation cohort.

Outreach is **not authorized yet**. The owner must approve each destination and
message before invitation. Participation is voluntary; stopping is allowed and
is recorded as incomplete rather than erased. Collect no patient data, private
contact details, affiliation, demographic/health data or raw computer logs.
Public GitHub feedback is optional; a tester may give the maintainer a redacted
response privately instead. Do not promise confidentiality for public issues.

| Planned slot | Desired perspective/coverage | Current status |
| --- | --- | --- |
| B01 | Student new to signal processing; Windows | Unassigned; not invited |
| B02 | Student comfortable with Python; Linux | Unassigned; not invited |
| B03 | EEG researcher; independently inspect parameter/reference assumptions | Unassigned; not invited |
| B04 | Student/researcher testing keyboard navigation, zoom and clarity | Unassigned; not invited |
| B05 | Researcher/educator reproducing the public EEG exercise; preferably another setting | Unassigned; not invited |

These are coverage targets, not invented people or eligibility quotas. macOS may
be tested as exploratory coverage but must not be described as already supported
by the Windows/Linux CI evidence.

## Freeze the build before the first session

The maintainer records the adoption PR's **full head SHA**, protocol BETA-1.0,
dataset-manifest SHA-256 and exact tutorial commands in [the session form](FEEDBACK.md).
All five use that same commit; `0.3.0` alone is insufficient because this branch
retains the published version string. Checkout with `git checkout --detach FULL_SHA`.
Store updates as protocol amendments; do not silently change settings or results.
Never change the immutable v0.3.0 release to repair beta failures.

Record each attempt once. If a participant retries after a fix, retain the first
failure and link a second session to a new build SHA; do not pool builds or replace
unfavorable results. Participants may stop any task without penalty.

## Session instructions (estimated 35–45 minutes plus downloads)

This is a proposed budget, not an observed completion time. Start a timer only
when the participant is ready; record installation/download time separately.

1. **Setup:** fresh clone and isolated environment. Record OS/Python, full commit,
   installation choice and whether help was needed. Follow [Quick Start](../QUICK_START.md)
   but use the frozen beta checkout instead of cloning the release again.
2. **Synthetic exercise:** keep EEG/250 Hz/30 s/eight channels/seed 42. Explore
   signal/PSD, inspect a candidate, export JSON/HTML/configuration. Explain µV,
   µV²/Hz, µV², raw versus processed and why post-notch power is not acquisition QC.
3. **Offline check:** `python tools/first_run_check.py --require-app --output local-results/beta-first-run.json`.
   Expect `passed: true`, two sample hashes verified, finite/nonnegative PSD.
   Optional EDF availability may be false until tutorial dependencies are installed.
4. **Public EEG:** install `.[tutorial]`; run the exact [EEG lesson](../EEG_TUTORIAL.md)
   with S001R01/channel 0 and an outside-checkout cache. Run it again offline.
   Inspect PSD/band units and matched-reference errors. Do not add files/channels
   or change tolerances to turn a failure into a pass.
5. **Accessibility/understanding:** use keyboard navigation and 150% zoom, report
   any inaccessible control, unreadable legend or confusing warning. Explain the
   native-padding non-equivalence and the clinical-validation boundary in your own words.
6. **Feedback:** complete [the form](FEEDBACK.md). Attach only redacted JSON summaries
   if comfortable. Do not submit EDFs, waveforms, raw headers, full paths or credentials.

Use a fresh terminal after stopping Streamlit with Ctrl+C. The commands assume
the virtual-environment Python, not an unrelated system interpreter. Ask for help
when blocked and record it; the program measures assistance, not silent struggle.

## Predeclared success criteria and failure handling

Per session, record task completion, help required, optional stopwatch times,
errors and comprehension answers. A numerical reproduction passes only when file,
protocol and executable-source hashes match the assigned build; metadata is
64 channels/160 Hz/60 s/0.25 Hz grid; all unchanged reference tolerances pass;
and the offline rerun retains matching settings/hash/numerical results within
tolerances. Do not require image-byte equality across plotting versions.

Usability exit target: at least **4 of 5** complete the synthetic path without
maintainer coding help; all five attempts have outcomes and redacted feedback;
every critical privacy/correctness blocker is resolved or blocks expansion; and
every tester who reaches the EEG task reports a pass or a retained failure.
Report task-specific denominators; if fewer than five participate, say so and
leave the program incomplete. Publish counts and anonymized failure themes only
after owner/tester sharing approval; never invent confidence intervals or efficacy.

Severity: P0 data disclosure/unsafe destructive action; P1 materially wrong units,
silent wrong results or unreproducible fixed protocol; P2 installation/flow blocker;
P3 wording/accessibility polish. Stop affected tasks for P0/P1, use private security
reporting when appropriate, retain the build/evidence, and triage before recruiting
further people. No new official release follows automatically from a successful beta.

See [feedback](FEEDBACK.md), [reproduction issue](../../.github/ISSUE_TEMPLATE/reproducibility.yml),
[usability issue](../../.github/ISSUE_TEMPLATE/beta_feedback.yml) and [v0.4 priorities](../V0_4_PRIORITIES.md).
