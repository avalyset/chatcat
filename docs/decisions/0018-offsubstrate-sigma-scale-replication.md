# ADR 0018: Off-substrate replication of the σ-scale seed-variability finding

## Status
Proposed — pre-registration. Nothing built, nothing run. Measurement
thresholds and the window-unit mapping are locked in this document BEFORE any
training run. chatcat Track 1, Ledd 1 (off-substrate evidence).

## Context

The paper's §3.5 finding is not "climb-then-slide is a robust phenomenon." It is
that **measurability itself is seed-variable**: the population of per-seed σ_init
straddles a noise floor σ* = T/(2√2) = 0.0326, so the gate verdict wanders with the
seed draw rather than reflecting a real batch-scale difference (Brown–Forsythe
p=0.99 on ADR 0013's resampling). That is the contribution replicable off-substrate.

What CANNOT be replicated off-substrate, and is therefore OUT of scope: the `cts`
climb/slide *test* against T. T = 0.0922 is chatcat's own climb/slide threshold,
anchored to the SimCat substrate. No external RL benchmark carries a T. Testing an
external climb/slide against chatcat's T — or inventing a T for the external domain
— is the fabricated-fixture failure mode. Prohibited.

Disk-verified portability (CC, this session):
- σ_init construction (inter-update SD of the rolling-100 smoothed return over the
  ep_init window) ports without redefinition — a pure function of the per-episode
  return series. Verdict (b): ports.
- climb/slide window *form* ports with ONE explicit mapping: the window unit is
  *update* (PPO iteration) in chatcat (freeze_seed_summary.py:105,110,111), and RL
  Zoo `monitor.csv` is *episode*-indexed. Verdict (b): ports with defined mapping.
  Nothing depends on SimCat-tick or Box(7,) semantics.

## Decision

Replicate the §3.5 σ-scale seed-variability finding on an independent codebase and
task: self-generated multi-seed CleanRL `ppo_continuous_action` runs (same algorithm
as the chatcat substrate — strongest object match, auth-free, reproducible).
Pre-registered question:

> Does the within-window σ_init population on an independent PPO continuous-control
> task exhibit the same seed-wander-over-a-floor structure the paper reports on the
> chatcat substrate — i.e. does σ straddle a noise floor such that a fixed
> threshold's separability verdict is seed-variable rather than batch-determined?

Needs NO external T-fixture. Asks whether the σ-scale *behaves* the same way, not
whether it crosses an imported threshold.

## Pre-registered predictions (locked before any run)

- **P1 (primary).** The per-seed σ_init population on the external task has a
  floor-straddle structure consistent with the chatcat substrate: σ does not cleanly
  separate into "resolvable" vs "unresolvable" regimes but forms a continuum around
  a floor. Operationalised: report the σ population, its median, its MAD, and its CV.
  **chatcat reference (disk-verified, seed_summary_frozen.csv, §3.5 population =
  ALL {6..20}, n=15): CV = 0.4837, median = 0.030381, MAD = 0.008632.** The chatcat
  median (0.030381) sits just below σ* = 0.03260 — the population straddles the floor,
  which IS the §3.5 finding. P1 holds if the external CV falls within [0.25, 0.75] —
  a band set around the chatcat CV wide enough to absorb the known fragility of
  CV=SD/mean here (two high seeds, 10=0.0785 and 14=0.0696, inflate mean and SD;
  the n=5 vs n=10 subpopulations span CV 0.38–0.74 by sample-size artefact alone).
  **Robustness co-primary: MAD/median ratio**, which is insensitive to those two
  seeds; report both. If neither the external CV nor MAD/median can be sensibly
  banded (e.g. external n too small), P1 is reported descriptively, not as pass/fail.
- **P2 (robustness).** Brown–Forsythe test for equality of σ_init variance across two
  independently-seeded external batches returns p > 0.05 — the same non-difference
  ADR 0013 found intrinsically. **Note on comparability (disk-corrected):** ADR 0013
  ran Brown–Forsythe on {6..10} vs {11..20} — n=5 vs n=10, UNEQUAL by construction
  (0013-resolution.md:30–35, W≈0.000159, p=0.9901). The external P2 uses two
  EQUAL-size batches by design; this is a deliberate difference from 0013's 5-vs-10
  split, not a replication of its exact setup. State it as such — do not claim the
  external test mirrors 0013's batch structure when it does not.
- **P3 (negative-result clause).** If the external σ population separates cleanly
  (bimodal, or CV far outside the band), that is a REAL answer: it bounds the finding
  to the chatcat substrate and is reported as such. Failure to replicate is
  publishable and is NOT rescued by re-picking the task or the window.

## Locked measurement thresholds (derive from anchors, not results)

- **Rolling window = 100 episodes.** Identical to chatcat's `ep_return_n_recent >=
  100` buffer-full criterion (freeze_seed_summary.py:84). Not tuned.
- **σ* = T/(2√2) = 0.0326** (disk-verified: T=0.0922 gate.py:32; σ* stated verbatim
  in 0013-resolution.md:22–23 and 0013-gate-verdict-stability.md:57–58 as 0.03260).
  On the external task σ* is a *reference line for shape comparison only*, NOT a
  pass/fail threshold — it is chatcat's floor, not the external task's. The external
  study reports the σ population and its CV; it emits NO PASS/FAIL. This is the
  firewall against the fabricated-T failure mode.
- **GATE_THRESHOLD = 2.0** is NOT used off-substrate (it is the cts ratio rule, out
  of scope here).

## Locked window-unit mapping (the one modelling decision; locked before run)

chatcat windows are in *update* units: ep_init = [buffer_full, buffer_full+50];
ep_peak = argmax±25; ep_final = last 50 (freeze_seed_summary.py:105,110,111). RL Zoo
/ CleanRL `monitor.csv` is episode-indexed.

**Locked choice: reconstruct update boundaries from the known rollout length**
(`n_steps` / batch size from the CleanRL config), NOT episode-index substitution.
Rationale: preserves the window's *temporal extent* (per unit of optimisation)
closest to the chatcat definition, which is what σ_init measures. Episode-space would
change the temporal extent and is therefore rejected NOW, not after seeing which
yields the cleaner result. (Post-hoc mapping selection would be the A2 violation.)

## Seed generation (the real cost, stated plainly)

Free RL Zoo repo has ONE seed per (algo, env) — the 16 monitor.csv are parallel
VecEnv workers of a single seed (shared t_start, verified). The σ-scale finding needs
a σ *population* over independent seeds. Therefore:

- Generate N ≥ 15 independent-seed CleanRL `ppo_continuous_action` runs on one
  continuous-control task (HalfCheetah-v4 or Hopper-v4), deterministic seeding,
  per-episode return logged to local CSV (NOT wandb — no account required).
  N=15 matches ADR 0012/0013's escalation N for comparability.
- GPU compute not yet spent on this track. A real resource commitment, not a
  download.

## Scope firewall (what this ADR does NOT do)

- Does NOT run the cts climb/slide test off-substrate (no external T).
- Does NOT claim convergent validity against AdaStop / rliable / any A-vs-B fixture
  (the gate is not an A-vs-B comparator; CC verified this three ways this session).
- Does NOT touch the chatcat repo's frozen analysis (SCX59) or the arXiv bundle.
- Does NOT gate the arXiv submission — that remains gated ONLY on the cs.LG
  endorsement. This is a second-paper / method-generalisation artefact.

## Consequences

- Clean replication (P1+P2 hold) converts the paper from single-substrate case study
  to a method with external evidence — the Ledd-1 visittkort for Simula.
- Failure to replicate (P3) bounds the finding honestly and is itself reportable.
- Either outcome IS the off-substrate evidence the original plan called Ledd 1 —
  correctly re-specified as a σ-scale replication study, not a fixture-match.

## Open decision for Eirik (NOT pre-registrable by chat)

Sequencing vs. compute: this costs GPU hours on a track behind the Gundersen
endorsement in priority. Starting now vs. after the arXiv credential lands is a
resource-ordering call. Both defensible; the ADR is ready either way.

## References
- Paper §3.5 (σ-scale seed-variability); ADR 0012 (N=15 escalation); ADR 0013
  (verdict-stability resampling, Brown–Forsythe p=0.99, σ* = 0.0326).
- freeze_seed_summary.py:82–124 (climb/slide + σ_init construction, disk-read).
- CleanRL `ppo_continuous_action` (the chatcat RL substrate's own algorithm).
