# ADR 0009: Ethics enforcement point — `capIntensityForRetreat` is bypassed by the RL path

## Status

**Resolved (2026-05-31).** Architecture: Option A — `EthicsMonitor`
owns the enforcement gate via a new `enforce()` method. Every action
path (RL env.step, rule-based TickRunner, baseline rule_based_episode)
now passes the agent's action through `ethicsMonitor.enforce()` before
`simcat.tick()`. The capped action is what reaches the simulator and
what is logged; the original (pre-cap) action is captured in a
per-step `CapEnforcement` record so empirical overshoot attempts are
traceable. `policy.ts:84`'s `capIntensityForRetreat(softPurr(0.2))`
call is kept as redundant defence in depth (same cap, same value, two
checks on the rule-based path) — the architectural single
enforcement point is the env layer, but local defensive coding in the
agent is preserved.

ADR 0008's first run (`phase2_baseline_norm__seed1__1780210056`) is
documented as invalidated and the re-run executed under the corrected
env is the resolution evidence for 0008 — see the Resolution section
below for ADR-0009-specific verification, and ADR 0008's own
resolution for the re-run verdict.

## Context — how this was found

ADR 0008's first training run (commit-time identifier
`phase2_baseline_norm__seed1__1780210056`,
`state_dict_sha256 = 15befadadfdb1ba01ee51aada88d1ce59487c42f5020970d70b02131e2c1e13a`)
landed `ADR_0008_DOES_NOT_RESOLVE`. Reward decomposition showed the
trained PPO agent lost to the rule-based baseline by Δ = −1.22 (58% from
opt_outs, 46% from engagement, ~0% from CSS). Per-state behaviour
diagnostics on the trained agent (see `litterbox/rl/analyse_phase2_baseline.py`
output for run `1780210056`) revealed an anomaly:

> In RETREATING state, the trained RL agent emitted engagement-action
> intensity = **0.701** (over 24 994 visits, 24 465 engagement-action
> ticks). The rule-based baseline on the same cats emitted RETREATING
> intensity = **0.200** (within the documented ≤ 0.3 cap).

ADR 0002, project documentation, and the source files themselves
describe `capIntensityForRetreat` as a hard ethical safeguard. A learned
agent emitting 0.70 should not have been possible if that safeguard is
enforced on the environment side. Tracing the actual code path showed
that it is not.

## The finding (cited against source)

### Where the cap is defined

`litterbox/src/agent/actions.ts`:

> Lines 3–9 — module docstring:
> ```
> Constraints (HARD-CODED ethical safeguards, not configurable):
>  - No prey-mimicry actions (explicitly out of scope for v0)
>  - Intensity capped at 0.3 when cat is RETREATING/LEAVING
>  - Slow blink protocol: Humphrey et al. 2020 …
> ```
>
> Lines 50–57 — the function:
> ```ts
> // Cap intensity for stress/retreat states (HARD LIMIT)
> export function capIntensityForRetreat(action: AgentAction): AgentAction {
>   if (action.type === 'side_glance' || action.type === 'soft_purr') {
>     return { ...action, intensity: Math.min(0.3, action.intensity) };
>   }
>   // Only side_glance and soft_purr allowed during retreat
>   return idle();
> }
> ```

The function is annotated **"HARD LIMIT"**. The module docstring lists
it under "HARD-CODED ethical safeguards, not configurable". Both
phrases imply systemic enforcement.

### Where the cap is invoked — the only site in the repository

`litterbox/src/agent/policy.ts`:

> Line 24 — import:
> ```ts
> import { idle, slowBlink, trill, softPurr, sideGlance, pause,
>          capIntensityForRetreat } from './actions';
> ```
>
> Lines 82–86 — call:
> ```ts
> // Priority 1b: Retreating/Leaving → constrained actions only
> if (obs.isRetreating) {
>   explanation = 'Cat is withdrawing. …';
>   lastAction = capIntensityForRetreat(softPurr(0.2));
>   return lastAction;
> }
> ```

`grep -rn capIntensityForRetreat src/ --include="*.ts"` returns those
two files only: the definition in `actions.ts:50`, the import in
`policy.ts:24`, and the single call in `policy.ts:84`. The cap is
applied inside the rule-based ChatCatAgent's `decide()` method,
*before* the action leaves the agent. It is not applied anywhere
between the agent and the simulator.

### Where the cap is NOT applied — the entire RL path

The RL agent's action travels through:

1. **Python `BaselineNormalizedChatcatEnv.step(action)`** —
   `litterbox/rl/env_continuous_baseline.py`, inherits
   `ChatcatGymContinuousEnv.step()` from
   `litterbox/rl/env_continuous.py`. Both forward the action to the
   bridge unchanged after argmax+clip decoding.
2. **TS `bridge.ts` step handler** — `litterbox/src/cli/bridge.ts`
   lines 113–121. Calls `buildAction(msg.action)` (lines 71–81), which
   only clips intensity to `[0, 1]` and looks up `duration_ms`. **No
   retreat-state check.**
3. **TS `env.ts` `step(action)`** — `litterbox/src/rl/env.ts` lines
   204–213:
   > ```ts
   > function step(action: AgentAction): StepResult {
   >   …
   >   const catState = simcat.tick(action);
   >   const intervention = ethicsMonitor.onTick(catState, action);
   >   …
   > ```
   `action` is forwarded to `simcat.tick()` directly, with no
   modification.
4. **TS `simcat.tick(action)`** — `litterbox/src/simcat/state-machine.ts`.
   The agent's intensity is *read* (lines 174–177 use it as a
   transition modifier) but never capped:
   > ```ts
   > // Low Agreeableness + high agent intensity → faster LEAVING
   > if ((state === 'LEAVING' || state === 'RETREATING') && agentIntensity > 0.3) {
   >   mod *= 1 + (1 - p.agreeableness) * agentIntensity * 0.5;
   > }
   > ```
   This is a *consequence* of high intensity (faster LEAVING via the
   agreeableness multiplier) — a reward-mediated learning signal — not
   an enforced ceiling.
5. **TS `ethicsMonitor.onTick(catState, action)`** —
   `litterbox/src/world/ethics-monitor.ts`. The monitor reads `action`
   to log into the session and to compute `EthicsIntervention`, but
   the intervention is a side-channel (`{forcePause, lockSession,
   dailyCapReached}`) that the *RL env* does not feed back into the
   action. Compare TickRunner's rule-based path
   (`src/world/tick-runner.ts:36–42`), which *does* override the
   agent's next-tick action on intervention — but in the RL path, env
   only logs intervention into `StepInfo` and the next action comes
   from the PPO network unchanged.

The net path for an RL-emitted action of intensity 0.70 in RETREATING
state is:

```
PPO network → decode_continuous_action → bridge.buildAction (clip [0,1])
            → env.step → simcat.tick(action with intensity 0.70)
            → reward computed from resulting catState
```

At no point is the action passed through `capIntensityForRetreat` or
any equivalent retreat-state check.

### What the rule-based path looks like for contrast

The rule-based ChatCatAgent goes through:

```
policy.decide() → capIntensityForRetreat(softPurr(0.2)) → returned to TickRunner
                                                       → simcat.tick(capped action)
```

The cap is enforced *inside* `agent.decide()` itself. Anything coming
out of that function is already constrained. The simulator (SimCat,
EthicsMonitor) was written assuming this invariant — there is no
duplicated check at the env layer because, for the only agent that
existed at the time, the policy.ts implementation guaranteed it.

## Why this is serious

### It contradicts the ethics-monitor's own stated contract

`litterbox/src/world/ethics-monitor.ts` line 2 — the file's docstring
opens with:

> ```
> Ethics Monitor — SEPARATE MODULE, agent CANNOT bypass
> ```

This is the project's foundational contract for the welfare subsystem.
The retreat-intensity cap is *the same class of constraint* as the
CSS≥5 forced-pause and the 24h lockout that the ethics monitor *does*
enforce — both are hard-coded welfare safeguards in the project's
public documentation. The cap was placed in `actions.ts`/`policy.ts`
at v0.1 because that was the only path that existed; the contract is
that **agent paths cannot bypass welfare enforcement**, and the RL
path bypasses this one.

### It is the same class of defect as ADR 0004

[ADR 0004](0004-state-machine-flicker-investigation.md) found that
CSS noise was computed independently in two places (agent path vs
ethics monitor path), so the two saw different CSS values for the
same tick. The fix was to make CSS deterministic and shared. The
present finding has the same shape: a welfare invariant is enforced
in one of two code paths but not the other, and the divergence is
silent (no error, no log, just a quietly-permitted high-intensity
action in a state where the project's documentation says it is
forbidden). The class of defect — "invariant exists in one branch,
not the system" — is repeating.

### It violates ADR 0002's safeguard #3, in spirit

[ADR 0002](0002-self-play-research-track.md) self-play safeguard #3
states that ethics-monitor enforcement must be the foundation, not a
property of any particular agent implementation. The current
arrangement makes the retreat-intensity cap a property of `policy.ts`'s
implementation, not of the env or the ethics-monitor. By construction,
a learned agent that has never seen `policy.ts` cannot inherit the
guarantee.

## Consequence for ADR 0008

ADR 0008's first training run optimised against an environment in
which `capIntensityForRetreat` was unenforced on the agent. The
trained PPO agent's policy was shaped by a reward landscape that
permitted RETREATING-intensity > 0.3 — exactly the regime the
project's documentation says should not be reachable by any agent.

This invalidates ADR 0008's first run as a baseline-normalisation
test:

- "Beat the rule-based baseline" was not a fair comparison: the
  baseline operated under the cap, the learned agent did not.
- The agent's lossy strategy in RETREATING (intensity 0.70) is not
  evidence that baseline-normalisation is the wrong reward design.
  It is evidence that the env was missing a constraint the reward was
  implicitly assuming.
- ADR 0008's existing artefacts can be kept for the file but cannot
  be used to resolve 0008. **A re-run after the enforcement fix is
  required before 0008 can resolve in either direction.**

## The open design choice (NOT pre-decided)

Two architectures could enforce the cap on all agent paths. Each has
trade-offs; the choice is deliberately not made in this ADR.

### Option A — Ethics-monitor as active enforcer

`EthicsMonitor.onTick(catState, action)` becomes `onTick(catState,
action) → { intervention, enforcedAction }`. The monitor returns the
action *as it must be executed*, with retreat caps and other hard
limits applied. `env.step` and `TickRunner` both call the monitor
*before* `simcat.tick(action)` and use the returned `enforcedAction`
for the simulator step.

Pros:
- The docstring contract ("agent CANNOT bypass") becomes literally
  true. Every action path passes through the monitor; the monitor
  owns the rules.
- New agent implementations (BC warm-start, alternative RL stacks)
  inherit enforcement automatically.
- Existing intervention logic (CSS≥5 pause, lockout, daily cap) is
  already in the monitor; the cap fits the same shape.

Cons:
- `EthicsMonitor` becomes responsible for action mutation, not just
  observation. Its current contract ("transparency is the feature";
  it logs what happened, doesn't change what happens to the cat) is
  expanded.
- The rule-based path's `policy.ts:84` cap becomes redundant; either
  remove it (one source of truth) or leave it (defence in depth, but
  divergence-risk re-emerges later).
- TickRunner's existing intervention-override logic
  (`tick-runner.ts:36-42`) would either move into the monitor or
  duplicate it.

### Option B — `env.step` consults monitor's rules, applies them inline

`EthicsMonitor` exposes a pure `wouldCap(catState, action) → AgentAction`
(or equivalent). `env.step` and `TickRunner` both call it before
`simcat.tick`. The monitor stays observation-only; the env layers
own the application.

Pros:
- `EthicsMonitor`'s current contract is preserved unchanged.
- Each agent-execution layer (RL env, rule-based tick-runner) owns
  its own enforcement step explicitly. Visible at the call site.
- Lower-risk refactor — monitor's existing interface is unaffected.

Cons:
- The enforcement logic lives in two places (env.step and
  tick-runner). The thing ADR 0004 warned against — invariant in
  multiple branches — re-emerges, just one level down.
- The contract "agent CANNOT bypass" becomes "env layer enforces; if
  you write a new env layer that forgets to call `wouldCap`, the
  guarantee disappears". The defect class is preserved structurally,
  just made one step harder to commit.
- `policy.ts:84` continues to apply its own cap separately. Three
  enforcement sites total.

### Option C (mentioned for completeness, not advocated)

Apply the cap inside `simcat.tick` itself. The simulator refuses to
process high-intensity actions in RETREATING/LEAVING states.

Pros:
- Single enforcement point, deepest possible.

Cons:
- Conflates simulation and ethics. The simulator's job is to be a
  faithful cat model under arbitrary stimuli; reasoning about which
  stimuli are *allowed* belongs to the welfare layer. Embedding cap
  here makes the simulator a moral agent, which it should not be.
- Loses the audit trail: ethics-monitor would log the action the
  agent *requested*; simcat would silently behave as if a different
  action was taken. Transparency degrades.

## What this ADR does not decide

- Which option (A, B, or C) is chosen.
- Whether the rule-based `policy.ts:84` cap is removed or kept as
  defence-in-depth after the env-layer fix lands.
- Whether other "HARD-CODED" constraints in `actions.ts` documentation
  ("No prey-mimicry actions") need the same audit. They likely do —
  this ADR triggers a broader review of which welfare invariants live
  in `policy.ts` vs the env.

## What follows

1. Eirik chooses the enforcement architecture (A / B / C / something
   else).
2. Resolution of 0009 documents the choice and the patch.
3. ADR 0008's first run is documented as invalidated (existing
   artefacts referenced for the file but not load-bearing).
4. ADR 0008 is re-run with `--seed 1`, against the corrected env.
   The pre-registered success criteria in 0008 are unchanged — the
   thresholds are about the policy's quality, not about the
   environment's correctness. The re-run is evaluated against the
   *same* criteria; the resolution will reference both the original
   (invalidated) artefacts and the corrected-env artefacts side by
   side.

## Resolution (2026-05-31)

### Architecture chosen

**Option A — ethics-monitor as active enforcer.**

A new method on `EthicsMonitor`:

```ts
enforce(stateBeforeTick: CatState, action: AgentAction)
    → { enforced: AgentAction; capInfo: CapEnforcement }
```

The monitor is called *before* `simcat.tick()` on every action path.
The `enforced` action is what reaches the simulator and what is logged
in subsequent `onTick()` calls. The `capInfo` record (always emitted)
exposes whether the cap fired, the original intensity and type, the
enforced intensity and type, and which rule fired (`""` if no cap).

The first rule implemented is the retreat-state restriction
formerly only enforced inside `policy.ts:84`'s
`capIntensityForRetreat()` call:

- If the cat is in `RETREATING` or `LEAVING`:
  - Allowed action types: `side_glance`, `soft_purr` only.
    Anything else becomes `idle`.
  - Allowed-type intensity capped to 0.30.
- Otherwise: pass-through (no modification).

Defence-in-depth in `policy.ts:84` is **kept**: the rule-based
ChatCatAgent still calls `capIntensityForRetreat()` in its `decide()`,
producing an already-compliant action. `enforce()` re-applies the cap
and finds `cap_applied=false` for rule-based actions — the architectural
single point is at the env layer; the agent-side check is local
defensive coding that does not hurt and provides explicit
documentation in the policy code.

### Trade-offs accepted

Per the three options the open ADR considered:

- **Option A (chosen)** accepts that `EthicsMonitor` now mutates
  actions in addition to logging interventions. Its docstring contract
  ("agent CANNOT bypass") becomes literally true — every action path
  must call `enforce()` before `simcat.tick()`. Adding new agent
  implementations (BC warm-start, alternative RL stacks) automatically
  inherits enforcement.
- **Option B rejected**: would have repeated the ADR-0004-class
  defect (invariant in multiple env-layer call sites; "if you write a
  new env layer that forgets to call wouldCap, the guarantee
  disappears").
- **Option C rejected**: conflates simulation and ethics; loses
  audit trail of what the agent requested vs what was executed.

### Code changes (committed in the same commit as this resolution)

- `src/world/ethics-monitor.ts`: added `enforce()` method,
  `CapEnforcement` type, constants `RETREAT_INTENSITY_CAP = 0.3` and
  `RETREAT_ALLOWED_TYPES = {'side_glance', 'soft_purr'}`.
- `src/rl/env.ts` `step()`: calls `ethicsMonitor.enforce(stateBeforeTick,
  action)` before `simcat.tick()`, uses `enforced` action everywhere
  downstream, and exposes `capInfo` in `StepInfo.ethics_enforcement`.
- `src/world/tick-runner.ts` `runOneTick()`: same — calls `enforce()`
  between `agent.decide()` and `simcat.tick()`.
- `src/cli/bridge.ts` `runRuleBasedEpisode()`: same, for the
  baseline-rollout path used by ADR 0008's baseline-normalised reward.
- `src/cli/verify-adr0009.ts`: 8 hand-tested cases of the
  enforcement gate. All pass.
- `rl/verify_adr0009_e2e.py`: end-to-end verification by replaying
  the invalidated ADR-0008-1 model through the corrected env.

### Verification

**Unit-level (8/8 hand-tested cases pass):**

```
PASS  side_glance @ 0.70 in RETREATING       → side_glance @ 0.30  (retreat_intensity_cap)
PASS  soft_purr   @ 0.95 in LEAVING          → soft_purr   @ 0.30  (retreat_intensity_cap)
PASS  trill       @ 0.50 in RETREATING       → idle        @ 0.00  (retreat_type_not_allowed)
PASS  slow_blink  @ 0.20 in RETREATING       → idle        @ 0.00  (retreat_type_not_allowed)
PASS  side_glance @ 0.20 in RETREATING       → pass through         (already ≤ 0.30)
PASS  side_glance @ 0.30 in RETREATING       → pass through         (boundary; ≤ not <)
PASS  trill       @ 0.95 in ENGAGING         → pass through         (not a retreat state)
PASS  side_glance @ 0.95 in RESTING          → pass through         (the ADR-0008-1 pattern; intentional)
```

The last case is significant: agent's RESTING-state behaviour
(side_glance @ 0.9 over 64% of all ticks, the dominant trained-policy
pattern from ADR 0008 Q3) is **NOT** affected by this cap. The cap
fires only in retreat states. Whether the RESTING-state behaviour is
itself something that should be capped is **out of scope here**; it's
a separate audit (the ADR-0008 first run showed welfare metrics
didn't worsen from it, but ethics intent says don't call a sleeping
cat — a separate enforcement rule, separate ADR if pursued).

**End-to-end (replay invalidated ADR-0008-1 model under corrected env):**

5 episodes, master_seed=1, total 90 000 steps.

| | |
|---|---:|
| cap_applied (total) | 1971 / 90 000 = 2.19% |
| `retreat_type_not_allowed` | 1915 |
| `retreat_intensity_cap` | 56 |
| Mean overshoot per cap | 0.6938 (matches Q3's reported RETREATING intensity ~0.70) |
| Worst single attempt | 1.0 → 0.0 (slow_blink @ 1.0 in RETREATING → idle) |

First five cap events (ep0):
```
step 1021  side_glance @ 1.0000  →  side_glance @ 0.3000  (retreat_intensity_cap)
step 1022  slow_blink  @ 1.0000  →  idle        @ 0.0000  (retreat_type_not_allowed)
step 1023  slow_blink  @ 1.0000  →  idle        @ 0.0000  (retreat_type_not_allowed)
step 1024  slow_blink  @ 1.0000  →  idle        @ 0.0000  (retreat_type_not_allowed)
step 1025  slow_blink  @ 1.0000  →  idle        @ 0.0000  (retreat_type_not_allowed)
```

This is exactly the welfare violation Q3 detected. Now intercepted at
the env layer, logged, and the simulator never sees the raw 1.0
intensity in retreat.

**Existing test suite:** `pnpm test` reports 36/36 pass — the
rule-based path's trajectories are unchanged because `policy.ts:84`
already capped, so `enforce()` is a no-op there (`cap_applied=false`).
The new gate only fires when an agent tries to overshoot, which the
rule-based path does not.

**Bridge determinism:** `pnpm exec tsx src/cli/bridge-determinism.ts`
→ BIT-IDENTICAL across 500 steps. In-process env and bridge subprocess
both call `enforce()`; same inputs produce same outputs on both paths.

### Note on previously-committed smoke hashes

ADR 0007 / phase 1 / phase 1b smoke-test hashes reference an
unenforced env. The smoke runs themselves remain valid as records of
what the env produced *then*; reproducing them now yields different
hashes because random actions in RETREATING with intensity > 0.3 are
now intercepted. This is the intended behaviour of the fix. The
hashes are historical records, not contracts; their commit messages
already documented them as "smoke hashes" rather than acceptance
criteria. No re-update of those commit messages is needed — the ADR
that motivated the hashes (0007) is already resolved against a
different question.

### Defects of the same class — audit deferred

`actions.ts` documentation lists three "HARD-CODED ethical safeguards,
not configurable":

1. **No prey-mimicry actions** — currently enforced by absence: there
   are no prey-mimicry actions in the `AgentActionType` union, so no
   action path can emit one. Enforcement is via type system at compile
   time; no runtime gate needed.
2. **Intensity capped at 0.3 when cat is RETREATING/LEAVING** — this
   ADR's fix. Now enforced in `ethicsMonitor.enforce()`.
3. **Slow blink protocol: half-blink → eye narrow → eye closure** —
   currently a visualisation convention in `viz/agent-sprite.ts`. Not
   a welfare invariant in the same sense; descriptive of the rendering.

`policy.ts` lists additional rules in its docstring (lines 14–17):
priority pause at CSS≥5, 60-min cooldown at CSS≥6, daily session cap.
**CSS≥5 forced pause, CSS≥6 cooldown, and daily cap are already
enforced by `ethicsMonitor.onTick()` via the `EthicsIntervention` side
channel** — but on the RL path, the intervention is logged into
`StepInfo` and NOT applied to the next action. The rule-based path's
TickRunner *does* override the next action on intervention; the RL
path does not. This is a separate audit gap — same class of defect
(invariant enforced in one of two paths) — but the consequence is
different: the RL agent sees the intervention in observation/info but
is allowed to choose its own next action. Whether that should also be
hard-enforced (force-idle the agent's next action under intervention)
is **deferred to a follow-on ADR**. It does not block 0008.

### What follows

- ADR 0008's first run (`phase2_baseline_norm__seed1__1780210056`,
  state_dict_sha256 `15befadadfdb…`) is invalidated as
  baseline-normalisation evidence. Its artefacts are retained for the
  record (analysis showed exactly the welfare bypass this ADR
  documents and fixes).
- ADR 0008 has been re-run with the corrected env. See ADR 0008's
  Resolution section for the verdict against the same pre-registered
  criteria (NON_TRIVIAL classifier + climb-and-holds + better-than-
  baseline). No threshold was edited.

## References

- [ADR 0002](0002-self-play-research-track.md) — self-play track,
  safeguard #3 (ethics-monitor anchored to real CSS, by extension
  the broader principle that welfare enforcement is systemic, not
  per-agent).
- [ADR 0004](0004-state-machine-flicker-investigation.md) — same
  class of defect (invariant in one of two code paths, silent
  divergence). Precedent for this ADR's posture (document before fix).
- [ADR 0007](0007-reward-calibration.md) — the resolution that
  motivated ADR 0008 and indirectly led to discovering this. 0007's
  closing line: "*Ikke fordi det er det vi håpet, men fordi det er
  det som er sant og vi kan bevise det.*" The same disposition
  applies here: the v0.1 architecture had a hole, the simulator-first
  discipline found it before a real cat was involved, and documenting
  it cleanly is the right move regardless of how inconvenient the
  re-run is.
- `litterbox/src/agent/actions.ts:50–57` — definition site.
- `litterbox/src/agent/policy.ts:24, 84` — sole invocation site.
- `litterbox/src/world/ethics-monitor.ts:2` — the "cannot bypass"
  contract this ADR documents being violated.
- `litterbox/rl/env_continuous_baseline.py`,
  `litterbox/src/cli/bridge.ts`,
  `litterbox/src/rl/env.ts`,
  `litterbox/src/simcat/state-machine.ts:174–177` — the RL path
  segments that do not apply the cap.
- ADR 0008 trained agent: `/tmp/chatcat-rl-runs/phase2_baseline_norm__seed1__1780210056/agent.pt`
  (`state_dict_sha256: 15befadadfdb1ba01ee51aada88d1ce59487c42f5020970d70b02131e2c1e13a`),
  RETREATING engagement intensity 0.701 over 24 994 visits — the
  empirical observation that triggered this investigation.

## Reproducibility

This ADR documents a code-path inspection, not a measurement. The
finding reproduces from `git grep capIntensityForRetreat
litterbox/src/ --include='*.ts'` against the repository at any commit
since `2f3660c` (2026-05-07, "feat: add ChatCatAgent policy v0 (rule-based,
not learned)" — the commit that introduced `policy.ts`, whose own
message lists "intensity caps during retreat" as a hard-coded ethical
safeguard); the function has had exactly one call site for its entire
lifetime.

The empirical signature (RL agent emitting RETREATING intensity > 0.3
without env-layer modification) reproduces deterministically from
`litterbox/rl/analyse_phase2_baseline.py` against the agent.pt
referenced above. Both inspections are free; neither requires a new
training run.
