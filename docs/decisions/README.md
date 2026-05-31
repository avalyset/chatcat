# Architectural Decision Records

This directory tracks chatcat's substantive architectural and methodological
decisions. Each ADR is committed once and amended in-place with a Resolution
section when the deferred evidence lands. Statuses are mirrored from each
file's own Status block; dates are the add-commit date in git
(`git log --diff-filter=A --format='%ci' -- <file>`).

| # | Title | Status | Date | Tracks |
|---|---|---|---|---|
| [0001](0001-litterbox-first.md) | Litterbox first | Accepted | 2026-05-07 | Simulator-first, before any real cat. |
| [0002](0002-self-play-research-track.md) | Self-play research track for emergent cat-communication strategies | Proposed (target: v0.2+) | 2026-05-07 | RL against SimCat; three mandatory safeguards (sim-to-real validation, continuous personality sampling, real-CSS anchoring); reward spec `engagement_minutes − α·max_CSS − β·opt_outs`. |
| [0003](0003-habituation-calibration.md) | Habituation rate values are placeholders pending real-cat data | Accepted (limitation, v0.1 onward until v0.4) | 2026-05-07 | Documents that the 0.005–0.015 habituation range is plausible-but-unvalidated; calibration deferred to v0.4 real-cat work. |
| [0004](0004-state-machine-flicker-investigation.md) | State Machine Flicker Investigation | Investigation complete. Not yet resolved. | 2026-05-08 | First instance of the "invariant in one of two paths" defect class (CSS computed differently in agent vs ethics-monitor); fixed in commits, ADR pending. |
| [0005](0005-baseline-interpretation.md) | Baseline interpretation — archetype collapse and two-pair clustering | Documented finding; hypothesis verified by ADR 0006. | 2026-05-12 | The five named archetypes appear to collapse onto ~2 latent behavioural axes plus anxious_skeptic as a separate cluster; verification deferred to 0006. |
| [0006](0006-continuous-sampling.md) | Continuous Feline Five sampling — methodology pre-commitment | Resolved (2026-05-30) | 2026-05-12 | Methodology pre-committed before any data existed; N=1000 uniform-cube sampling run executed and resolved. Effective dimensionality ~2–3, confirming ADR 0005's hypothesis. |
| [0007](0007-reward-calibration.md) | Reward calibration for the ADR 0002 self-play track | Resolved (2026-05-30) | 2026-05-30 | ADR 0002's default reward parameters are structurally degenerate; pre-registered grid scan documents the failure; closed negatively on the form-choice question. |
| [0008](0008-reward-baseline-normalization.md) | Baseline-normalised reward for the ADR 0002 self-play track | **Resolved: DOES_NOT_RESOLVE** (2026-05-31) | 2026-05-31 | Three training runs (one against the pre-0009 env, one against the corrected env, one LR-stability ablation) — all NON_TRIVIAL but climb-and-slide. env-bug and PPO-instability ruled out; reward structure confirmed insufficient on its own. |
| [0009](0009-ethics-enforcement-point.md) | Ethics enforcement point — `capIntensityForRetreat` is bypassed by the RL path | Resolved (2026-05-31) | 2026-05-31 | Found while declining to resolve 0008 against contaminated artefacts. Hard welfare invariant `capIntensityForRetreat` was only applied inside `policy.ts:84`; the RL path bypassed it. Fix: `EthicsMonitor.enforce()` as single enforcement gate on every action path. |

## Conventions

- **Pre-registration discipline.** When an ADR locks methodology or success
  criteria before the evidence that resolves it exists, those constraints
  are frozen — editing them after seeing a result is post-hoc rationalisation
  and invalidates the ADR. See 0005/0006 for the canonical version of the
  discipline; 0007/0008/0009 follow it.
- **In-place resolution.** An ADR is amended (status changed, Resolution
  section appended) in-place rather than written as a separate file, so the
  full pre-commitment + resolution trail lives in one document.
- **Negative resolutions are still resolutions.** ADR 0008's status is
  `DOES_NOT_RESOLVE` — the question was answered (baseline normalisation
  alone is informative but not stably learnable), even though the answer
  was not the hoped-for "this works". The work that produced the negative
  finding is itself a contribution; the next ADR (0010, when written)
  picks up from there without pre-empting design.
- **Pre-conditions on resolution.** ADR 0008's resolution depended on
  ADR 0009's fix — the original measurement was made against an env that
  lacked a welfare-invariant enforcement. The discipline of declining to
  resolve 0008 against the unreflected contamination is what surfaced 0009.

## Related repo conventions

- **Observations** live in [`../observations/`](../observations/) — devlog
  entries for what was actually run on a given day, separate from the ADRs
  that document the decisions and resolutions.
- **Citations** for behaviour parameters are in
  [`../../CITATIONS.md`](../../CITATIONS.md). ADRs do not duplicate them.
- **Ethics principles** are in [`../../ETHICS.md`](../../ETHICS.md);
  individual ADRs reference principles by section number rather than
  restating them.
