# ADR 0013 Resolution — gate verdict is intrinsically seed-variable (middle band)

## Status

**Resolved 2026-06-12.** The gate-verdict-stability analysis pre-registered
in `0013-gate-verdict-stability.md` was executed against the frozen 15-seed
summary. The k=5 PASS-rate fell in the **pre-registered middle band
[0.20, 0.80)** → **gate verdict is intrinsically seed-variable.** The band
IS the verdict; no reinterpretation beyond it.

## What was run

- `gate_distribution.py --i-have-the-trigger` against
  `paper/analysis/seed_summary_frozen.csv` — the 15 on-disk main-run seeds
  ({6..20}), **no retraining**.
- Method frozen in the ADR 0013 stub, applied unchanged: revised
  buffer-full `ep_init` window (first 51 updates with
  `ep_return_n_recent ≥ 100`); **T = 0.0922**;
  **`sigma_diff = median(sigma_init) × √2`**; **gate threshold = 2.0**
  (PASS iff `T / sigma_diff ≥ 2.0`); exhaustive choose-k for k=5 and k=10
  (`C(15,5) = C(15,10) = 3003`), full-set single verdict for k=15;
  differential-noise floor **`sigma* = T / (2√2) = 0.0326`** (a subset
  PASSES iff its `median(sigma_init) ≤ sigma*`).
- The analysis operates on `sigma_init` only; it does not read CTS, so the
  `gate-gated` `{11..20}` CTS values (ADR 0012 gate-STOP) were never
  touched.

## Results (verbatim from the run)

**Brown-Forsythe (median-centred Levene), {6..10} vs {11..20} `sigma_init`
scale-equality:**

```
W = 0.00015896618323385528   (≈ 0.000159)
p = 0.9901318349247737        (≈ 0.9901)
median_orig = 0.023918
median_esc  = 0.036166
ratio_of_medians (esc / orig) = 1.5120829500794384   (≈ 1.5121)
```

**Ratio-distribution quantiles {2.5, 25, 50, 75, 97.5}:**

```
k=5  [exhaustive choose-k, C(15,5)=3003, 3003 draws]:
     q2.5 = 1.2233359958230854   q25 = 1.6711159158588083
     q50  = 2.145921636068585    q75 = 2.386705418999842
     q97.5 = 2.5600897363307813
k=10 [exhaustive choose-k, C(15,10)=3003, 3003 draws]:
     q2.5 = 1.414719915488183    q25 = 1.878987959345179
     q50  = 2.111689482093047    q75 = 2.25991802781426
     q97.5 = 2.413610692682734
k=15 [full-set, single verdict, 1 draw]:
     2.145921636068585 (all quantiles — single point)
```

**PASS-rate (fraction of draws with ratio ≥ 2.0):**

```
k=5  : 0.5734   (fraction below 2.0: 0.4266)
k=10 : 0.7063   (fraction below 2.0: 0.2937)
k=15 : 1.0000   (single full-set draw, ratio 2.1459 ≥ 2.0)
```

## Verdict

**k=5 PASS-rate = 0.5734, which lies in the pre-registered band
[0.20, 0.80).** This is the **middle band.** The pre-registered conclusion
(ADR 0013 stub §4, verbatim):

> **PASS-rate at k=5 in [W, X) = [0.20, 0.80)** → **gate verdict is
> intrinsically seed-variable.** The population straddles the floor
> `sigma*` such that the median's position — and hence the verdict —
> depends on which seeds are drawn. **This is the earned, quantified
> form of "measurability is seed-variable":** a real endpoint, not a
> call for more compute. The midtbånd-as-endpoint principle from ADR
> 0012 §4 applies — more seeds do not resolve a verdict that is a
> property of the draw.

The band IS the verdict. No reinterpretation beyond it.

## Two corroborating facts (mechanism, not reinterpretation)

1. **Brown-Forsythe p = 0.9901 — no detectable scale difference between
   the two batches.** The apparent jump in median `sigma_init`
   (0.023918 → 0.036166) is **seed wander across `sigma*`**, not a
   genuinely noisier second batch. The honest claim is therefore "the
   verdict depends on which seeds are drawn," **not** "batch 2 was
   noisier." (The ~50% median gap and the W≈0 / p≈0.99 scale-equality are
   not in tension: the medians moved because individual seeds land on
   either side of `sigma*`, while the overall spread of the two batches is
   statistically indistinguishable.)

2. **Slice-dependence made concrete.** ADR 0012's N=15 gate-FAIL
   (T/σ_diff = 1.80) was computed on the new `{11..20}` slice; the full
   `{6..20}` set gives **2.1459 — a bare PASS**. Same corpus, different
   slice, opposite verdict. The k=15 single-draw bare-PASS is itself an
   **unstable point estimate** sitting just above the 2.0 threshold — it
   is the instability made visible, **not** evidence that the phenomenon
   passes.

## Consequences

- The earned, quantified form of "measurability is seed-variable" now
  rests on **committed, reproducible artefacts** (`seed_summary_frozen.csv`
  + `gate.py` + `gate_distribution.py` + `test_gate.py`), closing the
  off-repo / non-reproducible gap that the raw `~/chatcat-rl-runs/`
  metrics left.
- **Paper §3 / §4 are to be updated in a SEPARATE step** to carry this
  claim. They are **not touched here**; this resolution only records the
  run and the band.
- **Prediction note.** The middle band was the ADR 0013 §5 prediction —
  but that prediction was derived from the already-published batch medians
  (which are themselves the run's own input), so it is **weakly protected**
  and is not where the methodological weight sits. The pre-registered
  **bands** (locked before the resampling distribution was read), not the
  prediction, are the commitment that makes this verdict non-circular.

## What this resolution does NOT do

- Does not re-run the analysis (the run is the one already executed).
- Does not edit the ADR 0013 stub, the paper, the frozen CSV, or any other
  file.
- Does not re-anchor T, K, `sigma*`, or the bands.
- Does not escalate to new seeds (any such escalation is a separate ADR
  with its own pre-registration, per ADR 0012's bar).
