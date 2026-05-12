# ADR 0005: Baseline interpretation — archetype collapse and two-pair clustering

## Status
Documented finding. Interpretation is a hypothesis pending verification in ADR 0006.

## Context

On 2026-05-12 the calibrated v0.1 simulator (post-ADR 0004 fixes) ran
`pnpm batch:baseline` to produce a 5000-session reference dataset: 1000
sessions per archetype × 5 archetypes, fixed-seed deterministic.

- File: `batch-results/2026-05-12T18-29-47.jsonl`
- Wall time: 19.1 s (262 sessions/sec)
- Ethics cross-check: passed (no CSS≥6 episode persisted past the
  intervention window)

The aggregate summary table emitted by the batch runner showed four of
five archetypes collapsing onto a near-identical signature:

```
archetype           Mean(min)  MaxCSS  OptOuts/sess  Cooldowns
bold_diplomat          30.0     5.5      25.63          0/1000
curious_watcher        30.0     5.8      25.89          0/1000
anxious_skeptic         9.1     6.1       7.19        966/1000
aloof_sovereign        30.0     5.7      24.67          0/1000
playful_volatile       30.0     5.9      26.12          0/1000
```

Only anxious_skeptic separated, and only via the cooldown path. The
smoke run (50 sessions, ADR 0004 §8) had shown clearer separation. The
collapse at N=1000 prompted a drilldown to test three hypotheses:

- **H1 — Real categorical effect.** Personality at this dwell-floor
  regime expresses through cooldown propensity (anxious skeptic), not
  through opt-out rate.
- **H2 — Floor effect.** The 30-min cap truncates divergence before it
  accumulates.
- **H3 — Insensitive headline metrics.** The four collapsed archetypes
  differ in state distributions, CSS trajectories, or agent action
  mixes — but `Mean(min)` and `OptOuts/sess` cannot see it.

A one-shot analysis script (`litterbox/scripts/analyse-baseline.ts`,
exploratory, not committed) produced
`batch-results/2026-05-12-baseline-analysis.md` (also not committed —
`batch-results/` is gitignored). Findings are summarised below.

---

## Findings

### 1. State distributions cluster the five archetypes into two pairs

L1 distance between mean per-state time-share vectors (10 states,
sum of absolute %-point differences):

```
                bold   curious   aloof   playful   anxious
bold              0.0      6.3     7.0       1.6       6.3
curious           6.3      0.0     1.7       5.3       7.9
aloof             7.0      1.7     0.0       6.2       8.4
playful           1.6      5.3     6.2       0.0       6.3
anxious           6.3      7.9     8.4       6.3       0.0
```

Two near-pairs emerge: bold↔playful (1.6 pp) and curious↔aloof (1.7 pp).
Distances across pairs are 5–7 pp. anxious_skeptic sits further from
each (6–8 pp). The headline summary's "four archetypes collapsed" is
not an accurate read of the underlying state mix — the four split
cleanly into two near-twin pairs.

### 2. Per-session mean CSS resolves what MaxCSS hides

```
archetype          mean   median    p90    p99   maxCSS   ≥4 share
bold_diplomat      1.40    1.40    1.47   1.54     5.5     2.63%
aloof_sovereign    1.56    1.56    1.63   1.68     5.7     2.54%
curious_watcher    1.67    1.67    1.74   1.79     5.8     2.59%
playful_volatile   1.80    1.80    1.87   1.94     5.9     2.80%
anxious_skeptic    2.07    2.02    2.24   2.76     6.1     4.94%
```

Per-session mean CSS ranges from 1.40 (bold) to 2.07 (anxious) — a
48% spread. MaxCSS spans only 5.5–6.1 because the dwell floor produces
brief CSS spikes for every archetype regardless of trait. The
tick-weighted share of ticks at CSS≥4 ("low-grade stress") roughly
doubles between bold_diplomat (2.63%) and anxious_skeptic (4.94%). Mean
CSS and the ≥4 share carry signal the headline MaxCSS metric does not.

### 3. Agent action mix mirrors the state-mix pairing

Non-idle action share per archetype, over all session ticks:

```
archetype          non-idle share
bold_diplomat            28.53%
playful_volatile         28.13%
curious_watcher          25.60%
aloof_sovereign          25.28%
anxious_skeptic          22.63%
```

The bold/playful pair sits at ~28%, the curious/aloof pair at ~25%,
anxious_skeptic lower (its sessions terminate early via cooldown).
The pairing is consistent with finding 1 — the agent emits more
non-idle responses (slow_blink, soft_purr, trill, pause) to bold and
playful cats, fewer to aloof and curious. The same two-pair structure
appears in both what the cat does (state distribution) and how the
agent responds.

### 4. Anxious-skeptic "survivors" are RNG, not different cats

Of 1000 anxious_skeptic sessions, 966 hit cooldown_exhausted and 34
ran to max_ticks. Comparing subgroups:

```
subgroup     n    sim_min   maxCSS   CSS mean   opt_outs   forced_pauses
survivors   34     30.0      5.1       1.99       24.7        50.5
cooled     966      8.3      6.1       2.07        6.6        30.7
```

Per-trait input means are identical between subgroups
(N=0.80, E=0.20, D=0.20, I=0.70, A=0.50). The survivor mean CSS (1.99)
is barely below the cooled group's (2.07). The "survivor" label
reflects RNG outcome, not a latent qualitatively-different cat. There
is no bimodality to chase here.

---

## Interpretation

The four-archetype headline collapse is **not** primarily a floor
effect (H2 — the spread at the floor-truncated 30-min mark is real and
visible once metrics other than `Mean(min)` and `OptOuts/sess` are
used), and **not** insensitive metrics in the naive sense (H3 in its
simplest form — the drilldown does find differences). The shape of
those differences suggests a third interpretation:

**The five named archetypes, expressed through the v0.1 agent's action
space and the 30-min interaction window, project onto approximately
two latent behavioural axes plus anxious_skeptic as a separate cluster.**

This is a **hypothesis**, not a result. The two-pair clustering may be
a property of the agent–environment system: a constrained action space
(idle, slow_blink, soft_purr, trill, pause) cannot resolve all five
dimensions of the Feline Five trait space (Litchfield et al. 2017)
into distinct interaction signatures. Alternative explanations remain
live (see "Verification deferred" below).

If the hypothesis holds, two implications follow:

(a) **The named archetypes are less behaviourally distinct than they
appear on paper.** "Bold Diplomat" and "Playful Volatile" sessions
produce near-twin state mixes and near-twin agent action mixes — not
because the underlying cats are similar (their input trait vectors
differ on every dimension) but because the v0.1 agent cannot
discriminate them through what it does and what it observes.

(b) **ADR 0002's requirement for continuous Feline Five sampling
during v0.2 RL training is strengthened.** The five named presets risk
being a misleading evaluation basis: a policy that performs equally
well across the five archetypes may simply be performing well on the
two-or-three-dimensional projection the agent can perceive, while
remaining blind to trait differences a richer action space could
resolve.

---

## Verification deferred to ADR 0006

The two-pair clustering is derived from N=1000 sessions per archetype
across only five fixed trait vectors. It could be:

- Real (an action-space dimensionality limit baked into v0.1).
- An artefact of preset selection (the five Litchfield-derived presets
  happen to span only ~2 effective axes once mapped through SimCat's
  state machine and the v0.1 agent).
- An artefact of the analysis metrics (state-mix L1 distance and
  non-idle share may co-vary with trait subsets that are not yet
  isolated).

Resolving this requires a follow-up batch run that samples trait
vectors continuously from the Feline Five space rather than relying on
the five presets. If the resulting state-mix and action-mix landscape
is approximately one- or two-dimensional across thousands of sampled
cats, the dimensionality-limit interpretation gains support. If the
landscape is genuinely five-dimensional but the five preset locations
happen to fall into two clusters, the artefact-of-preset-selection
reading wins. ADR 0006 will document the design and outcome of that
run. No timeline commitment.

---

## Consequences

- The five named archetypes remain useful **inspection presets** for
  smoke tests and ad-hoc debugging. They should not be over-interpreted
  as five distinct interaction profiles in v0.1.

- The README, CITATIONS, and the simcat-v0.1 model card should not
  publish claims of per-archetype behavioural distinctness beyond what
  the L1 distances and CSS spreads in this baseline actually support
  (anxious_skeptic separates; the remaining four cluster into two
  near-pairs).

- ADR 0002's third safeguard — continuous Feline Five sampling for
  v0.2 RL training — is reinforced by this baseline. Training on the
  five preset vectors alone would risk a policy optimised for the
  two-pair projection rather than for the trait space.

- The anxious_skeptic "survivor" non-finding (34/1000 sessions that
  did not trigger cooldown) is recorded here so future contributors
  do not pursue a latent-bimodality interpretation. Survivors and
  cooled sessions share identical input traits and near-identical CSS
  means; the split is RNG, not personality.

- The batch runner's current JSONL schema records only aggregate
  per-session ethics counts (`opt_outs`, `forced_pauses`), not
  per-event tick timing. A future enhancement could add
  `opt_out_ticks: number[]` to support opt-out timing analyses (when
  in the session opt-outs cluster) that the present schema cannot
  answer.

---

## References

- ADR 0002 — Self-play research track for emergent cat-communication
  strategies (continuous Feline Five sampling requirement).
- ADR 0003 — Habituation rate values are placeholders pending
  real-cat data.
- ADR 0004 — State machine flicker investigation and resolution
  (dwell floors, CSS synchronisation). The baseline analysed here was
  run against the post-fix simulator.
- Litchfield, C. A., Quinton, G., Tindle, H., Chiera, B.,
  Kikillus, K. H., & Roetman, P. (2017). The "Feline Five": An
  exploration of personality in pet cats. PLOS ONE 12(8):e0183455.
- `batch-results/2026-05-12T18-29-47.jsonl` — baseline run output
  (gitignored).
- `batch-results/2026-05-12-baseline-analysis.md` — full analysis
  report (gitignored, exploratory).
- `litterbox/scripts/analyse-baseline.ts` — analysis script
  (not committed, exploratory).

Note: the "action-space dimensionality limit" framing is not cited
from the ACI literature. It is a hypothesis generated from this
baseline and remains to be tested per ADR 0006.
