# ADR 0018 — Phase 2 run-note (LOCKED before generation)

Companion to `0018-offsubstrate-sigma-scale-replication.md`. This note records the
concrete instantiation of the pre-registered Phase 2 seed-generation, locked BEFORE
any real run per the A2 firewall. Committing this note IS the lock. Nothing about
σ, P1, P2, or P3 is computed in this phase — Phase 2 only generates and stores the
per-episode return curves.

## Task (locked)

- **Environment: `HalfCheetah-v4`** (gymnasium). Chosen over Hopper-v4 for a
  disk-verified reason, not preference: HalfCheetah episodes are **fixed 1000 steps**
  (termination never fires; truncation at 1000 — verified this session). Uniform
  episodes-per-update keeps the update→episode window-unit mapping (locked in ADR
  0018) clean and faithful to chatcat's fixed-structure σ_init. Hopper terminates
  early on falling → variable-length episodes → variable episodes-per-update, which
  would muddy the mapping. Locked NOW, before seeing any σ.

## Seeds (locked, enumerated)

- **N = 15, seeds = {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20}.**
  Identical enumeration to ADR 0012/0013's N=15 seed-set — deliberately mirrored for
  comparability, not drawn to taste.

## Algorithm & config (locked, unmodified upstream script)

- **Script: CleanRL `ppo_continuous_action.py`, byte-unmodified.**
  - upstream: `vwxyzjn/cleanrl`, commit `35896b1fefa9898b904f7e09bcbe6e168e15d2a9`
  - sha256: `326dd8678bf9cc51abec833eb551ef2409a3804d604b689e1f0a084eca41f655`
- **All defaults, nothing tuned:** `total_timesteps=1000000`, `num_steps=2048`,
  `num_envs=1`, `learning_rate=3e-4`, `torch_deterministic=True`.
- **Device: CPU** (`--no-cuda`; no MPS) — chosen for run-to-run determinism, not
  speed. Measured ~2500 SPS → ~6.7 min/seed, ~1.7 h for all 15.
- **No wandb** (`--no-track`), no video (`--no-capture-video`). Auth-free.

## Pinned environment (provenance)

- python 3.11.15, torch 2.4.1, gymnasium 0.29.1, mujoco 3.1.6, numpy 1.26.4,
  tyro 0.8.6, imageio 2.34.2, tensorboard 2.17.1 (isolated uv venv).

## Outputs

- Per-episode `(global_step, episodic_return)` extracted verbatim from each run's
  tfevents (`charts/episodic_return`) to `curves/seed<NN>.csv`.
- Run directory: `~/chatcat-offsubstrate-run/` — **outside the chatcat repo.** This
  Phase does NOT touch `paper/analysis/` (SCX59-frozen) or the arXiv bundle.

## update→episode mapping recipe (as locked in ADR 0018, recorded for the analysis step)

- Update boundaries at `global_step = k · num_steps = k · 2048`.
- Episodes end at `global_step = m · 1000` (fixed HalfCheetah length).
- Rolling-100 buffer = trailing 100 completed episodes; buffer-full = 100th episode.
- `ep_init` window = first 51 updates after buffer-full; σ_init = inter-update SD of
  the rolling-100 smoothed return over that window. (Computed in the SEPARATE
  analysis step against the committed ADR — NOT in this Phase.)
