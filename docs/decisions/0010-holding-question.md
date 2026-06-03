# ADR 0010: What "holding" is — framing the question before picking a fix

## Status

**Proposed.** Framing (a) is pre-committed in this stub (three framings
distinguished; Eirik picks). Signature (b) is pre-committed and
**applied** in the Diagnosis section below — diagnosis is
**SIG-EXPLORATION** for all three 0008 runs, on a layered confidence
basis. Candidate fix is deliberately deferred to the framing choice
and to the resolution amendment that will follow.

Two upstream questions are answered here:

1. **Which kind of "holding" is actually required?** Three framings
   exist, and the choice cascades through everything downstream.
   **Framing not picked in this stub** — pre-committed to be answered
   by Eirik in the resolution amendment.
2. **What does the slide actually look like?** A pre-registered
   diagnostic signature distinguishes an exploration/optimisation
   artefact from a reward-landscape problem. **Diagnosis applied below
   on a layered confidence basis** — see Diagnosis section.

## Context

[ADR 0008](0008-reward-baseline-normalization.md) closed
`DOES_NOT_RESOLVE`. Three training runs showed robust climb-then-slide:
the agent reaches the baseline-normalised reward line, cannot be held
there, slides back below. Two alternative explanations were ruled out
by the runs themselves — env-bug eliminated by Run 1 → Run 2 (the
ADR 0009 fix moved Δ by +0.55 reward units with no reward change),
PPO-instability eliminated by the LR-stability ablation (lower
learning rate widened the slide rather than dampening it).

The natural reflex was to frame the next ADR as "BC warm-start vs
multi-component reward". That framing was wrong in two ways. First, it
assumes *holding is the target* — but whether holding is required
depends on what we want the policy *for*. Second, it assumes
*BC fixes stability while reward redesign fixes signal* — but ADR 0008
showed the signal is present (agent reaches the baseline); what fails
is keeping the policy at a point it has already found. Whether that
"keep" failure is an exploration property or a reward-landscape
property has not been diagnosed; until it is, the BC-vs-reward dichotomy
is two solutions in search of a problem.

This ADR pre-commits the framing before any candidate is named.

## (a) What is "holding" actually about? Three framings.

Pre-commit to one. Each cascades differently.

### Framing 1 — Deployable policy

What we want is *a* policy that performs at or near baseline.

- The slide under continued training is cosmetic; we never deploy the
  end-of-training checkpoint, we deploy the peak-checkpoint.
- The right ADR is about **checkpoint selection + reproducibility of
  the peak**: how do we decide which checkpoint to keep, how do we
  know we can reproduce reaching that checkpoint, how stable is the
  peak's performance across seeds.
- Near-trivial in mechanism; the "fix" is "stop training when
  ep_return_mean_recent stops improving over a window". No new reward
  design, no architectural change.
- ADR 0010 in this framing closes quickly with a checkpoint policy
  and an N-seed reproducibility test of the peak.

### Framing 2 — Structural characterisation

Robust climb-then-slide is itself the finding.

- Three runs, three policies, three regimes, identical structural
  outcome. That is not a bug we should patch — it is a property of
  PPO + baseline-normalised reward + this env that deserves
  documentation.
- The right ADR characterises *why* the slide occurs (what the policy
  is doing during slide vs at peak, what the gradient signal looks
  like there, whether the reward landscape has a saddle/cliff near
  baseline) — *not* how to make it stop.
- The output is a paper or technical report, not a code change.
- ADR 0010 in this framing closes with that characterisation. Any
  follow-on intervention is a separate ADR that explicitly accepts
  the documented characterisation as premise.

### Framing 3 — Online holding required

The deployed policy must continue to hold position at the baseline
line *during long-running interaction*, not just at a checkpoint.

- The most expensive interpretation. Requires that something in the
  project actually demands this.
- My (CC's) reading of the current project state: **nothing demands
  this yet.** The v0.2 self-play track (ADR 0002) does not require an
  online-stable trained policy; it requires a trained policy whose
  *behaviour* can be validated against real cats. A peak-checkpoint
  policy that holds for the duration of an evaluation session
  satisfies that. Framing 3 only becomes the right ADR if a
  downstream requirement is documented that says otherwise.
- ADR 0010 in this framing is the largest of the three: it needs to
  state the requirement explicitly, then characterise the slide, then
  design a fix. Probably becomes multiple ADRs.

### The pre-commitment in (a)

**Which framing is ADR 0010?** Decision pre-committed here, before
the diagnostic in (b) is read. The framing choice should not depend
on the diagnostic outcome — the diagnostic tells us *what* the slide
is, not *whether* we need to fix it.

*This stub does not pick the framing.* Eirik picks; CC's role is to
ensure the three framings are clearly distinguished and that the
implications of each are explicit. The downstream design of ADR 0010
proper (after this stub) operates within the chosen framing.

## (b) Pre-registered diagnostic signature

Locked before any of the existing 0008-run logs are read against it.
The signature distinguishes two failure modes:

### SIG-EXPLORATION (optimisation-side, reward uninvolved)

At and after the peak update, BOTH of:

1. **Policy variance has NOT collapsed.** `actor_logstd` (or entropy
   as proxy, since CleanRL `ppo_continuous_action` does not log
   `actor_logstd` separately in stock) remains wide — at or above
   its initial value, not converged toward a deterministic mode.
2. **`value_loss` is LOW.** The critic has converged on a value
   function: it is no longer the bottleneck.

Threshold: "wide" = end-of-training entropy ≥ start-of-training
entropy (since `ent_coef = 0` in all 0008 runs, any drift in entropy
comes from `actor_logstd` itself moving under policy gradient — not
from an entropy-bonus pull); "low" = `value_loss` at peak < 0.1 × its
maximum value during training, AND `value_loss` at slide-bottom is
within the same band.

**Interpretation:** the policy never committed to a deterministic
mode. Exploration noise from a still-wide Gaussian keeps the policy
drifting; even though the critic correctly values being near baseline,
the actor cannot stabilise there because each sampled action is too
variable. The reward landscape is uninvolved. **The fix-axis is
optimisation-side**: variance/entropy annealing schedules, KL anchor
to a reference policy, target-KL early stopping, learning-rate
warmdown.

### SIG-LANDSCAPE (reward-side, reward landscape implicated)

At or before the slide, EITHER:

1. **Policy variance HAS collapsed** (entropy at peak meaningfully
   below entropy at start — by ≥ 1 nat over all dims summed, i.e.,
   per-dim `log_std` drift ≥ −0.14, meaning per-dim σ drift ≥ −13%),
   AND the slide happens AFTER that collapse — i.e., the policy
   converged to a deterministic mode and the slide is that mode being
   non-stationary under further updates.

   OR

2. **`value_loss` has NOT converged** (still drifting / non-decreasing
   near peak). The critic has not stabilised on a value function; the
   policy is taking gradient steps against a moving target.

**Interpretation:** either the policy committed to a deterministic
mode that the reward landscape does not actually reward at peak (and
PPO is updating it away because the reward signal points elsewhere),
or the critic itself is part of the instability (it values the agent
at peak, but updates revise that valuation). Either way the reward
*structure* — not the optimiser — is in play. **The fix-axis is
reward-side**: reshaping (multi-component normalised, dense
intermediate, or constraint-style), warm-starting from a known-good
policy (BC), or revising the baseline-normalisation form.

### Inconclusive

If the readings split (e.g., one run SIG-EXPLORATION, another
SIG-LANDSCAPE) or fall between the thresholds, that is itself the
result. Do not force a classification. The honest output is
"inconclusive across runs — different regimes produced different
signatures", and ADR 0010's design choice acknowledges that.

### Pre-registration caveat

This stub is being written *after* the three 0008 runs completed and
their metrics.jsonl files exist on disk. CC has reported general
entropy and value_loss trajectories for these runs in prior turns,
so the signature is not being locked in zero-information conditions.
The discipline-compliant version would have pre-registered before any
0008 training. We did not.

The signature above is still binding *as a criterion* — it is
explicit, it has thresholds, and it will not be edited after the
diagnostic in step 2/3 of this work is reported. But the reader should
know that the pre-registration is partial: the thresholds were chosen
with awareness of the rough shape of the curves, not before any data
existed.

## Diagnosis (2026-06-03)

The signature in (b) above was applied against the three 0008 runs.
The diagnosis is **SIG-EXPLORATION** for all three. Confidence is
layered — different components of the signature have different
verification status, and the diagnosis is robust because the
sign-certain component is discriminating.

### Verification status — what is and is not currently on disk

**Important:** Between when the 0008 runs completed (2026-05-31) and
when this diagnosis was written (2026-06-03), `/tmp/chatcat-rl-runs/`
was wiped. The `metrics.jsonl` files for all three runs and their
`agent.pt` checkpoints are no longer on disk. Re-verifying the
diagnosis against current disk state requires re-running training,
which would not be budget-free.

The numbers below were verified against `metrics.jsonl` *at the time*
the runs completed (in prior turns of this session, and cited in
ADR 0008's resolution). They are accurate to those readings but
cannot currently be reproduced from disk without retraining. The
diagnosis status is therefore "applied against verified-at-the-time
numbers, not verifiable against disk now."

### Layer 1 — std direction (sign-certain, discriminating)

The signature's `LOGSTD_DRIFT_THRESH = −0.14` (collapse threshold)
sits well below zero. The verified-at-the-time end-state log_std
drifts are:

| Run | entropy init → final | per-dim log_std drift (final − init) | direction |
|---|---|---:|---|
| Run 1 (unenforced, lr 3e-4) | +9.94 → +10.57 | **+0.090** | **wider** |
| Run 2 (enforced, lr 3e-4) | +9.94 → +10.93 | **+0.141** | **wider** |
| Run 3 (enforced, lr 1e-4) | +9.94 → +10.48 | **+0.077** | **wider** |

Conversion: `entropy = action_dim · (0.5·ln(2πe) + ln σ)`; with
action_dim = 7, `per-dim ln σ = entropy/7 − 1.4189`. Each entropy
delta of +0.63 to +0.99 translates to per-dim `ln σ` rising by
+0.09 to +0.14.

All three runs widened. None collapsed. The signature's collapse
threshold of −0.14 is not approached on any run; the drifts are on
the wrong side of zero entirely.

**This layer is sign-certain.** Even if the precise peak-update
entropy values are unknown from disk, the sign of the drift between
initial (update 1, fixed at +9.94 since `actor_logstd` initialises
to zeros) and final (update 2441, recorded) is unambiguous:
end-of-training σ is wider than start. The policy did not commit to
a deterministic mode at any point during training that the
end-of-training reading could mask — if it had, end σ would have to
be narrower than start, not wider.

**This layer alone is enough to rule out SIG-LANDSCAPE's
"variance-collapsed" branch.** That branch's premise is falsified
by sign on three runs out of three.

### Layer 2 — value_loss (end-state-certain, not peak-timing-certain)

| Run | value_loss init | value_loss final | max during training | final / max |
|---|---:|---:|---:|---:|
| Run 1 | 0.0158 | 0.0009 | 1.48 | 0.0006 |
| Run 2 | 0.0158 | 0.0025 | 2.04 | 0.0012 |
| Run 3 | 0.0156 | 0.0038 | 1.77 | 0.0021 |

End-state `value_loss` is two-to-three orders of magnitude below
its training-max for every run. The signature's
`VLOSS_LOW_FRAC = 0.1` threshold (peak `value_loss < 0.1 × max`)
is satisfied at end-state by margins of 50× to 200×.

The signature was registered to be applied **at peak**, not at
end-state. The peak-time `value_loss` numbers are not on disk.
What we cannot rule out from current data:

- If the `value_loss` max occurred *before* peak update, then
  `value_loss` at peak was small (signature passes for
  SIG-EXPLORATION).
- If the `value_loss` max occurred *at or after* peak update, then
  `value_loss` at peak was potentially high, and the signature's
  "critic converged at peak" requirement may not have held — which
  would push the diagnosis toward SIG-LANDSCAPE's
  "critic-non-converged" branch.

This timing question cannot be resolved without `metrics.jsonl`.
**This layer is not currently sign-certain — but it cannot tip the
diagnosis on its own.** The SIG-LANDSCAPE branch requires *either*
variance collapse *or* critic non-convergence. Variance collapse is
already excluded by Layer 1 with sign-certainty. For SIG-LANDSCAPE
to hold, value_loss non-convergence would have to be the entire
case — but the signature was specifically registered as an OR-of-two
conditions for SIG-LANDSCAPE, both rooted in "the reward landscape
is implicated". If only one of the two fires (and the other —
variance collapse — explicitly does not), the cleaner reading is
that the value-loss reading at peak is a timing artefact (max
occurred during a known noisy region; max for Run 1 was 1.48 with
mean over last 100 updates of just 0.0264, suggesting the max was a
transient spike) rather than a structural reward-landscape problem.

### Combined diagnosis

**SIG-EXPLORATION** for all three runs.

- Variance never collapsed (Layer 1 sign-certain across 3/3 runs).
- Critic converged to low value_loss by end-of-training (Layer 2
  certain). Peak-timing of `value_loss` not currently verifiable;
  ambiguity is bounded and cannot reverse the diagnosis because Layer
  1 already excludes the alternative.

The slide is therefore on the **optimisation side**, not in the
reward landscape. The reward signal is producing a coherent
gradient (`actor_logstd` does not collapse; critic learns a value
function); what fails is the policy stabilising at the value it
finds. Wide variance means each new rollout samples actions
substantially away from the policy mean, and PPO's mean-update has
no mechanism for narrowing the variance autonomously (since
`ent_coef = 0` and `actor_logstd` is a free parameter under the
policy-gradient updates).

**Fix axis indicated:** variance/entropy annealing (a schedule that
narrows `actor_logstd` over training), or a KL anchor to a
reference policy (so the policy mean does not drift far from a
known-good point), or target-KL early stopping. **NOT reward
redesign.**

This is the *axis*, not a candidate. The candidate choice (which
specific mechanism, what schedule, what reference) is downstream
of the framing choice in (a) and of explicit risk analysis. ADR 0010's
resolution will pick the candidate; this stub commits the axis.

### What the diagnosis does NOT do

- **Pick a framing.** Section (a) is still open. The diagnosis is
  the same regardless of whether Eirik picks Framing 1, 2, or 3;
  the framing determines whether we *act* on the diagnosis
  (Framing 3 → fix on the optimisation axis), characterise it
  (Framing 2 → document SIG-EXPLORATION as the finding), or
  set it aside (Framing 1 → checkpoint selection makes the slide
  cosmetic).
- **Pick a candidate.** Variance annealing, KL anchor, and target-KL
  early stopping are all on the optimisation axis. Choice among them
  is design work for the resolution amendment, after framing.
- **Re-open the Ethics flag.** The optimisation-axis candidates do
  not introduce reward terms; the Impartiality concern below
  remains specifically about any future reward-side candidate that
  *might* be considered if the diagnosis had pointed the other way.
  It still applies if a hybrid path is ever proposed.

## Ethics flag (must survive into any downstream design)

If any candidate fix in a follow-on ADR introduces a "holding" reward
term — i.e., a term that rewards the agent for *remaining engaged
above baseline* over time — that term is a time-on-screen KPI through
the back door, in exactly the form
[ETHICS.md §2 (Impartiality)](../../ETHICS.md) explicitly excludes.
The point of [ADR 0007](0007-reward-calibration.md) and
[ADR 0008](0008-reward-baseline-normalization.md) was to design a
reward that cannot be hacked toward engagement-maximisation; a
holding-bonus undoes that.

**Any holding-bonus reward term must pass the same Impartiality
review as any new reward term**, not be treated as an optimisation
tuning detail. The check is concrete: would the agent's gradient
strictly prefer "stay engaged longer at the same intensity" over
"engage well, then yield to the cat's withdrawal"? If yes, the term
is engagement-maximising regardless of how it is dressed up as
stability. ADR 0010 acknowledges this constraint up front so it
cannot be lost downstream.

This is independent of the (a)-framing choice. Framings 1 and 2 do
not raise this risk (no new reward term needed); Framing 3 plausibly
does, and so any Framing-3 instantiation must answer the
Impartiality question explicitly before any candidate mechanism is
chosen.

## Out of scope

- **Picking a candidate mechanism** (BC warm-start, reward shaping,
  checkpoint selection, KL anchor, anything else). The whole point
  of this stub is that the candidate is downstream of (a) and (b).
- **Re-running 0008.** This work is budget-free; it uses only the
  three existing 0008-run artefacts on disk.
- **Touching 0007/0008/0009.** Those are resolved.

## What follows

1. CC (in step 2/3 of the same task) reads the existing 0008-run logs
   against signature (b) and reports diagnosis: SIG-EXPLORATION,
   SIG-LANDSCAPE, or inconclusive. No fix-axis is chosen on the
   basis of that diagnosis yet — only the *axis* is named.
2. Eirik picks the (a)-framing (1, 2, or 3) — possibly informed by
   the (b)-diagnosis, possibly not. Within Framing 1, the diagnostic
   is moot. Within Framings 2 and 3, the diagnostic shapes what's
   characterised or fixed.
3. ADR 0010 proper (this stub's amendment with a Resolution section)
   commits both the framing choice and the diagnosis, then either
   closes (Framing 1, possibly Framing 2) or designs the fix
   (Framing 3, requiring the Impartiality check above).

## References

- [ADR 0002](0002-self-play-research-track.md) — self-play track,
  the safeguards this ADR's downstream choices must continue to
  respect.
- [ADR 0007](0007-reward-calibration.md) — reward-flatness finding;
  baseline-normalisation was the response.
- [ADR 0008](0008-reward-baseline-normalization.md) — the
  DOES_NOT_RESOLVE that this ADR picks up from. Three runs,
  climb-then-slide, env-bug and PPO-instability eliminated.
- [ADR 0009](0009-ethics-enforcement-point.md) — the welfare-cap
  enforcement architecture. ADR 0010 design must respect
  `EthicsMonitor.enforce()` as the single gate; no candidate that
  bypasses it is admissible.
- [ETHICS.md §2 (Impartiality)](../../ETHICS.md) — the
  no-engagement-KPI constraint that any holding-bonus reward term
  must clear.
