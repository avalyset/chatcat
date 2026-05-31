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
Post-training grid scan + classifier for ADR 0008's baseline-normalised
training run.

Layered on grid_scan_phase2.py's classifier (LOCKED, unchanged) — same
NON_TRIVIAL / IDLE_OUT / PUSH_THE_CAT / TRIVIAL thresholds, same
metrics. Adds two ADR-0008-specific checks:

(2) climb-and-holds: read metrics.jsonl from the training run, compute
    ep_init / ep_peak / ep_final from ep_return_mean_recent, verify
    ep_peak − ep_init ≥ 1.0  AND  ep_final ≥ ep_peak − 0.5.

(3) better-than-baseline: run 100 eval episodes with the trained agent
    through BaselineNormalizedChatcatEnv, capture per-episode
    (R_agent_total, R_baseline) — the wrapper already subtracts the
    baseline at the terminal step, so the episode-summed reward IS the
    baseline-normalised score. Verify mean ≥ +1.0.

Final verdict is conjunctive: ADR 0008 resolves POSITIVELY iff all
three (classifier, climb-and-holds, better-than-baseline) hold.

Writes:
  <model-dir>/grid_scan_baseline/summary.json
  <model-dir>/grid_scan_baseline/trajectories.jsonl
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch

import gymnasium as gym  # noqa: E402
from env_continuous_baseline import BaselineNormalizedChatcatEnv  # noqa: E402
from env_continuous import (  # noqa: E402
    ACTION_DIM,
    ACTION_TYPES,
    N_TYPES,
    OBS_DIM,
    decode_continuous_action,
)
from grid_scan_phase2 import (  # noqa: E402
    IDLE_OUT_THRESHOLD,
    PUSH_NON_IDLE_THRESHOLD,
    PUSH_OPT_OUT_PER_EPISODE_THRESHOLD,
    PUSH_HIGH_CSS_SHARE_THRESHOLD,
    TRIVIAL_ENTROPY_THRESHOLD,
    TRIVIAL_TVD_THRESHOLD,
    MIN_STATE_VISITS,
    SIMCAT_STATES,
    ENGAGEMENT_TYPES,
    HIGH_CSS_THRESHOLD,
    compute_metrics,
    classify,
    load_agent,
)
from train_phase2 import (  # noqa: E402
    CROSSOVER_ALPHA,
    CROSSOVER_BETA,
    CROSSOVER_ENG_SCALE_MULT,
)

# ─── Pre-registered ADR 0008 thresholds (DO NOT EDIT post-hoc) ────────
CLIMB_THRESHOLD = 1.0          # ep_peak − ep_init must reach this
HOLDS_TOLERANCE = 0.5          # ep_final must be within this of ep_peak
BETTER_THAN_BASELINE_MEAN = 1.0  # mean (R_agent − R_baseline) over 100 eval episodes


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model-path", type=str, required=True,
                   help="Path to agent.pt from train_phase2_baseline.py")
    p.add_argument("--episodes", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--output-dir", type=str, default=None,
                   help="Defaults to <model-path-parent>/grid_scan_baseline/")
    return p.parse_args()


def run_eval(agent, episodes, master_seed):
    env = BaselineNormalizedChatcatEnv(
        reward_alpha=CROSSOVER_ALPHA,
        reward_beta=CROSSOVER_BETA,
        reward_engagement_scale_mult=CROSSOVER_ENG_SCALE_MULT,
    )
    env_thunk = gym.vector.SyncVectorEnv([lambda: env])
    rng = np.random.default_rng(master_seed)
    torch.manual_seed(master_seed)

    trajectories = []
    try:
        for ep in range(episodes):
            ep_seed = int(rng.integers(0, 2**31 - 1))
            obs, reset_info = env_thunk.reset(seed=ep_seed)
            baseline_reward = float(reset_info["baseline_reward"][0])
            ep_steps = []
            ep_reward_sum = 0.0
            done = False
            while not done:
                obs_t = torch.Tensor(obs)
                with torch.no_grad():
                    action_t, _, _, _ = agent.get_action_and_value(obs_t)
                action_np = action_t.cpu().numpy().squeeze(0)
                action_type, intensity = decode_continuous_action(action_np)
                state_idx = int(np.argmax(obs[0, :len(SIMCAT_STATES)]))
                next_obs, reward, terminations, truncations, infos = env_thunk.step(
                    action_t.cpu().numpy()
                )
                done_arr = np.logical_or(terminations, truncations)
                ep_reward_sum += float(reward[0])
                ep_steps.append({
                    "state": SIMCAT_STATES[state_idx],
                    "action_type": action_type,
                    "intensity": intensity,
                    "reward": float(reward[0]),  # baseline-normalised at terminal step
                    "css": float(infos["per_step_css"][0]),
                    "engagement_tick": int(infos["per_step_engagement"][0]),
                    "new_opt_out": bool(infos["new_opt_out"][0]),
                })
                obs = next_obs
                done = bool(done_arr[0])
            trajectories.append({
                "episode": ep,
                "env_seed": ep_seed,
                "baseline_reward": baseline_reward,
                "ep_reward_sum_normalised": ep_reward_sum,  # = R_agent_total − R_baseline
                "agent_total_reward": ep_reward_sum + baseline_reward,
                "steps": ep_steps,
            })
    finally:
        env_thunk.close()
    return trajectories


def read_climb_and_holds(metrics_path: Path) -> dict:
    rows = [json.loads(l) for l in metrics_path.open()]
    valid = [r for r in rows if r.get("ep_return_n_recent", 0) >= 10]
    if not valid:
        return {"ok": False, "reason": "no updates with >=10 episodes in buffer"}

    ep_init_row = next((r for r in rows if r["update"] >= 100), valid[0])
    ep_init = float(ep_init_row["ep_return_mean_recent"])
    ep_peak_row = max(rows, key=lambda r: r["ep_return_mean_recent"]
                      if r["ep_return_n_recent"] >= 10 else -float("inf"))
    ep_peak = float(ep_peak_row["ep_return_mean_recent"])
    ep_final = float(rows[-1]["ep_return_mean_recent"])

    climb = ep_peak - ep_init
    holds_gap = ep_peak - ep_final

    climb_ok = climb >= CLIMB_THRESHOLD
    holds_ok = ep_final >= ep_peak - HOLDS_TOLERANCE
    return {
        "ok": bool(climb_ok and holds_ok),
        "climb_ok": climb_ok, "holds_ok": holds_ok,
        "ep_init_update": ep_init_row["update"], "ep_init": ep_init,
        "ep_peak_update": ep_peak_row["update"], "ep_peak": ep_peak,
        "ep_final_update": rows[-1]["update"], "ep_final": ep_final,
        "climb_value": climb, "climb_threshold": CLIMB_THRESHOLD,
        "holds_gap": holds_gap, "holds_tolerance": HOLDS_TOLERANCE,
    }


def main():
    args = parse_args()
    model_path = Path(args.model_path)
    if not model_path.exists():
        print(f"model not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else model_path.parent / "grid_scan_baseline"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"loading model: {model_path}")
    print(f"running {args.episodes} evaluation episodes, master_seed={args.seed}")
    print(f"reward regime: adr0002_max_css crossover, baseline-normalised "
          f"(α={CROSSOVER_ALPHA} β={CROSSOVER_BETA} scale_mult={CROSSOVER_ENG_SCALE_MULT})")
    print()

    sizing_env = BaselineNormalizedChatcatEnv(
        reward_alpha=CROSSOVER_ALPHA, reward_beta=CROSSOVER_BETA,
        reward_engagement_scale_mult=CROSSOVER_ENG_SCALE_MULT,
    )
    sizing_vec = gym.vector.SyncVectorEnv([lambda: sizing_env])
    agent = load_agent(model_path, sizing_vec)
    sizing_vec.close()

    start = time.time()
    trajectories = run_eval(agent, args.episodes, args.seed)
    elapsed = time.time() - start

    metrics = compute_metrics(trajectories)
    classifier_label, classifier_reason = classify(metrics)

    # Baseline-normalised summary (criterion 3)
    ep_norm = [t["ep_reward_sum_normalised"] for t in trajectories]
    baselines = [t["baseline_reward"] for t in trajectories]
    agents = [t["agent_total_reward"] for t in trajectories]
    mean_norm = float(np.mean(ep_norm))
    std_norm = float(np.std(ep_norm))
    better_than_baseline_ok = mean_norm >= BETTER_THAN_BASELINE_MEAN

    # Climb-and-holds (criterion 2)
    metrics_path = model_path.parent / "metrics.jsonl"
    climb = read_climb_and_holds(metrics_path)

    # Conjunctive verdict
    classifier_ok = (classifier_label == "NON_TRIVIAL")
    overall_ok = bool(classifier_ok and climb["ok"] and better_than_baseline_ok)
    verdict = "ADR_0008_RESOLVES_POSITIVELY" if overall_ok else "ADR_0008_DOES_NOT_RESOLVE"

    summary = {
        "model_path": str(model_path),
        "episodes": args.episodes,
        "master_seed": args.seed,
        "wall_seconds": elapsed,
        "reward_regime": {
            "form": "adr0002_max_css",
            "alpha": CROSSOVER_ALPHA, "beta": CROSSOVER_BETA,
            "engagement_scale_mult": CROSSOVER_ENG_SCALE_MULT,
            "baseline_normalised": True,
        },
        "adr_0008_overall_verdict": verdict,
        "criterion_1_classifier": {
            "label": classifier_label,
            "reason": classifier_reason,
            "passed": classifier_ok,
        },
        "criterion_2_climb_and_holds": climb,
        "criterion_3_better_than_baseline": {
            "mean_normalised_reward": mean_norm,
            "std_normalised_reward": std_norm,
            "threshold": BETTER_THAN_BASELINE_MEAN,
            "passed": better_than_baseline_ok,
            "mean_agent_total": float(np.mean(agents)),
            "mean_baseline_total": float(np.mean(baselines)),
        },
        "pre_registered_thresholds": {
            "IDLE_OUT_THRESHOLD": IDLE_OUT_THRESHOLD,
            "PUSH_NON_IDLE_THRESHOLD": PUSH_NON_IDLE_THRESHOLD,
            "PUSH_OPT_OUT_PER_EPISODE_THRESHOLD": PUSH_OPT_OUT_PER_EPISODE_THRESHOLD,
            "PUSH_HIGH_CSS_SHARE_THRESHOLD": PUSH_HIGH_CSS_SHARE_THRESHOLD,
            "TRIVIAL_ENTROPY_THRESHOLD": TRIVIAL_ENTROPY_THRESHOLD,
            "TRIVIAL_TVD_THRESHOLD": TRIVIAL_TVD_THRESHOLD,
            "MIN_STATE_VISITS": MIN_STATE_VISITS,
            "CLIMB_THRESHOLD": CLIMB_THRESHOLD,
            "HOLDS_TOLERANCE": HOLDS_TOLERANCE,
            "BETTER_THAN_BASELINE_MEAN": BETTER_THAN_BASELINE_MEAN,
        },
        "metrics": metrics,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    with open(output_dir / "trajectories.jsonl", "w") as f:
        for t in trajectories:
            f.write(json.dumps({
                "episode": t["episode"],
                "env_seed": t["env_seed"],
                "baseline_reward": t["baseline_reward"],
                "agent_total_reward": t["agent_total_reward"],
                "normalised_reward": t["ep_reward_sum_normalised"],
                "n_steps": len(t["steps"]),
                "type_counts": {
                    at: sum(1 for s in t["steps"] if s["action_type"] == at)
                    for at in ACTION_TYPES
                },
                "max_css": float(max(s["css"] for s in t["steps"])),
                "mean_css": float(np.mean([s["css"] for s in t["steps"]])),
                "engagement_ticks": sum(s["engagement_tick"] for s in t["steps"]),
                "opt_outs": sum(1 for s in t["steps"] if s["new_opt_out"]),
            }) + "\n")

    print("=" * 72)
    print(f"ADR 0008 VERDICT: {verdict}")
    print("=" * 72)
    print()
    print(f"Criterion 1 — locked classifier:                    {'PASS' if classifier_ok else 'FAIL'}")
    print(f"  label: {classifier_label}")
    print(f"  reason: {classifier_reason}")
    print()
    print(f"Criterion 2 — climb-and-holds (from metrics.jsonl): "
          f"{'PASS' if climb['ok'] else 'FAIL'}")
    if "reason" in climb:
        print(f"  {climb['reason']}")
    else:
        print(f"  ep_init  (update {climb['ep_init_update']:>4}):  {climb['ep_init']:+.3f}")
        print(f"  ep_peak  (update {climb['ep_peak_update']:>4}):  {climb['ep_peak']:+.3f}")
        print(f"  ep_final (update {climb['ep_final_update']:>4}):  {climb['ep_final']:+.3f}")
        print(f"  climb = ep_peak − ep_init = {climb['climb_value']:+.3f}  "
              f"(threshold ≥ {CLIMB_THRESHOLD})  "
              f"{'✓' if climb['climb_ok'] else '✗'}")
        print(f"  holds = ep_peak − ep_final = {climb['holds_gap']:+.3f}  "
              f"(tolerance ≤ {HOLDS_TOLERANCE})  "
              f"{'✓' if climb['holds_ok'] else '✗'}")
    print()
    print(f"Criterion 3 — better-than-baseline:                 "
          f"{'PASS' if better_than_baseline_ok else 'FAIL'}")
    print(f"  mean(R_agent − R_baseline) over {len(trajectories)} eval episodes: "
          f"{mean_norm:+.3f}  (threshold ≥ {BETTER_THAN_BASELINE_MEAN})")
    print(f"  std:                                  {std_norm:.3f}")
    print(f"  mean R_agent_total:                   {np.mean(agents):+.3f}")
    print(f"  mean R_baseline_total:                {np.mean(baselines):+.3f}")
    print()
    print("─── Classifier metrics (same form as 0007) ───")
    print(f"  idle_share:                  {metrics['idle_share']:.4f}")
    print(f"  non_idle_share:              {metrics['non_idle_share']:.4f}")
    print(f"  action_type_entropy:         {metrics['action_type_entropy_bits']:.4f} bits "
          f"(max = {math.log2(N_TYPES):.4f})")
    print(f"  mean_engagement_intensity:   {metrics['mean_engagement_intensity']:.4f}")
    print(f"  mean_state_conditional_tvd:  {metrics['mean_state_conditional_tvd']:.4f}")
    print(f"  mean_opt_outs_per_episode:   {metrics['mean_opt_outs_per_episode']:.2f}")
    print(f"  high_css_share_overall:      {metrics['high_css_share_overall']:.4f}")
    print()
    print("─── Type marginal ───")
    for at in ACTION_TYPES:
        print(f"  {at:<14} {metrics['type_marginal'][at]:.4f}  "
              f"({metrics['type_counts'][at]:>6} steps)")
    print()
    print(f"wall time: {elapsed:.1f}s")
    print(f"output:    {output_dir}")
    print(f"summary:   {output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
