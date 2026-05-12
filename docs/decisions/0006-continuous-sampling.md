# ADR 0006: Continuous Feline Five sampling — methodology pre-commitment

## Status
Proposed (not started). Methodology constraints locked in advance of any data.

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

## Methodology constraints (pre-commitment)

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

## References

- ADR 0002 — Self-play research track for emergent cat-communication
  strategies (continuous sampling requirement, third safeguard).
- ADR 0005 — Baseline interpretation and two-pair clustering
  hypothesis (the hypothesis this ADR will verify).
