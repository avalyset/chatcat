# Phase 2 runbook — ADR 0007 resolution path

> **Superseded (2026-05-31).** This runbook was written before the
> ADR 0007 training run was executed and described one possible resolution
> path. ADR 0007 was subsequently resolved against different findings than
> the runbook anticipated (the form-choice question closed negatively;
> see [ADR 0007's resolution](../../docs/decisions/0007-reward-calibration.md)),
> and the work continued through ADRs 0008 and 0009 along a path this
> runbook does not describe. Kept here for the historical record. **Do
> not follow as instructions.** For the current state of the RL stack,
> see [`README.md`](README.md).

---

One-shot, autonomous execution. Two commands, one decision, optional
ADR resolution. No epoch-by-epoch monitoring.

## Prerequisites (already verified by phase 0 / 1 / 1b)

- `pnpm exec tsx src/cli/bridge.ts` runs and accepts stdio JSON.
- `uv run rl/drift_guard_continuous.py` → BIT-IDENTICAL.
- `pnpm test` → 36 / 36.

If any of these fails, do not start phase 2. Phase 2 assumes a known-good
training pipeline.

## Step 1 — Train (one command, autonomous)

```sh
cd litterbox
uv run rl/train_phase2.py --seed 1
```

Expected runtime: 30–90 min on Apple Silicon (~2k sps PPO loop measured
in fase 1b smoke; default 5M total timesteps). The script prints a
progress line every 10 updates; full per-update metrics go to
`metrics.jsonl` for later inspection if needed.

Output: `/tmp/chatcat-rl-runs/phase2__seed1__<timestamp>/`
- `agent.pt` — final model state_dict
- `metrics.jsonl` — per-update training metrics
- `run_config.json` — all args + reward parameters

Determinism: re-running with `--seed 1` should produce a bit-identical
`agent.pt` (verifiable via `state_dict_sha256` printed at the end).

## Step 2 — Grid scan + classify (one command)

```sh
uv run rl/grid_scan_phase2.py --model-path /tmp/chatcat-rl-runs/phase2__seed1__<timestamp>/agent.pt
```

Runs 100 evaluation episodes through the same crossover-reward env, then
prints a classification under the pre-registered degeneracy thresholds:

| Label | Means |
|---|---|
| `NON_TRIVIAL` | Agent learned a state-conditional, non-degenerate policy. Resolution of ADR 0007 is unblocked. |
| `IDLE_OUT` | Agent collapsed to constant idle. ADR 0007 calibration revision: lower β or raise engagement_scale. |
| `PUSH_THE_CAT` | Agent collapsed to constant high-intensity engagement. ADR 0007 calibration revision: raise β or lower engagement_scale. |
| `TRIVIAL` | Agent did not learn state-conditional behaviour (random-like or constant-action). NOT a reward-calibration problem — investigate PPO hyperparameters / training length / network capacity. |

Also prints the three reward-form scores (`adr0002_max_css`,
`mean_css`, `high_css_share`) on the trained-agent trajectories.
This is the data ADR 0007 deferred for choosing the form — under a
trained policy that decorrelates the three CSS aggregates, the forms
differ in ways the random baseline could not expose.

The full pre-registered classification logic and thresholds are
documented in the docstring of `grid_scan_phase2.py`. They are FROZEN —
editing them after seeing a result is not a calibration decision, it
is post-hoc rationalisation, and ADR 0007 (per ADR 0005 / 0006
precedent) is explicit that such edits invalidate the verification.

## Step 3 — Decision

Read the printed classification. Then:

### If `NON_TRIVIAL`

Draft `docs/decisions/0007-reward-calibration.md` resolution:

- Status: `Resolved (<date>)`
- Resolution section: describe what was trained (commit hash of
  `train_phase2.py`, master seed, wall time, total timesteps,
  `state_dict_sha256`), the agent's classification metrics, and the
  three-form reward scoring under the trained agent.
- If reward-form scoring shows that `mean_css` or `high_css_share`
  give a meaningfully different gradient signal under the trained
  policy, name a single form as the v0.2 calibration. If all three
  agree (high pairwise correlation as in the random baseline), keep
  `adr0002_max_css` for fidelity to ADR 0002 wording.
- Commit + push.
- Optionally: freeze the run on OSF as a child component of `a9mnv`
  (the ADR 0006 component), same pattern as 0006 — that is the
  "frozen externally" step, not the resolution itself.

### If `IDLE_OUT` or `PUSH_THE_CAT`

ADR 0007 named exactly these as the failure modes. The calibration
needs revision *before* a second training attempt.

- Open ADR 0007, document the failed run and its classification.
- Decide a new `(α, β, engagement_scale_mult)` tuple — note that
  α had almost no effect in the random-baseline grid scan, so β and
  `engagement_scale_mult` are the levers. Document the rationale.
- Edit `CROSSOVER_*` constants in `train_phase2.py` (these are the
  single source of truth; do not pass via CLI for a re-run — the
  point is to commit the new calibration).
- Commit + push the revised constants + an ADR 0007 amendment.
- Re-run step 1.

ADR 0007's escalation rule: if two consecutive runs under the same
calibration both collapse to a corner, the reward FORMULATION (not
just the parameters) must be revisited — e.g., z-score-normalised
components, or a constraint-style reward.

### If `TRIVIAL`

PPO did not learn. This is NOT a reward-calibration issue. Investigate:

- Training length (try `--total-timesteps 20_000_000`).
- Network capacity (Agent currently uses 64-unit hidden layers).
- Hyperparameters (`--learning-rate`, `--num-steps`, `--update-epochs`).
- Bridge throughput is fine (fase 0 verified), so wall time is policy-side.

Document the investigation and decision in a new ADR (don't mutate
ADR 0007 for a non-reward-calibration finding).

## Notes on autonomous execution

- The training command prints progress every 10 updates; the
  trajectory and metrics are written to disk as they happen, so if the
  process is interrupted (Ctrl+C handled gracefully) the partial model
  is saved.
- The grid-scan command runs offline against the saved model; you can
  re-run it any number of times to inspect a trained agent.
- Re-running `train_phase2.py --seed 1` always produces the same
  `agent.pt` modulo wall time. Re-running `grid_scan_phase2.py
  --seed 1` against the same model always produces the same
  classification.

## File map (committed)

- `train_phase2.py` — phase 2 training, locked to ADR 0007 crossover regime.
- `grid_scan_phase2.py` — post-training classifier with pre-registered degeneracy thresholds.
- `PHASE2-RUNBOOK.md` — this file.
- `env_continuous.py`, `ppo_chatcat_continuous.py`, `drift_guard_continuous.py` — phase 1b training stack (env, smoke PPO, wrapper drift guard).
- `env.py`, `ppo_chatcat.py`, `drift_guard.py` — phase 1 reference (Discrete).
- `../src/cli/bridge.ts` — stdio bridge (phase 0); reads `CHATCAT_ALPHA` / `CHATCAT_BETA` / `CHATCAT_ENG_SCALE_MULT` env vars for reward param overrides.
