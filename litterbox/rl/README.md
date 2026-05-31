# litterbox/rl/ — Python RL stack

Python-side scaffolding for the v0.2 self-play track (ADR 0002). Sits on
top of the stdio bridge in [`../src/cli/bridge.ts`](../src/cli/bridge.ts),
which wraps the TS [`ChatcatEnv`](../src/rl/env.ts).

TS owns SimCat, the EthicsMonitor (including the
[`EthicsMonitor.enforce()`](../src/world/ethics-monitor.ts) gate added in
ADR 0009), the reward function, and the observation/action encoders.
Python owns the PPO learner. The bridge is IPC, not architecture — there
is exactly one SimCat implementation, and it is in TypeScript.

## Files

### ADR 0008 — baseline-normalised reward (executed, Resolved: DOES_NOT_RESOLVE)

The three-run training stack used to produce
[ADR 0008's resolution](../../docs/decisions/0008-reward-baseline-normalization.md).
ADR 0008 closed negatively (baseline normalisation alone is informative
but not stably learnable); the files remain for reproducibility and any
follow-on ADR (0010) that builds on the same env wrapper.

- [`env_continuous_baseline.py`](env_continuous_baseline.py) —
  `BaselineNormalizedChatcatEnv`. On reset, queries
  `bridge.rule_based_episode` for the rule-based ChatCatAgent's reward
  on the same `(traits, simcat_seed)`; subtracts at the terminal step
  so the episode-summed reward equals R_agent_total − R_baseline.
- [`train_phase2_baseline.py`](train_phase2_baseline.py) — CleanRL
  `ppo_continuous_action` adapted; crossover-regime params locked
  (`α=1.0, β=0.5, scale_mult=5.0`).
- [`grid_scan_phase2_baseline.py`](grid_scan_phase2_baseline.py) —
  classifier from `grid_scan_phase2` plus ADR 0008's two additional
  criteria (climb-and-holds from `metrics.jsonl`, better-than-baseline
  from eval rewards). Thresholds locked: `CLIMB_THRESHOLD=1.0`,
  `HOLDS_TOLERANCE=0.5`, `BETTER_THAN_BASELINE_MEAN=1.0`.
- [`analyse_phase2_baseline.py`](analyse_phase2_baseline.py) — three
  diagnostic analyses on a trained-agent run (episode-length, reward
  decomposition, per-state intensity comparison). The analysis that
  surfaced the ADR 0009 finding before any 0008 resolution was written.

### ADR 0009 — ethics-enforcement-point verification (Resolved)

- [`verify_adr0009_e2e.py`](verify_adr0009_e2e.py) — end-to-end check
  that `EthicsMonitor.enforce()` actually intercepts a known-overshoot
  RL agent. Replays the pre-0009-fix ADR-0008 first-run model
  (which emitted RETREATING intensity 0.701) through the corrected
  env; reports cap events and overshoot statistics.

(Companion unit-level check, on the TS side, is
[`../src/cli/verify-adr0009.ts`](../src/cli/verify-adr0009.ts) —
8 hand-tested cases of `EthicsMonitor.enforce()`.)

### ADR 0007 — reward calibration (executed, Resolved)

The phase 2 training stack referenced by
[ADR 0007's resolution](../../docs/decisions/0007-reward-calibration.md).

- [`train_phase2.py`](train_phase2.py) — full PPO training in ADR 0007's
  crossover regime (α=1.0, β=0.5, scale_mult=5.0). Default 5M timesteps.
- [`grid_scan_phase2.py`](grid_scan_phase2.py) — post-training classifier
  with pre-registered degeneracy thresholds (IDLE_OUT / PUSH_THE_CAT /
  TRIVIAL / NON_TRIVIAL). Run against a saved `agent.pt`.

### Phase 1b training-path scaffolding (smoke; still useful as a sanity check)

- [`env_continuous.py`](env_continuous.py) — `ChatcatGymContinuousEnv`,
  the env used for all phase 2 training. Action space is
  `Box(low=0, high=1, shape=(7,), dtype=float32)` — 6 type-score dims
  (argmax decodes to action type) + 1 intensity dim (clipped to [0,1]).
- [`drift_guard_continuous.py`](drift_guard_continuous.py) — verifies
  that the continuous wrapper's `Box(7,)` → `(type, intensity)` decode is
  consistent between gym wrapper and direct-bridge paths.
- [`ppo_chatcat_continuous.py`](ppo_chatcat_continuous.py) — CleanRL
  `ppo_continuous_action.py` smoke test (10k timesteps).

### Phase 1 reference (Discrete, retired)

- [`env.py`](env.py) — `ChatcatGymEnv` with `Discrete(24)` (6 types × 4
  intensity bins). Kept for reference; superseded by `env_continuous.py`.
- [`drift_guard.py`](drift_guard.py) — drift guard for the Discrete
  wrapper.
- [`ppo_chatcat.py`](ppo_chatcat.py) — CleanRL `ppo.py` smoke for the
  Discrete env.

### Historical runbook

- [`PHASE2-RUNBOOK.md`](PHASE2-RUNBOOK.md) — runbook for ADR 0007's
  resolution path. **Superseded**: 0007 is resolved; subsequent work
  (0008, 0009) followed a different path than the runbook anticipated.
  Kept for the historical record. Do not follow as instructions.

## Running

All scripts use PEP 723 inline metadata; run via `uv`:

```sh
cd litterbox

# Drift guards (cheap correctness checks)
uv run rl/drift_guard.py
uv run rl/drift_guard_continuous.py

# Phase 2 (ADR 0007) reproduction
uv run rl/train_phase2.py --seed 1
uv run rl/grid_scan_phase2.py --model-path <agent.pt>

# Phase 2 baseline-norm (ADR 0008) reproduction
uv run rl/train_phase2_baseline.py --seed 1
uv run rl/grid_scan_phase2_baseline.py --model-path <agent.pt>

# ADR 0009 end-to-end enforcement check
uv run rl/verify_adr0009_e2e.py
```

PPO runs write artefacts under `/tmp/chatcat-rl-runs/` (kept out of the
repo). Each run prints `state_dict_sha256`; re-running with the same
`--seed` reproduces the hash exactly.

## Dependencies

- `pnpm` and `tsx` in PATH (bridge spawn).
- `uv` in PATH (script runner).
- macOS / Linux. No Windows-specific paths.
