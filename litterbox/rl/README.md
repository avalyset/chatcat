# litterbox/rl/ — Python RL stack

Python-side scaffolding for the v0.2 self-play track (ADR 0002). Sits on
top of the stdio bridge in [`../src/cli/bridge.ts`](../src/cli/bridge.ts),
which wraps the TS [`ChatcatEnv`](../src/rl/env.ts).

TS owns SimCat, the EthicsMonitor, the reward function, and the
observation/action encoders. Python owns the PPO learner. The bridge is
IPC, not architecture — there is exactly one SimCat implementation, and
it is in TypeScript.

## Files

**Phase 2 training (committed, not yet executed):**
- [`train_phase2.py`](train_phase2.py) — full PPO training in ADR 0007's
  crossover regime (α=1.0, β=0.5, engagement_scale_mult=5.0). Default
  5M timesteps (~30–90 min on Apple Silicon). Locked-in reward
  parameters; not configurable via CLI on purpose — the calibration
  choice belongs in this file as the single source of truth.
- [`grid_scan_phase2.py`](grid_scan_phase2.py) — post-training
  classifier with pre-registered degeneracy thresholds (IDLE_OUT /
  PUSH_THE_CAT / TRIVIAL / NON_TRIVIAL). Run against a saved agent.pt.
- [`PHASE2-RUNBOOK.md`](PHASE2-RUNBOOK.md) — exact command sequence
  for the training week, with the decision tree based on the
  classifier's verdict.

**Training path scaffolding (fase 1b+):**
- [`env_continuous.py`](env_continuous.py) — `ChatcatGymContinuousEnv`,
  the env used for fase 2 training. Action space is
  `Box(low=0, high=1, shape=(7,), dtype=float32)` — 6 type-score dims
  (argmax decodes to action type) + 1 intensity dim (clipped to [0,1]).
  Standard "categorical via continuous logits" pattern for envs that
  demand a Box space. Rationale documented in the module docstring.
- [`drift_guard_continuous.py`](drift_guard_continuous.py) — verifies
  that the continuous wrapper's Box(7,) → (type, intensity) decode is
  consistent between gym wrapper and direct-bridge paths. Test actions
  include both bounded and Normal-distributed samples to cover what
  PPO actually emits.
- [`ppo_chatcat_continuous.py`](ppo_chatcat_continuous.py) — CleanRL
  `ppo_continuous_action.py` adapted for `ChatcatGymContinuousEnv`.
  Algorithm unchanged. Fase 1b smoke (10k timesteps).

**Reference / pensjonert (fase 1):**
- [`env.py`](env.py) — `ChatcatGymEnv` with `Discrete(24)` (6 types × 4
  intensity bins). Kept for reference; intensity-axis approximation
  superseded by the continuous form above.
- [`drift_guard.py`](drift_guard.py) — drift guard for the Discrete
  wrapper.
- [`ppo_chatcat.py`](ppo_chatcat.py) — CleanRL `ppo.py` adapted for
  the Discrete env.

## Running

All scripts use PEP 723 inline metadata; run via `uv`:

```sh
cd litterbox

# Continuous (training path)
uv run rl/drift_guard_continuous.py
uv run rl/ppo_chatcat_continuous.py [--seed 1] [--total-timesteps 10000]

# Discrete (reference)
uv run rl/drift_guard.py
uv run rl/ppo_chatcat.py [--seed 1] [--total-timesteps 10000]
```

The PPO run writes artefacts under `/tmp/chatcat-rl-runs/` (kept out of
the repo). Each run prints:
- `trajectory_sha256` — hash of the per-step (action, reward, done) log,
  used for determinism verification across runs.
- `state_dict_sha256` — hash of the final model weights.

Re-running with the same `--seed` should reproduce both hashes exactly.

## What this does NOT do

- It is not training. ADR 0007 deferred reward calibration to a real
  trained agent; the smoke test is the path-clearing step before that.
- It does not implement the post-training grid scan (that is fase 2 /
  ADR 0007 resolution).
- It does not pick the final action-space representation. The
  `Discrete(24)` choice is a smoke-test convenience for CleanRL's
  out-of-the-box ppo.py. Fase 2 may move to continuous PPO or a library
  with native Tuple/MultiDiscrete support.

## Dependencies

- `pnpm` and `tsx` in PATH (bridge spawn).
- `uv` in PATH (script runner).
- macOS / Linux. No Windows-specific paths.
