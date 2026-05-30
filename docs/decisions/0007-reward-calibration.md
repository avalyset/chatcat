# ADR 0007: Reward calibration for the ADR 0002 self-play track

## Status

**Proposed (open problem, resolution deferred to first trained agent).**

This ADR documents an elimination test: ADR 0002's default reward
parameters are structurally degenerate and cannot be used as-is. It does
not yet name the correct parameters. Resolution is deferred to a trained
PPO agent's behaviour, because correlation under random exploration
cannot adjudicate the question — see *Methodology caveat* below.
Precedent for an ADR that locks framing before its resolution evidence
exists: [ADR 0005](0005-baseline-interpretation.md) and
[ADR 0006](0006-continuous-sampling.md).

## Context

[ADR 0002](0002-self-play-research-track.md) specifies the v0.2 self-play
reward as

> Reward = engagement_minutes − α·max_CSS − β·opt_outs

but does not calibrate α, β, or the engagement-scale factor against the
numerical spread of the three components. The default implementation
chose α = 1.0, β = 0.5, engagement_scale = 1/(tick_rate · 60) — values
that look balanced on paper but were not checked against an empirical
baseline.

A random-action characterisation harness was built in three commits:

- `96436d8` — env scaffold: a gym-style wrapper over `SimCat` + `EthicsMonitor` with `reset(seed, traits?)` / `step(action) → {obs, reward, done, info}`, sitting directly on the simulator (not through `TickRunner`).
- `9b646ec` — three episode-level reward forms in `litterbox/src/rl/reward.ts`: the ADR 0002 reference (`adr0002_max_css`), a mean-CSS variant (`mean_css`, time-weighted integral), and a high-CSS-share variant (`high_css_share`, fraction of ticks with CSS ≥ 4 per Kessler & Turner 1997).
- `9b4775f` — a 3 × 3 × 3 grid scan over (α, β, engagement_scale) ∈ {0.5, 1, 2} × {0.1, 0.5, 1} × {1, 5, 20} per form, scoring all 81 grid points on the same N = 100 random-action episodes at master_seed = 1.

Trait vectors were sampled uniformly from [0,1]^5 (per ADR 0002 safeguard
#2 and [ADR 0006](0006-continuous-sampling.md)). Habituation rate fixed
at 0.010 (per ADR 0003 placeholder midpoint, isolating the reward
question from the unrelated habituation question).

## Findings

### Random-action component spreads (N=100, master_seed=1)

| component             | mean   | std   |
|---                    |---:    |---:   |
| engagement_minutes    | 1.54   | 0.57  |
| max_CSS               | 5.84   | 0.33  |
| mean_CSS              | 1.73   | 0.30  |
| high_css_share (≥4)   | 0.025  | 0.008 |
| opt_outs              | 25.77  | 5.13  |
| episode_length (ticks)| 17 426 | 2 250 |

Termination split: max_ticks 92, lockout 8. All three reward forms agree
to within FP precision when reconstructed from per-step decompositions
(max divergence 5.4e-13).

### ADR 0002 default — Pearson correlation between episode return and raw components

| form              | r(return, engagement) | r(return, opt_outs) |
|---                |---:                   |---:                 |
| adr0002_max_css   | +0.0847               | −0.9605             |
| mean_css          | +0.0757               | −0.9635             |
| high_css_share    | +0.0551               | −0.9749             |

The opt_outs signal is ~11× larger in magnitude than the engagement
signal across all three forms. The reward is **imbalanced by an order of
magnitude** in the direction ADR 0002 explicitly warned about (reward
hacking via simulator exploitation).

### Grid-scan structure (3 × 3 × 3 × 3 = 81 points)

Four structural observations from the full grid:

1. **β dominates the regime.** Per fixed (α, scale): β = 1.0 → opt-out-dominated (|r_opt| ≈ 0.99); β = 0.5 → opt-out-dominated (|r_opt| ≈ 0.96); β = 0.1 → engagement-dominated *if* scale ≥ 5.

2. **engagement_scale is the second lever.** Per fixed (α, β): scale = 1 leaves engagement too small to matter at any β; scale = 5 reaches crossover at β = 0.5; scale = 20 saturates engagement-dominance even at β = 0.1.

3. **α is nearly irrelevant under random actions.** Across α ∈ {0.5, 1, 2} at fixed (β, scale), |r_eng| and |r_opt| vary by less than 0.02. The CSS-penalty terms have std on the order of 0.3 (max_CSS), 0.30 (mean_CSS), or 0.008 (high_css_share) — too small for α to amplify into a competitive signal against the opt_outs term's std of 5.13.

4. **Reward-form choice (max_CSS / mean_CSS / high_css_share) is near-free under random actions.** Pairwise correlation between the three forms' episode returns is r > 0.99 across the whole grid (0.9923, 0.9932, 0.9985 at the ADR-default point). The three forms rank episodes essentially identically when the policy is random.

### Top engagement-correlated regimes (extract)

| form              | α   | β   | scale | \|r_eng\| | \|r_opt\| |
|---                |---: |---: |---:   |---:       |---:       |
| high_css_share    | 1.0 | 0.1 | 20    | **0.9990**| 0.1246    |
| mean_css          | 1.0 | 0.1 | 20    | 0.9987    | 0.1244    |
| adr0002_max_css   | 1.0 | 0.1 | 20    | 0.9986    | 0.1232    |
| adr0002_max_css   | 1.0 | 0.1 | 5     | 0.9778    | 0.0122    |
| **adr0002_max_css** | **1.0** | **0.5** | **5** | **0.6994**| **0.5814** |
| adr0002_max_css   | 1.0 | 0.5 | 1 (default) | 0.0847 | 0.9605 |

The bolded crossover row is the only point in the grid where both
correlation magnitudes are comparable.

## Central interpretation — two opposite degenerations

The two ends of the grid are not just "imbalanced" — they are opposite
reward-hacking failure modes in the sense ADR 0002 warned about ("an
agent learns to exploit SimCat's imperfections rather than communicate
with cats").

**High-β regime (β ≥ 0.5, scale ≤ 5): opt-out minimisation.** The
agent's gradient is dominated by −β · opt_outs. The optimal policy never
triggers a LEAVING/RETREATING transition. The cleanest way to do that is
to never engage in the first place — sit idle, score zero on engagement,
score zero on opt_outs, ride out the episode. A reward that almost never
rewards engagement selects for non-interaction. This is the ADR 0002
default regime.

**High-scale regime (β ≤ 0.1, scale ≥ 5): engagement maximisation
without opt-out cost.** The agent's gradient is dominated by
+scale · engagement_tick. The optimal policy maximises ENGAGING time
even at the cost of pushing the cat. The CSS-penalty term cannot
restrain this (α nearly irrelevant); the opt_outs term is small enough
that the agent learns to absorb opt-outs as the price of engagement
ticks. The agent exploits the simulator's tolerance for stress.

**Crossover regime (β = 0.5, scale = 5).** For the recommended
`adr0002_max_css` form, this is the unique grid point where neither
component is pre-deleted from the gradient. All three forms give
|r_eng| ≈ 0.70 against |r_opt| ≈ 0.58 at this point. The balance is set
by the ratio `scale / β`, which equals 10 here; for `high_css_share`
specifically, the CSS-penalty term has std 0.008 (below noise floor),
so the crossover degenerates to a 1D ridge along `scale / β = 10` —
`(β = 0.1, scale = 1)` is a near-equivalent point for that form. For
the `adr0002_max_css` reference form, max_CSS's std-0.33 noise breaks
this degeneracy and singles out β=0.5, scale=5. The crossover is the
only regime that leaves room for a learned policy to trade engagement
against opt-outs rather than collapse to one corner.

## Methodology caveat (explicit)

Pearson correlation between episode return and raw components, computed
under a random-action policy, **cannot select the right reward
parameters**. The grid scan above is an elimination test, not a
prescription:

- Random policy visits ENGAGING for ~5% of ticks (median 1.49 min of
  30). It spends essentially no time in the high-engagement /
  low-opt-out region a learned policy would explore. The correlation
  gradients above reflect the random-baseline distribution of
  (engagement, opt_outs), not the tradeoff that matters during
  training.
- The CSS-penalty term's apparent irrelevance under random actions is
  partly a statement *about random actions*. Random behaviour visits
  low- and medium-CSS states; a learned policy that engages will push
  cats further up the CSS scale, where the penalty term gains spread
  and α regains relevance.
- "Reward form is irrelevant" (r > 0.99 between max_CSS / mean_CSS /
  high_css_share) is similarly contingent on random actions producing
  trajectories where the three CSS aggregates are highly correlated. A
  policy that learns to manage stress could decorrelate them, at which
  point form choice becomes substantive.

These three statements together: the grid scan diagnoses ADR 0002
defaults as broken and identifies two opposite failure regimes. It does
not select the right point between them. That choice requires a trained
policy's trajectory distribution.

## Preliminary position (unvalidated)

For the first PPO baseline under ADR 0002, start at:

- form = `adr0002_max_css` (faithful to the original ADR 0002 spec)
- α = 1.0
- β = 0.5
- engagement_scale = 5 / (tick_rate · 60)   *(i.e., the "scale = 5" grid value relative to the previous default)*

**Not because this is validated correct, but because it is the only
grid point where neither component is pre-deleted from the gradient.**
A trained agent's behaviour in this regime — what fraction of time it
spends engaging, how it trades engagement against opt-outs as
habituation accumulates, whether it converges to one of the degenerate
corners anyway — is the first dataset that can actually adjudicate the
calibration question.

The reward-form choice (max_CSS vs mean_CSS vs high_css_share) is
deferred to the same trained-agent diagnostic. Under a policy that
decorrelates the three CSS aggregates, the forms will differ in ways
the random baseline cannot expose. `mean_css` and `high_css_share`
remain importable from `litterbox/src/rl/reward.ts` for the
post-baseline comparison.

## Resolution criteria (deferred)

This ADR resolves when:

1. A PPO baseline trained against SimCat under the crossover regime
   converges on a *non-trivial* policy — measurably different from
   random in the per-episode (engagement_minutes, max_CSS, mean_CSS,
   high_css_share, opt_outs) distribution, and not identical to either
   of the two degenerate corner policies (idle-out or push-the-cat).
2. The trained policy's per-episode trajectory distribution is rescored
   under the same 81-point grid. If the gradient under the trained
   policy still collapses to one corner, the post-training grid scan is
   the actionable diagnostic.
3. The post-training grid scan, combined with qualitative inspection of
   the trained policy, names a single (form, α, β, scale) tuple as the
   v0.2 calibration. That tuple is committed and this ADR closes.

If two consecutive trained-policy iterations under the chosen regime
both collapse to a degenerate corner, the reward *formulation* (not
just the parameters) must be revisited — e.g., z-score-normalised
components against the trained-policy baseline, or a constraint-style
reward where opt_outs / CSS are hard penalties and engagement is the
sole positive signal.

## Out of scope for this ADR

- Choice of RL algorithm (PPO vs alternative). ADR 0002 specifies PPO
  baseline; this ADR does not revisit that.
- Choice of training framework (Python bridge vs TS-native vs other).
  That decision is a separate v0.2 architectural concern.
- The reward-form decision itself. This ADR documents that all three
  forms behave indistinguishably under random actions and that the
  choice is deferred to a trained-policy diagnostic.
- Habituation-rate calibration. ADR 0003 owns that question; this ADR
  fixes hab = 0.010 to isolate the reward question.

## References

- [ADR 0002](0002-self-play-research-track.md) — Self-play research
  track for emergent cat-communication strategies. Specifies the reward
  formula this ADR calibrates. Names the reward-hacking failure mode
  the two degenerate regimes here instantiate.
- [ADR 0005](0005-baseline-interpretation.md) — Baseline interpretation
  and two-pair clustering hypothesis. Precedent for a hypothesis
  deferred from one ADR to a later verification.
- [ADR 0006](0006-continuous-sampling.md) — Continuous Feline Five
  sampling, methodology pre-commitment. Precedent for locking framing
  before the evidence that resolves it exists. This ADR uses the same
  continuous-sampling regime (uniform [0,1]^5, habituation fixed at
  0.010) for the random baseline.

## Reproducibility

- Commits on `main`:
  - `96436d8` — env scaffold (`litterbox/src/rl/env.ts`, `reward.ts`, `encoders.ts`, harness `litterbox/src/cli/rl-random.ts`).
  - `9b646ec` — three episode-level reward forms + correlation report.
  - `9b4775f` — `--grid` mode for the 3 × 3 × 3 × 3 scan.
- Run: `pnpm rl:random --episodes 100 --master-seed 1 --grid`.
- Numerically identical across re-runs at the same master_seed (only
  wall-time differs).
