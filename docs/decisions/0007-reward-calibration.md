# ADR 0007: Reward calibration for the ADR 0002 self-play track

## Status

**Resolved (2026-05-30, evening).** The pre-registered crossover regime
was trained and evaluated. The pre-registered degeneracy classifier was
applied against locked thresholds (PUSH-criterion fix anchored to the
random baseline pushed earlier in the day, `9b9063e`). The form-choice
question 0007 explicitly deferred to a trained agent is closed
negatively: under the only regime where neither component is
pre-deleted from the gradient, no form provides a learnable gradient
above the random-policy floor. A reward-redesign ADR (0008) follows;
this resolution does not pre-empt its design.

Precedent for an ADR that locks framing before its resolution evidence
exists: [ADR 0005](0005-baseline-interpretation.md) and
[ADR 0006](0006-continuous-sampling.md). Both the degeneracy
classifier (`litterbox/rl/grid_scan_phase2.py`) and its thresholds
were locked before any trained-agent data existed; the resolution
honours that pre-registration — no threshold was edited after seeing
a result.

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

## Resolution (2026-05-30, evening)

### What was run

Three PPO runs were attempted under the pre-registered crossover
regime (form `adr0002_max_css`, α=1.0, β=0.5, engagement_scale_mult=5.0),
N=5M timesteps each (~32 min wall on Apple Silicon), evaluated by
`grid_scan_phase2.py` with N=100 episodes at master_seed=1.

**Run 1 — crossover, free variance (CleanRL default).**
- Command: `uv run rl/train_phase2.py --seed 1`
- Output dir: `/tmp/chatcat-rl-runs/phase2__seed1__1780166999/`
- `state_dict_sha256`: `88a1f70f3e87443a84aa871ced1f970e7e751ad92c4aade0026df9e640b0e602`
- Code commit: `9583df2` (phase 2 scaffold) + classifier fix `9b9063e`.
- Verdict: **NON_TRIVIAL** under the locked classifier — non-idle 0.92,
  entropy 1.95 bits, state-conditional TVD 0.34.

**Run 2 — entropy-coefficient ablation, aborted before launch.**
- Hypothesis: ent_coef was too high, suppressing determinism.
- Verification before launch: `train_phase2.py` line 98 sets
  `--ent-coef` default to 0.0; Run 1's `run_config.json` confirmed
  `ent_coef: 0.0`. The entropy term was already not in the loss.
- Run not executed. Per the same pre-registration discipline this ADR
  was built under, an elimination test whose premise is falsified
  before launch must be flagged, not run blindly. The observation
  rerouted to run 3.

**Run 3 — crossover, frozen `actor_logstd = -1.0` (per-dim σ ≈ 0.37).**
- Command: `uv run rl/train_phase2.py --seed 1 --frozen-logstd -1.0 --exp-name phase2_frozen_logstd_m1`
- Output dir: `/tmp/chatcat-rl-runs/phase2_frozen_logstd_m1__seed1__1780170832/`
- `state_dict_sha256`: `c48d9636eaa31c05cc47a434ba626a21e28b699769a4a4452b4c53548dfad98b`
- Code commit: this resolution's commit (`--frozen-logstd` flag and
  state_dict-buffer plumbing in `train_phase2.py` and
  `grid_scan_phase2.py`).
- Frozen-logstd choice anchored at −1.0 (not −2.0 which was an
  off-the-cuff first suggestion): for a 6-way argmax over type-logits,
  σ ≈ 0.37 retains meaningful exploration (~25% argmax-flip probability
  for mean-gap 0.5) while making the learned mean dominate sampling
  noise. Verified post-run: all 10 SimCat states visited > 50 times,
  5/6 action types ≥ 5% share, value_loss decreasing — exploration
  guard green, result binding.
- Verdict: **NON_TRIVIAL** under the locked classifier — non-idle 0.95,
  entropy 1.91 bits, state-conditional TVD 0.56.

### Results — direct three-way table

Random baseline (`--random-baseline` mode, no model), Run 1 (free
variance, free actor_logstd), Run 3 (free actor_mean, frozen
actor_logstd = −1.0). All scored under the crossover reward, all
seeded master_seed=1, all 100 evaluation episodes.

| Metric                    | Random  | Run 1   | Run 3   |
|---                        |---:     |---:     |---:     |
| idle_share                | 0.1668  | 0.0752  | 0.0534  |
| non_idle_share            | 0.8332  | 0.9248  | 0.9466  |
| action_type_entropy (bits)| 2.5850  | 1.9466  | 1.9060  |
| mean_engagement_intensity | 0.5000  | 0.1695  | 0.0944  |
| **mean_state_TVD**        | 0.0040  | **0.3376** | **0.5587** |
| mean_opt_outs_per_episode | 24.02   | 24.25   | 24.04   |
| high_css_share_overall    | 0.0232  | 0.0241  | 0.0231  |
| classification            | TRIVIAL | NON_TRIVIAL | NON_TRIVIAL |
| reward `adr0002_max_css`  | −10.314 | −10.205 | −10.339 |
| reward `mean_css`         | −6.262  | −6.139  | −6.321  |
| reward `high_css_share`   | −4.541  | −4.409  | −4.601  |

Reward `std` across all three runs and all three forms is 2.84–2.97;
all observed mean differences from random are within ±0.13 — i.e.,
within 5% of one standard deviation. The reward signal cannot
distinguish a state-conditional, deterministic agent from random
exploration at this sample size.

**Action-type marginals (run 1 vs run 3):** Run 1 ended on
`side_glance 47%, trill 28%, soft_purr 0.6%`; Run 3 ended on
`side_glance 55%, soft_purr 18%, slow_blink 12%, trill 1.6%`.
Different policies — same welfare, same reward.

### Resolution of ADR 0007's explicit question

ADR 0007 asked: under a policy that actually decorrelates the three
CSS aggregates, do the three reward forms differ in ways the random
baseline could not expose?

**No.** Two trained agents with strong state-conditioning (TVD ~7× and
~14× higher than the random-baseline noise floor of 0.0040,
respectively) and visibly different action-type marginals produce
**reward distributions indistinguishable from random** under all three
forms. The pairwise correlation pattern between forms documented in the
ADR 0007 random-baseline grid scan (r > 0.99 between forms) is
preserved under both trained policies — the forms continue to rank
trajectories together rather than apart.

The deferred form-choice decision is therefore closed negatively: at
this scale of training, in this regime, no form provides a learnable
gradient above random. `adr0002_max_css` remains the v0.2 nominal form
purely for fidelity to ADR 0002's wording.

### The deeper finding (not predicted by ADR 0007)

ADR 0007 named two failure modes (idle-out, push-the-cat). It did not
name a third: that a trained agent's behaviour can be measurably
state-conditional yet reward-invariant. That is what we observed —
twice, with two different variance disciplines, two different action
mixes.

The reward in the crossover regime is **flat enough that no
state-conditional deterministic policy at this PPO budget produces a
reward signal distinguishable from random**. Three alternative
explanations are ruled out by the runs:

1. **Entropy-bonus suppression of determinism** — falsified before
   Run 2 by inspection of `train_phase2.py` and Run 1's
   `run_config.json`: `ent_coef = 0.0` throughout. No entropy bonus
   exists in the loss to suppress determinism.
2. **Variance drift makes any deterministic structure invisible to
   the reward** — falsified by Run 3: with `actor_logstd` frozen at
   −1.0 (σ ≈ 0.37, ~11× tighter than Run 1's drifted endpoint),
   the agent learned an *even more* state-conditional policy
   (TVD 0.56 vs 0.34) and still landed at random-equivalent reward
   (within Δ < 0.2 on every form).
3. **Exploration failure** — falsified by the exploration guard
   pre-registered into Run 3: all 10 SimCat states received
   > 50 visits, 5/6 action types received ≥ 5% share, `value_loss`
   decreased monotonically (0.0159 → 0.0069). The critic was learning;
   the environment was being covered; the agent was not stuck.

With those three alternatives excluded, the residual conclusion is
that the reward formulation `engagement_minutes − α·max_CSS − β·opt_outs`
in the crossover (α=1.0, β=0.5, scale_mult=5.0) regime is *informationally
too coarse* to differentiate a sensible state-conditional policy from
random sampling at the 5M-timestep PPO scale. The gradient PPO computes
from this reward leads to behaviour change (the trained agents are
clearly not random) without leading to reward improvement — a
characteristic signature of a near-flat reward landscape.

The classic "climb-then-slide" pattern was reproduced under both
runs: Run 1 climbed to ep-return-mean = −10.03 at update ~1000 then
slid back to −10.98; Run 3 climbed to −9.99 at update ~1082 and slid
to −10.60. Neither held its gain. This is consistent with a reward
surface where local improvements exist (the climb) but the global
gradient is too noisy to maintain them (the slide).

### Methodology caveat

This finding is reward-flatness **in the crossover regime
(α=1.0, β=0.5, scale_mult=5.0), in this SimCat env, with the
Box(7,) action encoding (6 type-logits + intensity, argmax + clip),
at the 5M-timestep PPO scale on CPU with CleanRL's
ppo_continuous_action defaults**. It is **not** a claim that no reward
can drive learning against SimCat. It is the specific empirical
observation that this formulation, calibrated to this regime, does not.

A genuinely informative reward might decompose differently
(e.g., normalised components against trained-policy baselines, dense
intermediate rewards for state-conditional behaviours that ADR 0002's
formula treats as zero-information). That decomposition is the subject
of the follow-on ADR.

### What follows

A reward-redesign ADR (**0008**) is the natural next work. It is *not*
part of 0007's resolution and is intentionally not pre-empted here.
0008 will frame the question — what reward could give PPO learnable
gradient signal against SimCat? — and propose a candidate, with the
same pre-registration discipline (methodology locked before any new
training run). It may also consider whether a stronger algorithmic
prior (e.g., behaviour cloning from the rule-based ChatCatAgent as a
warm start) belongs in the v0.2 architecture alongside reward redesign.

### Decisions following from this resolution

- ADR 0002's compute-budget commitment (`$10–50`, 1M-step order) is
  **respected** — we spent two 5M-timestep runs and a baseline,
  well inside budget.
- ADR 0002's third safeguard (CONTINUOUS PERSONALITY SAMPLING) is
  unaffected; trait sampling worked as specified throughout.
- ADR 0007's preliminary position (start at crossover, adr0002_max_css)
  was the right starting point — it allowed the elimination test to be
  run cleanly. The preliminary position is now *retired* (not adopted),
  because the trained-agent data showed the regime cannot learn.
- No ethics-monitor thresholds, action-space definition, or shipped
  behaviour change as a consequence of this resolution. The agent's
  welfare profile (opt-outs, CSS occupancy) was essentially identical
  to random in both runs — the reward did not teach the agent to harm
  the cat. The classification flagged this correctly as NON_TRIVIAL
  rather than PUSH_THE_CAT because the welfare-outcome guard fires
  on degradation, not on activity.

## References

- [ADR 0002](0002-self-play-research-track.md) — Self-play research
  track for emergent cat-communication strategies. Specifies the reward
  formula this ADR calibrates. Names the reward-hacking failure mode
  the two degenerate regimes here instantiate. The third failure mode
  (state-conditional but reward-invariant) was unanticipated.
- [ADR 0005](0005-baseline-interpretation.md) — Baseline interpretation
  and two-pair clustering hypothesis. Precedent for a hypothesis
  deferred from one ADR to a later verification.
- [ADR 0006](0006-continuous-sampling.md) — Continuous Feline Five
  sampling, methodology pre-commitment. Precedent for locking framing
  before the evidence that resolves it exists. This ADR uses the same
  continuous-sampling regime (uniform [0,1]^5, habituation fixed at
  0.010) for both the random baseline and the trained agents.

## Reproducibility

### Random-baseline grid scan (origin of the three-form correlation table)

- Commits on `main`:
  - `96436d8` — env scaffold (`litterbox/src/rl/env.ts`, `reward.ts`, `encoders.ts`, harness `litterbox/src/cli/rl-random.ts`).
  - `9b646ec` — three episode-level reward forms + correlation report.
  - `9b4775f` — `--grid` mode for the 3 × 3 × 3 × 3 scan.
- Run: `pnpm rl:random --episodes 100 --master-seed 1 --grid`.
- Numerically identical across re-runs at the same master_seed.

### Phase 2 training stack

- Commits on `main`:
  - `437d056` — stdio bridge prototype + latency probe + determinism check.
  - `99a101e` — CleanRL PPO Discrete smoke (phase 1 reference, retired).
  - `bdf21be` — continuous Box(7,) env + ppo_continuous_action smoke.
  - `9583df2` — phase 2 training scaffold + grid scan + runbook (ADR 0007 crossover).
  - `9b9063e` — PUSH_THE_CAT criterion fix (welfare outcome, not action intensity), with random-baseline empirical anchor.
- This-commit additions: `--frozen-logstd` flag in `train_phase2.py`
  with `actor_logstd` as `register_buffer` when frozen; matching
  inference path in `grid_scan_phase2.py` that reads `frozen_logstd`
  from `run_config.json` (backward-compatible — runs without the field
  fall back to the CleanRL Parameter default).

### Run-1 + Run-3 reproduction

- Run 1: `uv run rl/train_phase2.py --seed 1` → `agent.pt` with
  `state_dict_sha256 = 88a1f70…0b0e602`. Then
  `uv run rl/grid_scan_phase2.py --model-path <agent.pt> --episodes 100 --seed 1`
  reproduces every classification metric in the table above to FP precision.
- Run 3: `uv run rl/train_phase2.py --seed 1 --frozen-logstd -1.0
  --exp-name phase2_frozen_logstd_m1` →
  `state_dict_sha256 = c48d963…548dfad98b`. Same grid-scan command
  reproduces Run 3's row.
- Re-running Run 1's grid scan after the classifier-fix commit
  (`9b9063e`) and the `--frozen-logstd` plumbing both produce
  bit-identical metrics to those captured at the time of the run —
  verified before this resolution was drafted.
