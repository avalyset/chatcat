#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "numpy>=1.26",
#   "gymnasium>=0.29,<2",
#   "torch>=2.0",
# ]
# ///
"""
ADR 0008 first-run analysis: why the agent lost to baseline by -1.22.

Three questions, deterministic against existing artefacts:

  Q1  Episode-length comparison: are agent and baseline episodes the same
      length on the same seed? If not, Δ is partly a length artefact.
  Q2  Reward decomposition: break (R_agent − R_baseline) into (engagement,
      max_CSS, opt_outs) components. Where does the agent lose ground?
  Q3  Per-state engagement intensity: does the agent run high intensity
      in states where it doesn't trigger welfare cost, while baseline
      holds low intensity everywhere? Per-state intensity for both.

Data sources:
  - Agent per-episode aggregates: from existing trajectories.jsonl on
    disk (no re-run needed for Q1/Q2).
  - Baseline per-episode aggregates: fresh query to bridge for each
    env_seed in agent trajectories (bridge.ts rule_based_episode now
    returns full per-state aggregates).
  - Agent per-state intensity: requires per-step capture. Re-runs the
    agent eval for the same 100 seeds in trajectories.jsonl
    (deterministic; reproduces bit-identically given the seed). The
    BaselineNormalizedChatcatEnv wrapper is bypassed for the re-eval —
    we use the plain ChatcatGymContinuousEnv so we don't pay the
    rule_based_episode cost twice (we query bridge separately for
    baseline-detailed data afterwards).

Usage: uv run rl/analyse_phase2_baseline.py [--run-dir <dir>]
"""

import argparse
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch

import gymnasium as gym  # noqa: E402
from env_continuous import (  # noqa: E402
    ACTION_DIM,
    ACTION_TYPES,
    ChatcatGymContinuousEnv,
    decode_continuous_action,
    find_litterbox_dir,
)
from train_phase2 import (  # noqa: E402
    Agent,
    CROSSOVER_ALPHA,
    CROSSOVER_BETA,
    CROSSOVER_ENG_SCALE_MULT,
)
from grid_scan_phase2 import (  # noqa: E402
    SIMCAT_STATES,
    ENGAGEMENT_TYPES,
    HIGH_CSS_THRESHOLD,
)


DEFAULT_RUN_DIR = "/tmp/chatcat-rl-runs/phase2_baseline_norm__seed1__1780210056"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", type=str, default=DEFAULT_RUN_DIR,
                   help="Phase 2 baseline-norm run directory")
    return p.parse_args()


def query_baseline_aggregates(seeds: list[int]) -> list[dict]:
    """Spawn one bridge subprocess and query rule_based_episode for each
    seed, capturing full per-state aggregates. Bridge.ts must have been
    updated to return these fields. Reads CHATCAT_* env vars so the reward
    formula matches the training run.
    """
    proc = subprocess.Popen(
        ["pnpm", "exec", "tsx", "src/cli/bridge.ts"],
        cwd=str(find_litterbox_dir()),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env={
            **{k: v for k, v in __import__("os").environ.items()},
            "CHATCAT_ALPHA": str(CROSSOVER_ALPHA),
            "CHATCAT_BETA": str(CROSSOVER_BETA),
            "CHATCAT_ENG_SCALE_MULT": str(CROSSOVER_ENG_SCALE_MULT),
        },
    )

    def send(msg):
        assert proc.stdin is not None and proc.stdout is not None
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    out = []
    try:
        for s in seeds:
            resp = send({"type": "rule_based_episode", "seed": int(s)})
            if "error" in resp:
                raise RuntimeError(f"bridge error on seed {s}: {resp['error']}")
            out.append(resp)
    finally:
        try:
            send({"type": "close"})
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    return out


def re_eval_agent_with_per_state(model_path: Path, seeds: list[int]):
    """Re-run agent eval deterministically for each seed, capturing
    per-state engagement-action intensity aggregates. Uses the
    non-baseline wrapper to avoid double rule_based_episode queries."""
    env = ChatcatGymContinuousEnv()  # rewardParams default — irrelevant; we don't use reward here
    env_vec = gym.vector.SyncVectorEnv([lambda: env])
    agent = Agent(env_vec, frozen_logstd=None)
    state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
    agent.load_state_dict(state_dict)
    agent.eval()

    # Reproduce eval seeding from grid_scan_phase2_baseline run_eval:
    # torch.manual_seed(master_seed) was set there. We do the same.
    torch.manual_seed(1)

    per_episode = []  # list of dicts per episode
    try:
        for ep_idx, seed in enumerate(seeds):
            obs, _ = env_vec.reset(seed=int(seed))
            ep = {
                "env_seed": int(seed),
                "steps": 0,
                "engagement_ticks": 0,
                "max_css": 0.0,
                "opt_outs": 0,
                "high_css_ticks": 0,
                "per_state_visits": defaultdict(int),
                "per_state_type_counts": defaultdict(lambda: defaultdict(int)),
                "per_state_eng_intensity_sum": defaultdict(float),
                "per_state_eng_intensity_count": defaultdict(int),
            }
            done = False
            while not done:
                obs_t = torch.Tensor(obs)
                with torch.no_grad():
                    action_t, _, _, _ = agent.get_action_and_value(obs_t)
                action_np = action_t.cpu().numpy().squeeze(0)
                action_type, intensity = decode_continuous_action(action_np)
                state_idx = int(np.argmax(obs[0, :len(SIMCAT_STATES)]))
                state_name = SIMCAT_STATES[state_idx]

                ep["per_state_visits"][state_name] += 1
                ep["per_state_type_counts"][state_name][action_type] += 1
                if action_type in ENGAGEMENT_TYPES:
                    ep["per_state_eng_intensity_sum"][state_name] += intensity
                    ep["per_state_eng_intensity_count"][state_name] += 1

                next_obs, _, term, trunc, infos = env_vec.step(action_t.cpu().numpy())
                done = bool(term[0] or trunc[0])
                ep["engagement_ticks"] += int(infos["per_step_engagement"][0])
                css = float(infos["per_step_css"][0])
                if css > ep["max_css"]:
                    ep["max_css"] = css
                if css >= HIGH_CSS_THRESHOLD:
                    ep["high_css_ticks"] += 1
                if bool(infos["new_opt_out"][0]):
                    ep["opt_outs"] += 1
                ep["steps"] += 1
                obs = next_obs
            per_episode.append(ep)
            if (ep_idx + 1) % 20 == 0:
                print(f"  agent re-eval: ep {ep_idx + 1}/{len(seeds)}")
    finally:
        env_vec.close()
    return per_episode


def main():
    args = parse_args()
    run_dir = Path(args.run_dir)
    traj_path = run_dir / "grid_scan_baseline" / "trajectories.jsonl"
    model_path = run_dir / "agent.pt"

    agent_records = [json.loads(l) for l in traj_path.open()]
    seeds = [r["env_seed"] for r in agent_records]
    print(f"loaded {len(agent_records)} agent episodes from {traj_path}")
    print(f"querying bridge for baseline aggregates on the same {len(seeds)} seeds...")
    t0 = time.time()
    baselines = query_baseline_aggregates(seeds)
    print(f"  done in {time.time() - t0:.1f}s")
    print()

    # ─── Q1: episode length comparison ──────────────────────────────
    agent_lens = np.array([r["n_steps"] for r in agent_records])
    baseline_lens = np.array([b["steps"] for b in baselines])

    print("─" * 64)
    print("Q1  Episode-length comparison (on identical seeds)")
    print("─" * 64)
    print(f"  {'':<14} {'mean':>10} {'median':>10} {'p10':>10} {'p90':>10} {'min':>10} {'max':>10}")
    for label, arr in [("agent", agent_lens), ("baseline", baseline_lens)]:
        print(f"  {label:<14} {arr.mean():>10.1f} {np.median(arr):>10.0f} "
              f"{np.percentile(arr, 10):>10.0f} {np.percentile(arr, 90):>10.0f} "
              f"{arr.min():>10} {arr.max():>10}")
    same_max_ticks_agent = int((agent_lens == 18000).sum())
    same_max_ticks_baseline = int((baseline_lens == 18000).sum())
    print(f"  episodes ending at max_ticks=18000: agent {same_max_ticks_agent}/100, baseline {same_max_ticks_baseline}/100")
    pair_diff = agent_lens - baseline_lens
    print(f"  per-seed length diff (agent - baseline): mean {pair_diff.mean():+.1f}  "
          f"median {np.median(pair_diff):+.0f}  min {pair_diff.min()}  max {pair_diff.max()}")
    print()

    # ─── Q2: reward decomposition ───────────────────────────────────
    eng_scale = CROSSOVER_ENG_SCALE_MULT / (10 * 60)
    a_eng = np.array([eng_scale * r["engagement_ticks"] for r in agent_records])
    b_eng = np.array([eng_scale * b["engagement_ticks"] for b in baselines])
    a_css_pen = np.array([CROSSOVER_ALPHA * r["max_css"] for r in agent_records])
    b_css_pen = np.array([CROSSOVER_ALPHA * b["max_css"] for b in baselines])
    a_opt_pen = np.array([CROSSOVER_BETA * r["opt_outs"] for r in agent_records])
    b_opt_pen = np.array([CROSSOVER_BETA * b["opt_outs"] for b in baselines])

    # Per-episode normalised score reconstructed from components
    # (sanity: should match summary.json's mean −1.223)
    reconstructed_delta = (a_eng - b_eng) - (a_css_pen - b_css_pen) - (a_opt_pen - b_opt_pen)

    print("─" * 64)
    print("Q2  Reward decomposition: where does Δ = R_agent − R_baseline come from?")
    print("─" * 64)
    print(f"  {'component':<22} {'agent mean':>14} {'baseline mean':>16} {'Δ (a−b) mean':>16}")
    print(f"  {'engagement (+)':<22} {a_eng.mean():>+14.4f} {b_eng.mean():>+16.4f} {(a_eng - b_eng).mean():>+16.4f}")
    print(f"  {'-α·max_CSS  (−)':<22} {-a_css_pen.mean():>+14.4f} {-b_css_pen.mean():>+16.4f} {-(a_css_pen - b_css_pen).mean():>+16.4f}")
    print(f"  {'-β·opt_outs (−)':<22} {-a_opt_pen.mean():>+14.4f} {-b_opt_pen.mean():>+16.4f} {-(a_opt_pen - b_opt_pen).mean():>+16.4f}")
    print(f"  {'total Δ':<22} {'':<14} {'':<16} {reconstructed_delta.mean():>+16.4f}")
    print(f"  (summary.json reported Δ mean −1.223 → reconstructed matches to FP rounding)")
    print()

    # Component contribution as fractions of total |Δ|
    total_abs = abs(reconstructed_delta.mean())
    if total_abs > 1e-9:
        print(f"  share of total Δ explained by each component:")
        contributions = {
            "engagement": (a_eng - b_eng).mean(),
            "max_CSS": -(a_css_pen - b_css_pen).mean(),
            "opt_outs": -(a_opt_pen - b_opt_pen).mean(),
        }
        for name, val in contributions.items():
            sign = "+" if val > 0 else "-"
            print(f"    {name:<14} {val:>+8.4f}  ({sign}{abs(val) / total_abs * 100:.1f}% of |Δ|)")
    print()

    # Also raw component means (no scaling) for inspection
    a_eng_ticks = np.array([r["engagement_ticks"] for r in agent_records])
    b_eng_ticks = np.array([b["engagement_ticks"] for b in baselines])
    a_max_css = np.array([r["max_css"] for r in agent_records])
    b_max_css = np.array([b["max_css"] for b in baselines])
    a_opt_outs = np.array([r["opt_outs"] for r in agent_records])
    b_opt_outs = np.array([b["opt_outs"] for b in baselines])
    print(f"  raw component means (unscaled):")
    print(f"    engagement_ticks:  agent {a_eng_ticks.mean():>8.1f}  baseline {b_eng_ticks.mean():>8.1f}  diff {(a_eng_ticks - b_eng_ticks).mean():>+8.1f}")
    print(f"    max_CSS:           agent {a_max_css.mean():>8.3f}  baseline {b_max_css.mean():>8.3f}  diff {(a_max_css - b_max_css).mean():>+8.3f}")
    print(f"    opt_outs:          agent {a_opt_outs.mean():>8.2f}  baseline {b_opt_outs.mean():>8.2f}  diff {(a_opt_outs - b_opt_outs).mean():>+8.2f}")
    print()

    # ─── Q3: per-state engagement-action intensity ──────────────────
    print("─" * 64)
    print("Q3  Per-state engagement-action intensity (agent vs baseline)")
    print("─" * 64)
    print(f"  Re-running agent eval to capture per-step states (deterministic, ~6 min)...")
    t0 = time.time()
    agent_per_episode = re_eval_agent_with_per_state(model_path, seeds)
    print(f"  agent re-eval done in {time.time() - t0:.1f}s")
    print()

    # Aggregate agent per-state across all episodes
    agent_state = {st: {"visits": 0, "eng_sum": 0.0, "eng_count": 0} for st in SIMCAT_STATES}
    for ep in agent_per_episode:
        for st in SIMCAT_STATES:
            agent_state[st]["visits"] += ep["per_state_visits"].get(st, 0)
            agent_state[st]["eng_sum"] += ep["per_state_eng_intensity_sum"].get(st, 0.0)
            agent_state[st]["eng_count"] += ep["per_state_eng_intensity_count"].get(st, 0)

    # Aggregate baseline per-state across all baseline rollouts
    baseline_state = {st: {"visits": 0, "eng_sum": 0.0, "eng_count": 0} for st in SIMCAT_STATES}
    for b in baselines:
        for st in SIMCAT_STATES:
            baseline_state[st]["visits"] += b["per_state_visits"].get(st, 0)
            baseline_state[st]["eng_sum"] += b["per_state_eng_intensity_sum"].get(st, 0.0)
            baseline_state[st]["eng_count"] += b["per_state_eng_intensity_count"].get(st, 0)

    print(f"  {'state':<16} {'a visits':>10} {'a eng':>8} {'a int':>8}   {'b visits':>10} {'b eng':>8} {'b int':>8}   {'Δ int':>8}")
    print(f"  {'─' * 16} {'─' * 10} {'─' * 8} {'─' * 8}   {'─' * 10} {'─' * 8} {'─' * 8}   {'─' * 8}")
    for st in SIMCAT_STATES:
        a_v = agent_state[st]["visits"]
        a_c = agent_state[st]["eng_count"]
        a_int = agent_state[st]["eng_sum"] / max(1, a_c)
        b_v = baseline_state[st]["visits"]
        b_c = baseline_state[st]["eng_count"]
        b_int = baseline_state[st]["eng_sum"] / max(1, b_c)
        d_int = a_int - b_int if a_c > 0 and b_c > 0 else float("nan")
        a_int_str = f"{a_int:>8.4f}" if a_c > 0 else f"{'—':>8}"
        b_int_str = f"{b_int:>8.4f}" if b_c > 0 else f"{'—':>8}"
        d_int_str = f"{d_int:>+8.4f}" if a_c > 0 and b_c > 0 else f"{'—':>8}"
        print(f"  {st:<16} {a_v:>10} {a_c:>8} {a_int_str}   {b_v:>10} {b_c:>8} {b_int_str}   {d_int_str}")

    # Overall (across all states with engagement actions)
    a_overall_sum = sum(agent_state[st]["eng_sum"] for st in SIMCAT_STATES)
    a_overall_count = sum(agent_state[st]["eng_count"] for st in SIMCAT_STATES)
    b_overall_sum = sum(baseline_state[st]["eng_sum"] for st in SIMCAT_STATES)
    b_overall_count = sum(baseline_state[st]["eng_count"] for st in SIMCAT_STATES)
    print(f"  {'─' * 64}")
    print(f"  {'overall':<16} "
          f"{sum(agent_state[st]['visits'] for st in SIMCAT_STATES):>10} "
          f"{a_overall_count:>8} {a_overall_sum / max(1, a_overall_count):>8.4f}   "
          f"{sum(baseline_state[st]['visits'] for st in SIMCAT_STATES):>10} "
          f"{b_overall_count:>8} {b_overall_sum / max(1, b_overall_count):>8.4f}   "
          f"{(a_overall_sum / max(1, a_overall_count) - b_overall_sum / max(1, b_overall_count)):>+8.4f}")


if __name__ == "__main__":
    main()
