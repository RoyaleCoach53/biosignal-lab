# Beta session and feedback form

Blank template — **no real participant results recorded**. Copy locally or use
the [GitHub beta form](../../.github/ISSUE_TEMPLATE/beta_feedback.yml). Public
issues are public; provide only information you are willing to disclose.

## Session/build

- Optional anonymous slot: B01/B02/B03/B04/B05 (maintainer assignment, not a name):
- Date; protocol BETA-1.0; full build commit SHA:
- Dataset-manifest SHA-256; tutorial runner SHA-256:
- OS family/version and Python version (omit hostname, username and account paths):
- Prior Python/EEG familiarity (optional short description):
- Installation command/extra and fresh environment confirmed:
- Outcome: completed / incomplete / declined / blocked:

## Task outcomes

| Task | Complete / blocked / not attempted | Help required? | Optional active minutes; downloads separate |
| --- | --- | --- | --- |
| Install and launch | | | |
| Synthetic signal and PSD | | | |
| Quality/candidate review | | | |
| JSON/HTML/config export | | | |
| Public EEG first run | | | |
| Public EEG offline rerun | | | |
| Keyboard/150% zoom | | | |

## Reproduction

- Official recording ID/hash (no recording attachment):
- Metadata: channels / sampling Hz / seconds / grid Hz:
- Matched-reference pass or failure, exact error keys and unchanged tolerances:
- Source/protocol hashes match the assigned build? If not, retain as a mismatch:
- Offline rerun result; no unsupported exclusions or settings changes:
- Versions from the redacted summary (omit local paths/full logs):

## Understanding and usability

1. In your own words, distinguish µV, µV²/Hz and µV².
2. What does processing change? Why does a low post-notch fraction not prove clean raw data?
3. Why does agreement with matched MNE settings not establish clinical validation?
4. What did you expect a confusing control or warning to mean?
5. What blocked you, what workaround/help was needed, and what one improvement would help most?
6. Could you navigate by keyboard and read the figure at 150% zoom? Name the control/legend.

Rate ease of finding the next action and clarity of warnings separately from
1 (very difficult/unclear) to 5 (very easy/clear), or choose not to answer.
These are descriptive responses, not a validated usability scale.

## Sharing choice

- I reviewed my response for private paths, credentials, identifiers and human recordings:
- I understand a GitHub issue is public; permission to quote feedback is **not** implied:
- May the maintainer include a de-identified summary in the aggregate beta report? yes / no:
- Optional separate permission for an exact public quote: no by default; request later:

Report security defects privately through [SECURITY.md](../../SECURITY.md).
Do not attach raw EDFs, waveform CSVs, medical information or identifying screenshots.
