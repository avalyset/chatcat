# litterbox/rl/ — Python RL stack

Python-side scaffolding for the v0.2 self-play track (ADR 0002). Sits on
top of the stdio bridge in [`../src/cli/bridge.ts`](../src/cli/bridge.ts),
which wraps the TS [`ChatcatEnv`](../src/rl/env.ts).

TS owns SimCat, the EthicsMonitor, the reward function, and the
observation/action encoders. Python owns the PPO learner. The bridge is
IPC, not architecture — there is exactly one SimCat implementation, and
it is in TypeScript.

## Files

- [`env.py`](env.py) — `ChatcatGymEnv`, a `gymnasium.Env` subclass that
  spawns the TS bridge as a subprocess and translates the gym contract
  into NDJSON over stdio. Action space is `Discrete(24)` (6 types × 4
  intensity bins); rationale documented in the module docstring.
- [`drift_guard.py`](drift_guard.py) — verifies that a fixed action
  sequence produces a bit-identical trajectory through the gym wrapper
  vs directly through the bridge subprocess. Companion to the fase 0
  bridge-determinism check; together they cover bridge + wrapper.
- [`ppo_chatcat.py`](ppo_chatcat.py) — CleanRL `ppo.py` adapted for
  `ChatcatGymEnv`. Algorithm unchanged. Used as the fase 1 smoke test
  (10k timesteps default — enough for one optimizer update, not enough
  for any conclusion about learning).

## Running

All three scripts use PEP 723 inline metadata; run via `uv`:

```sh
cd litterbox
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
