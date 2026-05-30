# ADR 0006: Continuous Feline Five sampling — methodology pre-commitment

## Status
**Resolved (2026-05-30).** Methodology was pre-committed 2026-05-12 (this
file's original body, below) before any data existed. The continuous-sampling
run was executed 2026-05-30. The pre-registered prediction was tested against
the data and is reported in the Resolution section. The verification deferred
from ADR 0005 is now closed.

## Context

ADR 0002 mandates that v0.2 RL training samples continuously from the
full Feline Five trait space (Litchfield et al. 2017), not only from
the five named archetypes. The named archetypes are inspection presets,
not the training distribution.

ADR 0005 documented a hypothesis from the v0.1 baseline: that the five
named archetypes project onto approximately two latent behavioural
axes plus anxious_skeptic as a separate cluster, derived from L1
distance over per-archetype mean state-share vectors. Verification was
explicitly deferred to this ADR, because the N=5 preset basis is
inadequate for the dimensionality question and a richer dataset is
required.

This stub exists so that the analysis methodology for the
continuous-sampling run is fixed before the run is executed. Choosing
the metric after seeing the data would risk selecting whichever metric
happens to confirm ADR 0005's prior. Locking the constraints in
advance is the discipline that distinguishes a verification from a
post-hoc rationalisation.

---

## Methodology constraints (pre-commitment, locked 2026-05-12)

- **L1 distance over per-archetype mean state vectors is not adequate
  as the primary metric.** It was sufficient for the five-preset
  baseline (only five points to compare). With thousands of sampled
  trait vectors a pairwise distance matrix is the wrong shape of
  answer.

- **The primary analysis must address: "how many effective
  behavioural axes does this system express?"** This is a
  dimensionality question, not a pairwise-similarity question.

- **At least one of the following must be reported, chosen and
  committed to before the data is analysed:**
  - (a) PCA on the per-session state-share space (10 dimensions).
    Report explained variance per component. Effective dimensionality
    estimable from participation ratio or the explained-variance
    cumulative curve.
  - (b) KL divergence on the underlying tick-level state
    distributions, with a dimensionality reduction (e.g. t-SNE or
    UMAP) on pairwise KL distances across sampled cats.
  - (c) Both, with the secondary used as robustness check on the
    primary.

- **The continuous trait sampling must cover the full Feline Five
  unit cube, not just the convex hull of the five presets.**
  Otherwise the experiment cannot distinguish "preset locations
  happen to cluster" from "the full space clusters".

- **Sample size: N must be ≥ 1000 sampled trait vectors, one session
  per vector, fixed seed per session for reproducibility. If compute
  constraints make this infeasible, this ADR must be revised before
  running with a smaller N — not after.**

- **Pre-register the prediction.** If the action-space-dimensionality
  hypothesis is true, explained variance should concentrate in 2–3
  principal components. If the preset-selection-artefact reading is
  true, explained variance should be approximately uniform across
  components (the preset locations were misleading, but the full
  space is genuinely five-dimensional).

---

## Out of scope for this ADR

- The actual continuous-sampling run.
- Changes to the batch runner needed to support per-session sampling
  from the Feline Five space. That would require a follow-on
  code-change ADR or be folded into the work that resolves this ADR.
- Any conclusions about whether the v0.1 agent's action space is a
  dimensionality bottleneck. Those conclusions belong to the
  resolution of this ADR, not to the stub.

---

## Resolution (2026-05-30)

### What was run

Continuous trait sampling was added to the headless batch runner
(`litterbox/src/cli/batch.ts`, `pnpm batch:continuous`). Each of N=1000
sessions draws an independent Feline Five trait vector by sampling each
of the five traits uniformly from [0,1] via `createPersonality`, which
genuinely covers the full unit cube — not `interpolatePersonality`,
which produces only the convex hull (4-simplex, measure zero in the
cube) of the five presets and cannot reach extreme trait combinations.

- N = 1000 sessions, one per sampled trait vector.
- Master seed = 1 governs both the trait sequence and the per-session
  seeds; draw order documented as a contract in code.
- Habituation rate held fixed at 0.010 for all sessions. This isolates
  the Feline Five vector as the sole experimental variable. Habituation
  rates are placeholders (ADR 0003); sampling them would be sampling
  noise, and would confound the dimensionality question. **Consequence:
  these results are not directly comparable to the ADR 0005 baseline,
  which used preset-specific habituation rates.** This is a deliberate
  control, not an oversight.
- Per-session JSONL records the 10-dimensional state-share vector
  (verified to sum to 1.0 ± 1e-9 as a hard invariant before each record
  is written; the invariant held for all 1000 sessions), plus secondary
  metrics. A `_meta` header records the master seed.
- Reproducibility verified: two runs with the same master seed produced
  bit-identical output modulo the `generated_at` timestamp.
- Termination split: 601 `max_ticks`, 399 `cooldown_exhausted`,
  0 `leaving`, 0 `lockout`.

Analysis script `litterbox/scripts/analyse-continuous.py` (committed —
unlike ADR 0005's exploratory script, this is a pre-registered
verification whose output enters an ADR resolution, so it is committed
for reproducibility). PCA uses scikit-learn on raw state-share
fractions: centred, no standardisation, no CLR. Raw was pre-committed;
the choice is defended below.

We executed option (c): primary PCA plus the secondary KL-based check,
the latter used as a robustness check on the former. Both are
pre-registered.

### Primary metric — PCA on raw state-share fractions

Row-sum sanity: max |row_sum − 1| = 2.22e-16 (machine epsilon).

| k | explained variance ratio | cumulative |
|---:|---:|---:|
| 1 | 0.8762 | 0.8762 |
| 2 | 0.0584 | 0.9345 |
| 3 | 0.0373 | 0.9719 |
| 4 | 0.0106 | 0.9825 |
| 5 | 0.0093 | 0.9918 |
| 6–9 | (declining) | → 1.0000 |
| 10 | 1.48e-30 | 1.0000 |

**Participation ratio PR = (Σλ)² / Σλ² = 1.29.**

Component 10 ≈ 0 (λ₁₀/λ₁ = 1.7e-30) confirms the data live on the
9-simplex: one dimension is linearly dependent through the sum-to-1
constraint. This is the expected sanity result, not a bug.

PC1 (87.6%) loads almost entirely on **RESTING (+0.90) against ENGAGING
(−0.32)**, with ABSENT/APPROACHING/CURIOUS as weak secondary terms. The
stress states load at noise level on PC1: STRESSED −0.008, RETREATING
+0.003, OVERSTIMULATED −0.079. PC1 is a rest-versus-engagement axis,
orthogonal to stress. PC2 (5.8%) is ABSENT (+0.83) against the
engagement states — a "kind of non-engagement" axis. This is consistent
with ADR 0005's observation that CSS≥4 occupies only 2.6–4.9% of ticks:
the stress states are too rare in occupancy to drive variance.

A hypothesis that PC1 was a "cooldown axis" (given the 399/1000 cooldown
terminations) was raised and tested against the loadings. It is
**rejected**: a cooldown axis would load on the stress states, which it
does not. The cooldown spiral does not drive the dominant variance.

### Secondary metric — Jensen-Shannon + classical MDS (robustness check)

Jensen-Shannon divergence (not mean KL): JS is bounded on (0, ln2],
√JS is a true metric (Endres & Schindelin 2003), and mean KL is
unbounded and would be dominated by pairs where one distribution has
near-zero mass on a state the other visits. ε-floor = 1e-12 (≈8 orders
of magnitude below the smallest observed non-zero state-share), rows
renormalised after flooring.

Pairwise JS over 499,500 pairs (nats): min 9.88e-05, median 8.55e-03,
mean 2.61e-02, max 0.525 (theoretical max ln2 = 0.693).

Classical MDS on D = √JS, eigenvalues of −½·H·D²·H:

| k | eigenvalue | ratio (pos) | cumulative |
|---:|---:|---:|---:|
| 1 | 7.61 | 0.583 | 0.583 |
| 2 | 1.71 | 0.131 | 0.714 |
| 3 | 1.20 | 0.092 | 0.805 |
| 4 | 0.80 | 0.062 | 0.867 |
| 5 | 0.43 | 0.033 | 0.900 |

**Participation ratio PR = 2.69.**

Embedding quality: 429 negative eigenvalues, all at floating-point noise
level (total |negative| / total positive = 1.25e-14). √JS embeds in
near-Euclidean space here, so the MDS eigenvalues are interpretable as
dimensionality. Cumulative thresholds: 80% at 3 components, 90% at 5.

### Interpretation

**The pre-registered prediction discriminates cleanly.** It set out two
outcomes: concentrated variance (2–3 PC) supports the bottleneck
reading; approximately uniform variance supports the preset-artefact
reading. We sampled the full cube uniformly and found PC1 = 87.6% and a
sharp elbow — nowhere near uniform. **The preset-artefact reading is
rejected.** The full trait space collapses too; the low dimensionality
is not an artefact of where the five presets happen to sit.

**Effective dimensionality is ~2–3, not 5.** The two pre-registered
metrics agree the structure is low-dimensional (both far below 5, far
below 10) but disagree on how low: raw PCA gives PR=1.29 (~1 axis),
JS+MDS gives PR=2.69 (~3 axes). This disagreement is itself the answer
to ADR 0005's last open alternative. Raw PCA weights each state by its
*absolute* variance, so the high-occupancy RESTING state dominates PC1
and compresses the apparent dimensionality toward 1. The
absolute-variance weighting was flagged as a caveat *before* the JS
numbers were seen, not after — it is not a post-hoc explanation. JS is
sensitive to distributional shape across the whole simplex, including
the rare states raw PCA ignores; when those are allowed to count, 2–3
real axes appear.

The honest reading: there is a **real low-dimensional structure in the
agent–environment system at ~2–3 axes**, which raw PCA overstated as ~1.
The third ADR 0005 alternative ("analysis-metric artefact") is partly
implicated — raw PCA's ~1 was partly a metric artefact — but not fully,
because even the artefact-robust metric yields only ~3, not 5.

This lands close to ADR 0005's *original* L1-based reading ("two latent
behavioural axes plus anxious_skeptic as a separate cluster"). The
robust estimate (~2–3) confirms that two-axis reading better than this
ADR's own "2–3 PC" reformulation did: the primary metric ran slightly
*below* the predicted range and the secondary landed inside it. The
pre-registration held in the sense that mattered — the metric was chosen
before the data, the prediction was falsifiable, and it was tested as
written.

### Caveat that remains open

This is the dimensionality of the trait space **as expressed through the
v0.1 agent's five-action space, at fixed habituation, within the 30-min
interaction window.** It is not a claim about the intrinsic
dimensionality of the Feline Five model. The Feline Five traits, seen
through a richer action space or a longer window, could resolve into
more axes. The ~2–3 figure is a property of the agent–environment
system, and the constrained action space is precisely the bottleneck
ADR 0002 proposes to test by replacing the rule-based policy with a
learned one. If a learned agent resolves more than ~2–3 axes against the
same SimCat, that gap is evidence the v0.1 action space — not the trait
model — was the limit.

### Decisions following from this resolution

- ADR 0005's two-pair clustering hypothesis is **supported** (not proven
  — this is simulation, and SimCat is not validated against real cats
  per ADR 0001/0003). The named archetypes should continue to be
  described as inspection presets, not as behaviourally distinct
  profiles, in README, CITATIONS, and the SimCat model card.
- ADR 0002's continuous-sampling safeguard is **reinforced**: training
  on the five presets would train on ~2–3 effective axes' worth of
  behavioural variation while believing it covers five. Continuous
  sampling is necessary, not optional.
- The "action-space dimensionality limit" remains a **hypothesis about
  the v0.1 agent**, now with quantitative support, but still not a
  result cited from the ACI literature. It becomes testable when ADR
  0002's learned agent exists.
- No change to ethics-monitor thresholds, action space, or any
  shipped behaviour. This was a characterisation run.

### Reproducibility

- `255cd18` — build: bring src/cli under tsc --noEmit (tsconfig.cli.json)
- `cc4ec97` — feat: continuous Feline Five sampling + PCA analysis script
- `8247468` — analysis: PC1/PC2 loadings
- `9d5b457` — analysis: Jensen-Shannon + classical MDS robustness check

Run: `pnpm batch:continuous` (N=1000, master_seed=1, hab=0.010), then
`uv run litterbox/scripts/analyse-continuous.py <jsonl>`. Bit-identical
on re-run modulo the meta-header timestamp.

---

## References

- ADR 0002 — Self-play research track for emergent cat-communication
  strategies (continuous sampling requirement, third safeguard).
- ADR 0005 — Baseline interpretation and two-pair clustering
  hypothesis (the hypothesis this ADR verifies).
- Litchfield et al. 2017 — Feline Five.
- Endres, D. M. & Schindelin, J. E. (2003). A new metric for probability
  distributions. IEEE Transactions on Information Theory, 49(7),
  1858–1860. (√JS is a metric.)
