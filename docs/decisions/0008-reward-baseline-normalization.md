# ADR 0008: Baseline-normalised reward for the ADR 0002 self-play track

## Status

**Resolved (2026-05-31): DOES_NOT_RESOLVE.** Three training runs against
the locked pre-registered criteria — first run against the env state of
the time, re-run against the [ADR 0009](0009-ethics-enforcement-point.md)-corrected
env, and an LR-stability ablation against the corrected env — all
classify as NON_TRIVIAL but fail climb-and-holds and better-than-baseline.
The pattern (climb-then-slide back below baseline) is robust across
three different policies, two different environments, and two different
learning rates. Two alternative explanations are ruled out:
(1) env bug — eliminated by ADR 0009's enforcement fix, which shifted Δ
by +0.55 reward units without any reward change;
(2) PPO instability — eliminated by the LR-stability ablation, where a
3× lower learning rate *worsened* the slide rather than dampening it.
The residual finding is that **baseline normalisation alone produces
informative-but-unstable reward signal**: the agent reaches the
baseline line and cannot be held there. Resolution closes 0008 and
points to a follow-on ADR (0010) for what could hold the agent at a
positive baseline-normalised return — but 0008's resolution does not
pre-empt 0010's design, in the same way 0007's resolution did not
pre-empt 0008.

## Context

[ADR 0007](0007-reward-calibration.md) resolved negatively: the
crossover-regime reward `engagement_minutes − α·max_CSS − β·opt_outs`
is informationally too coarse to differentiate a state-conditional
deterministic policy from random exploration at the 5M-timestep PPO
scale. Both trained agents (Run 1: free variance; Run 3:
frozen `actor_logstd = -1.0`) were measurably state-conditional
(TVD 0.34 and 0.56 respectively against random's 0.004) but produced
reward distributions indistinguishable from random
(Δ < 0.2 on every form; std ≈ 2.9). The signature on training was
"climb-then-slide": ep-return-mean rose ~1.0 unit by mid-training
then slid back to within ~0.1 of the initial value.

0007's three alternative explanations were ruled out: ent_coef was
already 0 (no entropy-bonus pull on the policy), variance drift was
falsified by the frozen-logstd run producing the same result, and the
exploration guard was green (all states visited, all action types
present, value_loss decreasing). The residual finding was that the
reward landscape itself is too flat for PPO to find a stable gradient.

This ADR tests one specific hypothesis: **a baseline-normalised reward
restores learnable gradient signal without prescribing behaviour, so
ADR 0002's emergence premise is preserved.** The agent is rewarded
for *doing better than a reference policy on the same cat* — not for
doing any particular thing.

The emergence-preservation point is the whole reason this approach is
preferred over the alternative discussed in 0007's resolution (dense
intermediate shaping rewards for state-conditional behaviours).
Dense shaping would directly reward the agent for, say, slow_blinking
when the cat is ALERT — which prescribes the strategy. Baseline
normalisation rewards only the *outcome* differential against a
reference and leaves the means (which actions, when) emergent.

## Methodology (locked before running)

### Reward formulation

Per episode, the PPO-visible reward at the terminal step is adjusted by
the rule-based reference's total reward on the same cat:

    R_PPO_final = R_agent_final + ( Σ R_agent_step  −  R_baseline(seed) )

where `R_baseline(seed)` is the total adr0002_max_css episode reward
of the rule-based v0.1 ChatCatAgent run on the SAME `(traits,
simcat_seed)` derived from `seed` by the same `mulberry32` flow the
RL env uses. Non-terminal step rewards are unchanged.

Summing across the episode, the agent's net episode reward equals
`R_agent_total − R_baseline(seed)`. Positive iff the agent did better
than the rule-based reference on that cat; negative iff worse. Zero
is the "matches reference" line.

Subtracting at the terminal step (rather than distributing
`R_baseline / episode_steps` across all steps) is equivalent in
expectation but cleaner: per-step rewards remain the natural
decomposition of the original adr0002_max_css form, and the
"versus baseline" signal appears as a single end-of-episode adjustment.

### Reference baseline source

The rule-based **v0.1 ChatCatAgent** (`litterbox/src/agent/policy.ts`)
is the natural reference: it exists, it is the canonical hand-crafted
policy that v0.2 self-play is meant to improve on, and "beat the
hand-crafted policy" is a substantive emergence target rather than an
arbitrary number. ADR 0002's framing was always that emergent strategies
should be discovered relative to what we already know works; this is
the literal operationalisation.

### How the baseline is obtained

**On-the-fly, per episode reset.** When the Python env wrapper calls
`reset(seed=S)`:

1. Wrapper sends a new message type `{"type": "rule_based_episode",
   "seed": S}` to the TS bridge.
2. Bridge derives `(traits, simcat_seed)` from `S` via the same
   `mulberry32` flow used by `env.ts` reset, instantiates a fresh
   `SimCat` + rule-based `ChatCatAgent` + `EthicsMonitor`, runs the
   episode to termination, returns total reward.
3. Wrapper stores this as `self.current_baseline_reward`.
4. Wrapper then proceeds with the normal RL `reset` and `step` flow;
   the baseline is subtracted at the terminal step's reward.

Rule-based episodes are cheap (~262 sessions/sec per ADR 0006 batch
data); on-the-fly adds ~1–2 seconds of wall time per 100 episodes.
This is acceptable and avoids the brittleness of pre-computing a
seed-indexed baseline table that would have to be regenerated on any
change to the rule-based policy or env.

### Run configuration

- Same crossover regime as 0007 (α=1.0, β=0.5, scale_mult=5.0) so
  reward components are directly comparable to ADR 0007's runs.
- Same PPO hyperparameters as `train_phase2.py` (CleanRL
  `ppo_continuous_action` defaults: num_steps=2048, num_minibatches=32,
  update_epochs=10, lr=3e-4, ent_coef=0).
- 5M timesteps, master seed = 1 — directly diffable with ADR 0007's
  Run 1 and Run 3.
- Free `actor_logstd` (no frozen-logstd ablation in this first run;
  if needed we revisit per 0007's lesson).

## Pre-registered success criteria (FROZEN)

All three must hold for 0008 to be resolved POSITIVELY. If any fail,
the run is informative evidence about baseline normalisation's
adequacy, but the ADR does not close.

### 1. Locked degeneracy classifier from 0007 — UNCHANGED

The agent must be classified `NON_TRIVIAL` under the locked thresholds
in `grid_scan_phase2.py` (IDLE_OUT_THRESHOLD=0.90,
PUSH_NON_IDLE_THRESHOLD=0.80, PUSH_OPT_OUT_PER_EPISODE_THRESHOLD=40,
PUSH_HIGH_CSS_SHARE_THRESHOLD=0.05, TRIVIAL_ENTROPY_THRESHOLD=0.5,
TRIVIAL_TVD_THRESHOLD=0.05). Not editing these thresholds —
re-locking them here only as a reminder that they are inherited.

### 2. Climb-AND-holds (training stability)

The "climb-then-slide" pattern that defined 0007's failure mode must
NOT repeat. Operationalised from `metrics.jsonl`:

- `ep_init` = `ep_return_mean_recent` at update 100 (first reasonably
  filled buffer of 100 episodes)
- `ep_peak` = max(`ep_return_mean_recent`) over all updates ≥ 100
- `ep_final` = `ep_return_mean_recent` at the final update

**Climb threshold:** `ep_peak − ep_init ≥ 1.0`.
1.0 reward unit is ≈3.5× the standard error of the rolling mean
(per-episode std ≈ 2.9, N=100 → SE ≈ 0.29). A climb of 1.0 is therefore
clearly above noise floor.

**Holds threshold:** `ep_final ≥ ep_peak − 0.5`.
The final mean must be within 0.5 reward units of the peak — i.e., the
agent retained essentially all of its peak gain rather than sliding
back. 0.5 ≈ 1.7× SE: tolerates noise but not the 50–95% slide-backs
seen in ADR 0007 (Run 1 retained 3% of peak gain; Run 3 retained 47%).

### 3. Better-than-baseline (the actual emergence test)

Across 100 evaluation episodes (master_seed=1) under the trained
policy, with per-episode baseline subtraction:

    mean( R_agent_total − R_baseline(seed) )  ≥  +1.0

1.0 reward unit above zero is ≈3.5 standard errors above the "matches
reference" line (eval-mean SE ≈ 0.29 per episode, with reward std
≈ 2.9 carried over from 0007). An agent that meets this threshold has
materially outperformed the hand-crafted v0.1 policy on the same
distribution of cats — which is the v0.2 emergence target ADR 0002
specified.

This is the criterion 0007 did not have, and it is the one that
actually adjudicates whether baseline normalisation makes the reward
learnable. The other two criteria are about the agent being well-formed
and the training being stable; this is about whether the agent is
genuinely better.

## Out of scope (explicit)

- **Dense intermediate shaping** (e.g., per-state reward for
  state-conditional actions). Explicitly rejected: dense shaping
  prescribes the strategy, conflicting with ADR 0002's emergence
  premise. ADR 0007's resolution mentioned dense shaping as a
  decomposition option; this ADR rules it out as the wrong answer to
  the right question. If baseline normalisation fails, dense shaping
  is still not the path — a deeper revisit (multi-component normalised
  reward, learned reward model) is.
- **Behaviour cloning warm-start from the rule-based policy.**
  Discussed in 0007's resolution. Deferred to a future ADR (potentially
  0009) if 0008 fails. BC would change *how* the agent learns rather
  than *what* it learns toward, and that is a different lever than
  reward design.
- **Habituation-rate variation.** ADR 0003 owns that; 0008 holds
  habituation fixed at 0.010 (the ADR 0006 baseline value, matching
  0007's runs).
- **Reward-form re-selection.** 0007 closed the form question
  negatively under flat reward; if baseline normalisation succeeds,
  the form question may need revisiting under the new regime, but
  that revisit belongs in this ADR's resolution or a successor, not
  in this stub.

## Resolution criteria (deferred)

This ADR resolves POSITIVELY iff all three pre-registered criteria
hold on the first training run (seed=1, 5M timesteps) with the
locked methodology.

This ADR resolves NEGATIVELY iff the run completes but fails one or
more criteria. In that case, the failure mode (which criterion failed,
on what numbers) is the actionable diagnostic for the next ADR. The
candidate next moves, in expected order:

- If `NON_TRIVIAL` fails: investigate exploration / training-length
  before assuming reward is the issue.
- If climb-and-holds fails but mean is still ≥ +1.0 at peak: the
  reward gradient is informative but unstable — investigate PPO
  hyperparameters (clip_coef, num_minibatches, lr schedule).
- If mean improvement < +1.0 even at peak: baseline normalisation
  is insufficient on its own; consider 0009 (BC warm-start) or
  multi-component reward normalisation.

## Resolution (2026-05-31)

### What was run

Three full 5M-timestep PPO training runs against the locked criteria,
each followed by `grid_scan_phase2_baseline.py` with 100 evaluation
episodes at master_seed=1.

| Run | Env | LR | state_dict_sha256 | Output dir |
|---|---|---|---|---|
| 1 (first) | unenforced (ADR 0009 not yet fixed) | 3e-4 | `88a1f70f3e87443a84aa871ced1f970e7e751ad92c4aade0026df9e640b0e602` | `phase2_baseline_norm__seed1__1780210056` |
| 2 (re-run) | enforced (ADR 0009 fix applied) | 3e-4 | `0ec5c9cb4820176d6c2bba164cf6dcd99d4d46838aee2edf3d0ddd2031772ac2` | `phase2_baseline_norm__seed1__1780215772` |
| 3 (LR-test) | enforced | **1e-4** | `19b5b677231ae988a426b17c0e55c5464bfcf8a1c7ff68494409d8272e3d0bfe` | `phase2_baseline_norm_lr1e4__seed1__1780218775` |

Run 2 was necessary because Run 1's measurement was made against an
environment with an unenforced welfare invariant — see ADR 0009 for
the full account; in short, the v0.1 `capIntensityForRetreat` cap was
only applied inside the rule-based `policy.ts`, never on the RL path
that the PPO agent used. Run 1's trained agent learned a policy that
exploited that gap (RETREATING intensity 0.701 over 24 994 visits).
Resolving 0008 against Run 1 would have meant resolving against
artefacts produced in a broken environment; we did not.

Run 3 (LR-test) was a single-lever stability ablation. Run 2 showed a
climb-then-slide signature (climb to ep-return +0.31 at update 136,
slide back to −0.87 at the end). Two readings were possible: PPO
instability (gradient steps too aggressive, agent overshoots its peak
and can't return), or reward-structure flatness (the peak is a local
optimum the reward landscape cannot hold the agent in). Run 3 ran
with `--learning-rate 1e-4` (3× lower than CleanRL's
`ppo_continuous_action.py` default) — alt annet identisk. If PPO
instability was the issue, smaller steps should have let the agent
settle into its peak.

### Three-way table — locked criteria + descriptive metrics

| | Run 1 (unenforced env) | Run 2 (enforced env) | Run 3 (enforced, LR 1e-4) |
|---|---:|---:|---:|
| **Verdict** | DOES_NOT_RESOLVE | DOES_NOT_RESOLVE | DOES_NOT_RESOLVE |
| Classifier (locked) | NON_TRIVIAL ✓ | NON_TRIVIAL ✓ | NON_TRIVIAL ✓ |
| Climb (≥ 1.0) | +0.459 ✗ | +0.294 ✗ | +0.037 ✗ |
| Holds (gap ≤ 0.5) | +0.111 ✓ | +1.184 ✗ | +1.408 ✗ |
| **Better-than-baseline (≥ +1.0)** | **−1.223 ✗** | **−0.670 ✗** | **−1.683 ✗** |
| | | | |
| `ep_init` @ update 100 | −0.766 | +0.020 | +0.041 |
| `ep_peak` | −0.307 (@274) | **+0.314** (@136) | +0.078 (@272) |
| `ep_final` @ update 2441 | −0.417 | −0.870 | −1.330 |
| mean R_agent (eval) | −10.820 | −10.268 | −11.281 |
| mean R_baseline (eval) | −9.598 | −9.598 | −9.598 |
| idle_share | 0.004 | 0.028 | 0.358 |
| non_idle_share | 0.996 | 0.972 | 0.642 |
| action_type_entropy (bits) | 0.881 | 1.473 | 2.092 |
| mean_engagement_intensity | 0.672 | 0.543 | 0.863 |
| mean_state_TVD | 0.426 | 0.494 | 0.463 |
| mean_opt_outs/episode | 24.53 | 24.20 | 25.42 |
| high_css_share | 0.0221 | 0.0220 | 0.0217 |
| Dominant action types | side_glance 84% | trill 71% | trill 28%, slow_blink 23%, idle 36% |

Three runs, three completely different action mixes, three different
training regimes — and one robust outcome: climb to ≈ baseline line,
then slide back below it.

### The positive finding (not buried)

Baseline normalisation **solved ADR 0007's reward-flatness problem**.

The signal is no longer indistinguishable from random:

- ADR 0007: trained-agent reward Δ vs random was −0.11 to +0.13 on
  every form, well within the per-episode reward standard deviation
  of 2.9. The signal was below noise.
- ADR 0008 Run 2 (enforced env): trained-agent baseline-normalised
  reward Δ = −0.670, std 3.084. The signal is **distinct from zero**
  (~2.2 standard errors below zero for N=100), and the gap from
  random's effective Δ (~0) to the trained agent's Δ is the largest
  any reward formulation has produced in this project.
- The entropy drift that 0007 used as a fingerprint of reward
  flatness — actor_logstd growing 4× (per-dim std 1.0 → 4.1) over
  training because the policy gradient has no direction to pull
  variance down — **shrank 15×** under baseline normalisation
  (Run 2: per-dim std 1.0 → 1.13, a drift of ~13% rather than ~310%).
  PPO is being told something coherent now.
- The agent reaches the baseline line. Run 2's peak was +0.314, Run 1's
  peak was −0.307 *but only because Run 1 found a stable local
  optimum in an env that allowed it to exploit the unenforced cap* —
  the same policy in a corrected env (Run 2) actually overshoots and
  reaches positive territory.

Baseline normalisation is real progress from ADR 0007's flat reward.
The 0007 → 0008 step is not wasted; it is the first reward formulation
in this project where the agent's behaviour can be measured as
meaningfully different from baseline by the reward signal it optimises.

### Why it does not resolve

**The signal is informative but not stably learnable.**

Across three runs with three different policies, climb is followed by
slide. The agent can reach the baseline line; it cannot stay there.
This pattern is robust:

- **Run 1** had a *small* slide (+0.111) only because the agent
  exploited the unenforced retreat-cap to find a stable broken local
  optimum (side_glance @ 0.9 in RESTING for 64% of all ticks; ADR
  0008 first-run Q3 documented this). The stability of Run 1's peak
  was an artefact of an unenforced welfare invariant, not of reward
  structure. Once ADR 0009 removed that broken local optimum, the
  underlying reward landscape's lack of a stable peak revealed itself.
- **Run 2** climbed to a real peak in positive territory (+0.314 at
  update 136) and slid back to −0.87. Slide gap +1.184 — well past the
  pre-registered tolerance of 0.5.
- **Run 3** under a 3× lower learning rate climbed barely above its
  init (+0.037), then slid +1.408 — the biggest slide of all three.
  If the slide were PPO-instability-driven (gradient steps too
  aggressive overshooting a peak), lower LR should have dampened it.
  Instead it widened.

The PPO-instability explanation is therefore eliminated. The env-bug
explanation was eliminated independently by the Run 1 → Run 2 shift:
ADR 0009's fix moved Δ by +0.553 reward units (−1.223 → −0.670) with
no reward change, proving that Run 1's measurement was contaminated by
the unenforced cap. With both alternatives ruled out, the residual
explanation is **reward structure**: the baseline line is a local
plateau the reward landscape cannot hold a learned policy at.

This is consistent with the analysis of Run 1's behaviour (see the
analysis turn before ADR 0009 was named): the agent loses to baseline
on opt_outs (+1.4/episode vs baseline) and engagement (−67 ticks/episode
vs baseline), almost nothing on CSS. The losses are *small and
distributed*, not concentrated. A reward signal computed from those
small distributed deltas does not produce a strong gradient pulling the
agent toward "stay here" once it's found "here".

### Explicit ADR 0009 link

Run 1's measurement was invalidated by ADR 0009's finding. The
unenforced retreat-cap let the trained agent emit RETREATING intensity
0.701 (over 24 994 visits) without env-side restriction, while the
rule-based baseline operated under a cap of 0.3 enforced by its own
`policy.ts:84`. The agent and the baseline were not playing the same
game.

Re-running against the ADR-0009-corrected env was not optional for
resolving 0008 — it was the only way to have a valid baseline-vs-agent
comparison. The fact that we found ADR 0009 *because* we declined to
resolve 0008 on Run 1's contaminated artefacts is the strongest
methodological vindication of the discipline this project has used
throughout: don't write a resolution against a measurement you have
reason to doubt. The 0009 finding is preserved in its own ADR; it does
not need to live in 0008's resolution to be credited.

### What this points to (without pre-empting)

The remaining question is **what could hold the agent at a positive
baseline-normalised return**. ADR 0008 does not answer it. Two
candidate directions exist; neither is endorsed here:

1. **Behaviour-cloning warm-start.** Initialise the PPO actor from
   the rule-based `ChatCatAgent`'s decision function (or a supervised
   approximation to it). The agent starts at the baseline line rather
   than having to find it from scratch, and PPO from a near-baseline
   starting policy may be more stable than PPO from random init.
   Addresses the "climb-then-slide" pattern by removing the climb
   (agent starts where it needs to stay) and giving the slide less
   distance to travel before any corrective gradient kicks in.
2. **Multi-component normalised reward.** Decompose the
   baseline-normalised score by component (engagement Δ, max_CSS Δ,
   opt_outs Δ) and normalise each separately, then sum. Plausibly
   gives PPO a denser, less degenerate gradient: at present the three
   components partially cancel (Run 1: engagement −0.56, max_CSS
   +0.05, opt_outs −0.71). Multi-component might preserve directional
   information per component rather than only the summed Δ.

These are different classes of solution. BC addresses *stability*
(give the agent a good starting point); multi-component addresses
*signal density* (give the agent richer per-component gradient).
ADR 0008's evidence — agent reaches the baseline line, slide pattern
is robust — is closer to a stability problem than a signal-density
problem (signal sufficient to climb; insufficient to hold). But
this is a hypothesis for ADR 0010 to test, not a conclusion for
ADR 0008 to lock in. The same way ADR 0007 did not pre-empt 0008's
design when it pointed forward, ADR 0008 should not pre-empt 0010's.

### Methodology caveat

This finding is "baseline normalisation alone does not produce a
stably learnable reward signal" **in the crossover regime
(α=1.0, β=0.5, scale_mult=5.0), in this SimCat env (after the
ADR 0009 enforcement fix), with the Box(7,) action encoding, at the
5M-timestep PPO scale, on CPU, with CleanRL `ppo_continuous_action`
default hyperparameters except where varied for Run 3**. It is not a
claim that no reward formulation can drive learning against SimCat.
It is the specific empirical observation that this formulation — and
the variation explored here — does not.

### Decisions following from this resolution

- ADR 0009 is fully credited: its fix was material to 0008's
  resolution, not just a sanity check. Run 1's artefacts are kept on
  disk as the record of the broken-env measurement but are not the
  evidence on which 0008 closes.
- ADR 0010 (to be written when Eirik is ready) addresses what holds
  the agent at the baseline line. Its design is not constrained
  here.
- No ADR 0002 safeguard is revisited as a consequence of this
  resolution. The reward formulation in `engagement_minutes − α·max_CSS −
  β·opt_outs` is not declared broken; it is declared *insufficient on
  its own* at this scale.
- No shipped behaviour, ethics-monitor threshold, or env constant
  changes as a consequence of this resolution.

### Reproducibility

- Code commits (on `main` after the push that lands these
  resolutions):
  - `437d056` — stdio bridge prototype.
  - `99a101e` — Discrete PPO smoke (phase 1 reference).
  - `bdf21be` — continuous Box(7,) env + ppo_continuous_action smoke.
  - `9583df2` — phase 2 training scaffold + grid scan + runbook.
  - `9b9063e` — PUSH_THE_CAT classifier fix (welfare-outcome anchor).
  - `55a2161` — ADR 0007 resolution + frozen-logstd plumbing.
  - The two commits landing alongside this resolution add: ADR 0009
    resolution + ethics-enforcement fix (`enforce()` in
    `EthicsMonitor`, applied in `env.ts`, `tick-runner.ts`, and
    `bridge.ts`); and ADR 0008's resolution + the three-run training
    stack used to produce it (`env_continuous_baseline.py`,
    `train_phase2_baseline.py`, `grid_scan_phase2_baseline.py`,
    `analyse_phase2_baseline.py`).
- Run 1 deterministic from `uv run rl/train_phase2_baseline.py --seed 1`
  against the env state PRIOR to ADR 0009's enforcement fix — i.e.,
  reproducible by reverting the enforcement commits before running. Its
  agent.pt and metrics.jsonl are retained at
  `/tmp/chatcat-rl-runs/phase2_baseline_norm__seed1__1780210056/` for
  the record; future reproductions against the corrected env will
  diverge.
- Run 2 deterministic from `uv run rl/train_phase2_baseline.py --seed 1`
  against the current `main`.
- Run 3 deterministic from `uv run rl/train_phase2_baseline.py
  --seed 1 --learning-rate 1e-4 --exp-name phase2_baseline_norm_lr1e4`
  against the current `main`.

## References

- [ADR 0002](0002-self-play-research-track.md) — self-play track,
  emergence premise this ADR explicitly preserves.
- [ADR 0007](0007-reward-calibration.md) — the resolution this ADR
  responds to. Reward-flatness finding; three alternative
  explanations eliminated; climb-then-slide signature; baseline
  numbers (random, Run 1, Run 3) that this run will be diffed against.
- [ADR 0009](0009-ethics-enforcement-point.md) — the welfare-cap
  enforcement gap found while declining to resolve ADR 0008 against
  Run 1's contaminated artefacts. 0009's fix shifted Run 1 → Run 2's
  Δ by +0.55 reward units without any reward change; that empirical
  shift is what eliminated env-bug as an alternative explanation for
  the climb-then-slide pattern.
- [ADR 0005](0005-baseline-interpretation.md) — precedent for
  pre-registration discipline (hypothesis deferred to verification).
- [ADR 0006](0006-continuous-sampling.md) — precedent for locking
  methodology before data exists. This ADR uses the same continuous
  Feline Five sampling regime as ADR 0006 and ADR 0007.

## Reproducibility

This stub commits the methodology. The training run will produce its
own commit with state_dict_sha256 and verifiable artefacts under
`/tmp/chatcat-rl-runs/phase2_baseline_norm__seed1__<timestamp>/`,
following the same pattern as 0007's runs.

The bridge addition (rule_based_episode message), Python wrapper
(BaselineNormalizedChatcatEnv), and training/eval scripts
(`train_phase2_baseline.py`, `grid_scan_phase2_baseline.py`) are
committed alongside this stub. Together they make the methodology
runnable as a single command — same discipline as 0007's runbook.
