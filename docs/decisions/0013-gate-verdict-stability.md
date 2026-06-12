# ADR 0013: Gate-verdict stability over the 15 frozen seeds — pre-registration

## Status

**Proposed (pre-registered, not yet executed).** This document locks the
methodology AND the numeric decision bands for a resampling analysis of
the criterion-validity gate's verdict over the existing 15 main-run
seeds — **before** the real resampling distribution is read. The
analysis itself (`paper/analysis/gate_distribution.py` on the real
frozen summary) is a separate step, executed only after Eirik
explicitly triggers it.

This is the same circularity guard as ADR 0010 §2.3 (anchoring seed:
measure scale, never read the seed's own outcome) and ADR 0011/0012
(lock the criterion before the data that resolves it). Here the
specific trap is: the gate verdict's PASS-rate is itself a number, and
choosing the "stable vs variable" bands after seeing that PASS-rate
would be post-hoc rationalisation. The bands (§4) are therefore fixed
now, from differential-noise-floor logic, with a stated prediction.

## Context

ADR 0011 ran the criterion-validity gate on the original five seeds
`{6..10}`: median `sigma_init` = 0.023918, `T/sigma_diff` = 2.7257,
**PASS**. ADR 0012 ran it on ten new seeds `{11..20}`: median
`sigma_init` = 0.036166, `T/sigma_diff` = 1.8027, **FAIL** — and per
its gate-STOP, stopped before computing the climb-readout (CTS) for
`{11..20}`.

So the gate **passed on one seed batch and failed on the other, under
identical training configuration.** That leaves a sharp question ADR
0012 did not answer and deliberately did not let more compute paper
over: **is the gate verdict stable, or is it itself a function of which
seeds you happen to draw?** ADR 0012 named this (Path 3) but explicitly
did not pre-register it.

This ADR pre-registers it as a **budget-free reanalysis** of the 15
seeds already on disk — no retraining. The substrate is the committed
`paper/analysis/seed_summary_frozen.csv` (one row per seed; `sigma_init`
for all 15; CTS computed for `{6..10}`, `gate-gated` sentinel for
`{11..20}` per ADR 0012's gate-STOP).

## Pre-commitment — what this ADR locks BEFORE the real run

### 1. Frozen inputs (no retraining)

- **The only input** is the 15 per-seed `sigma_init` values in
  `seed_summary_frozen.csv` (the gate operates on `sigma_init`; it does
  not read CTS, so the gate-gated `{11..20}` CTS values are never
  touched by this analysis).
- **Revised buffer-full `ep_init` window** (ADR 0011 §1: first 51
  updates with `ep_return_n_recent ≥ 100`) — the window `sigma_init`
  was measured over. Unchanged.
- **T = 0.0922** (ADR 0010 Precision 3). Unchanged, not re-derived.
- **`sigma_diff` = median(per-seed `sigma_init`) × √2.** Unchanged.
- **Gate threshold = 2.0**: a subset PASSES iff `T / sigma_diff ≥ 2.0`,
  equivalently iff `median(sigma_init) ≤ T / (2√2) = 0.03260`. Call
  `sigma* = 0.03260` the **differential-noise floor** — the median
  `sigma_init` at which the gate is exactly on its threshold.

### 2. Resampling scheme (locked)

For resample sizes **k ∈ {5, 10, 15}** over the 15 seeds:
- **Exhaustive choose-k** (without replacement) when `C(15, k) ≤ 10000`
  — true for k=5 (3003), k=10 (3003), k=15 (1). The full enumeration is
  exact, not sampled.
- **Bootstrap B = 10000** (with replacement) only if a future k makes
  `C(15, k) > 10000` (not the case for the locked k-set; specified for
  completeness so the scheme is fully determined).
- Per k, report: PASS-rate (fraction of subsets with `T/sigma_diff ≥ 2.0`),
  ratio quantiles {2.5, 25, 50, 75, 97.5}, and fraction of draws on each
  side of 2.0. The headline statistic is **PASS-rate at k=5** (the
  smallest, most draw-sensitive resample, and the size of each original
  ADR batch).

### 3. Variance partition (descriptive, locked)

- Between-seed spread of `sigma_init` across all 15 (mean, SD, range).
- `{6..10}` vs `{11..20}` scale equality via **Brown-Forsythe**
  (median-centred Levene). Reported as a descriptive scale-equality
  check with its W statistic and p-value — **not** a hypothesis "result"
  the paper claims; it quantifies the ~50% median-`sigma_init`
  discrepancy ADR 0012 flagged.

### 4. Pre-registered decision bands on PASS-rate at k=5 (LOCKED before data)

The gate is a **binary** validity classifier. Its verdict is "stable"
to the extent that resampling reproduces the same verdict. The bands
below map the k=5 PASS-rate to a stability verdict.

**Bands: W = 0.20, X = 0.80.**

- **PASS-rate at k=5 ≥ X = 0.80** → **gate stably PASSES.** The seed
  population's `sigma_init` mass sits clearly below the floor `sigma*`
  for the large majority of draws; the N=15 FAIL was an unlucky draw
  dominated by the high-`sigma` escalation seeds. **The phenomenon
  question reopens** (the gate is valid, so climb-then-slide robustness
  can be re-measured against a criterion that holds).

- **PASS-rate at k=5 in [W, X) = [0.20, 0.80)** → **gate verdict is
  intrinsically seed-variable.** The population straddles the floor
  `sigma*` such that the median's position — and hence the verdict —
  depends on which seeds are drawn. **This is the earned, quantified
  form of "measurability is seed-variable":** a real endpoint, not a
  call for more compute. The midtbånd-as-endpoint principle from ADR
  0012 §4 applies — more seeds do not resolve a verdict that is a
  property of the draw.

- **PASS-rate at k=5 < W = 0.20** → **gate reliably FAILS.** Mass sits
  clearly above the floor for the large majority of draws; ADR 0010's
  F3 conclusion (climb-then-slide not robust against a well-posed
  criterion) holds, since the criterion is reliably noise-dominated.

**Justification of W and X from differential-noise-floor logic (not
post-hoc):** The gate passes iff a draw's `median(sigma_init) ≤ sigma*
= 0.03260`. "Stably one-sided" means the draw lands on the same side of
`sigma*` for the large majority of draws. We take "large majority" =
**4/5 = 0.80**, the robustness bar already locked in ADR 0010 (M ≥ 4/5
for CTS robustness) — reused here for verdict-reproducibility rather
than invented for this ADR, so the threshold is inherited, not chosen
to fit. **W = 0.20 is its mirror** (stably-FAIL is the symmetric
complement of stably-PASS). The `[0.20, 0.80)` interior is exactly the
regime where the population mass straddles `sigma*` and the verdict is
a draw-artifact.

### 5. Pre-registered prediction (stated before the real run)

Derived only from the two **already-committed** batch medians (ADR
0011: `{6..10}` median 0.023918, below `sigma*`; ADR 0012: `{11..20}`
median 0.036166, above `sigma*`) — NOT from the unread resampling
distribution:

> One batch sits clearly below the floor and the other clearly above,
> and the 15-seed pool mixes 5 low-`sigma` with 10 high-`sigma` seeds.
> A k=5 draw's median therefore flips across `sigma*` depending on how
> many low-`sigma` seeds it happens to contain. **We predict the k=5
> PASS-rate falls in the middle band [0.20, 0.80) → "intrinsically
> seed-variable."** If instead it lands ≥ 0.80 or < 0.20, the gate is
> stably one-sided and we were wrong about the mixing — which is itself
> the informative outcome the pre-registration is built to accept.

## Discipline

- Method + bands + prediction locked here, BEFORE the real
  `gate_distribution.py` run on `seed_summary_frozen.csv`.
- `gate_distribution.py` refuses real data without an explicit
  `--i-have-the-trigger` flag; a synthetic `--smoke-test` mode
  exercises the code without reading real values. The real run waits
  for Eirik's explicit trigger.
- **The paper's §3 Results claim is NOT to be edited until this ADR
  resolves.** The current §3 reports the N=15 gate-FAIL and the
  borderline as-is; whether that framing changes depends entirely on
  which band §4 lands in, and that must not be pre-empted.
- No retraining. The 15 frozen seeds are the entire input. Any
  escalation to new seeds would be a separate ADR with its own
  pre-registration (ADR 0012's bar).
- Negative / middle-band outcomes are real answers, equal in standing
  to a "gate stable" outcome.

## Gate (resolution of this ADR)

ADR 0013 is **resolved** when `gate_distribution.py --i-have-the-trigger`
has been run on the frozen summary and the resolution document records:
the k=5/10/15 PASS-rates and ratio quantiles, the Brown-Forsythe W/p,
which of the three §4 bands the k=5 PASS-rate fell in, and the
consequent disposition of the phenomenon question and the paper's §3.
The decision rule is already fixed; resolution only reads which band
the locked statistic fell in.
