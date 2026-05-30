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
Post-training grid scan + degeneracy classifier — ADR 0007 resolution path.

Loads a trained agent.pt from train_phase2.py and runs N evaluation
episodes through ChatcatGymContinuousEnv in the SAME crossover regime
the model was trained in. Captures per-step (state, action, intensity,
reward, css) and classifies the trained policy against the
pre-registered degeneracy criteria below.

Also scores the trajectory under the three EpisodeRewardFns from ADR 0007
(adr0002_max_css, mean_css, high_css_share) so reward-balance under the
trained agent — the only context ADR 0007 said could adjudicate the form
choice — can be read directly.

### Pre-registered degeneracy criteria (locked before any trained model)

Run on N=100 evaluation episodes with stochastic action sampling
(`agent.get_action_and_value()` with `action=None`) using
fixed master seed for reproducibility.

  IDLE_OUT     iff  idle_share > IDLE_OUT_THRESHOLD (0.90)
  PUSH_THE_CAT iff  non_idle_share > PUSH_NON_IDLE_THRESHOLD (0.80) AND
                    mean_engagement_intensity > PUSH_INTENSITY_THRESHOLD (0.75)
                    (engagement = action_type in {slow_blink, trill,
                     soft_purr, side_glance}; pause and idle excluded)
  TRIVIAL      iff  (action_type_entropy < TRIVIAL_ENTROPY_THRESHOLD (0.5)
                     bits, out of max log2(6) ≈ 2.585)
                    OR
                    (state_conditional_TVD < TRIVIAL_TVD_THRESHOLD (0.05),
                     mean TVD between per-state action-type distributions
                     and the marginal, averaged over states with ≥
                     MIN_STATE_VISITS (50) observed steps)
  NON_TRIVIAL  iff  none of the above

Classification is mutually exclusive in this order (first matching label
wins). NON_TRIVIAL only when the policy is between the two corner
extremes, has non-degenerate action-type entropy, AND uses state info
beyond chance.

These thresholds were chosen to:
  - cleanly exclude the two ADR-0007-named corner collapses
    (constant-idle / constant-high-intensity)
  - exclude random/constant policies that wouldn't qualify as "learned
    behaviour" (action_type_entropy < 0.5 catches constant; TVD < 0.05
    catches state-blind)
  - leave a meaningful middle range that an actually-learning PPO can
    reach (random sampling from Box(7,) would fail TVD; corner
    collapses would fail entropy or the non-idle band)

Re-running this script with the same --model-path and --seed produces
bit-identical classification metrics.

Usage:
  cd litterbox
  uv run rl/grid_scan_phase2.py --model-path <path>/agent.pt [--episodes 100] [--seed 1]
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
from env_continuous import (  # noqa: E402
    ACTION_DIM,
    ACTION_TYPES,
    ChatcatGymContinuousEnv,
    N_TYPES,
    OBS_DIM,
    decode_continuous_action,
)
from train_phase2 import (  # noqa: E402
    Agent,
    CROSSOVER_ALPHA,
    CROSSOVER_BETA,
    CROSSOVER_ENG_SCALE_MULT,
)

# ─── Pre-registered degeneracy thresholds (DO NOT EDIT post-hoc) ─────
IDLE_OUT_THRESHOLD = 0.90        # idle_share above → IDLE_OUT
PUSH_NON_IDLE_THRESHOLD = 0.80   # non_idle_share above, AND...
PUSH_INTENSITY_THRESHOLD = 0.75  # mean engagement intensity above → PUSH_THE_CAT
TRIVIAL_ENTROPY_THRESHOLD = 0.5  # action_type_entropy below → TRIVIAL
TRIVIAL_TVD_THRESHOLD = 0.05     # state-conditional TVD below → TRIVIAL
MIN_STATE_VISITS = 50            # states with fewer visits dropped from TVD avg

ENGAGEMENT_TYPES = {"slow_blink", "trill", "soft_purr", "side_glance"}
SIMCAT_STATES = [
    "ABSENT", "RESTING", "ALERT", "CURIOUS", "APPROACHING",
    "ENGAGING", "OVERSTIMULATED", "STRESSED", "RETREATING", "LEAVING",
]
HIGH_CSS_THRESHOLD = 4  # Kessler & Turner 1997 — matches src/rl/reward.ts


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model-path", type=str, required=True,
                   help="Path to agent.pt from train_phase2.py")
    p.add_argument("--episodes", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--output-dir", type=str, default=None,
                   help="Defaults to <model-path-parent>/grid_scan/")
    return p.parse_args()


def load_agent(model_path: Path, env) -> Agent:
    agent = Agent(env)
    state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
    agent.load_state_dict(state_dict)
    agent.eval()
    return agent


def run_evaluation(agent: Agent, episodes: int, master_seed: int):
    env = ChatcatGymContinuousEnv(
        reward_alpha=CROSSOVER_ALPHA,
        reward_beta=CROSSOVER_BETA,
        reward_engagement_scale_mult=CROSSOVER_ENG_SCALE_MULT,
    )
    # Single env, not vectorised — easier to capture per-step detail.
    env_thunk = gym.vector.SyncVectorEnv([lambda: env])
    rng = np.random.default_rng(master_seed)
    torch.manual_seed(master_seed)

    trajectories = []
    try:
        for ep in range(episodes):
            ep_seed = int(rng.integers(0, 2**31 - 1))
            obs, _ = env_thunk.reset(seed=ep_seed)
            ep_steps = []
            done = False
            while not done:
                obs_t = torch.Tensor(obs)
                with torch.no_grad():
                    action_t, _, _, _ = agent.get_action_and_value(obs_t)
                action_np = action_t.cpu().numpy().squeeze(0)
                # Decode for analysis (mirrors the wrapper's decode).
                action_type, intensity = decode_continuous_action(action_np)
                state_idx = int(np.argmax(obs[0, :len(SIMCAT_STATES)]))
                next_obs, reward, terminations, truncations, infos = env_thunk.step(
                    action_t.cpu().numpy()
                )
                done_arr = np.logical_or(terminations, truncations)
                ep_steps.append({
                    "state": SIMCAT_STATES[state_idx],
                    "action_type": action_type,
                    "intensity": intensity,
                    "reward": float(reward[0]),
                    "css": float(infos["per_step_css"][0]),
                    "engagement_tick": int(infos["per_step_engagement"][0]),
                    "new_opt_out": bool(infos["new_opt_out"][0]),
                })
                obs = next_obs
                done = bool(done_arr[0])
            trajectories.append({
                "episode": ep,
                "env_seed": ep_seed,
                "steps": ep_steps,
            })
    finally:
        env_thunk.close()
    return trajectories


def compute_metrics(trajectories):
    all_steps = [s for t in trajectories for s in t["steps"]]
    n_steps = len(all_steps)

    # Action type marginal
    type_counts = {t: 0 for t in ACTION_TYPES}
    for s in all_steps:
        type_counts[s["action_type"]] += 1
    type_marginal = {t: c / n_steps for t, c in type_counts.items()}

    idle_share = type_marginal["idle"]
    non_idle_share = 1.0 - idle_share

    # Mean intensity over engagement actions only
    eng_intensities = [s["intensity"] for s in all_steps if s["action_type"] in ENGAGEMENT_TYPES]
    mean_eng_intensity = float(np.mean(eng_intensities)) if eng_intensities else 0.0

    # Action type entropy (bits)
    type_entropy_bits = -sum(
        p * math.log2(p) for p in type_marginal.values() if p > 0
    )

    # State-conditional TVD: per-state action-type distribution vs marginal
    state_counts = {st: {t: 0 for t in ACTION_TYPES} for st in SIMCAT_STATES}
    for s in all_steps:
        state_counts[s["state"]][s["action_type"]] += 1
    state_visits = {st: sum(state_counts[st].values()) for st in SIMCAT_STATES}

    per_state_tvd = {}
    for st in SIMCAT_STATES:
        if state_visits[st] < MIN_STATE_VISITS:
            continue
        state_dist = {t: c / state_visits[st] for t, c in state_counts[st].items()}
        tvd = 0.5 * sum(abs(state_dist[t] - type_marginal[t]) for t in ACTION_TYPES)
        per_state_tvd[st] = tvd
    mean_state_tvd = float(np.mean(list(per_state_tvd.values()))) if per_state_tvd else 0.0

    # Episode aggregates for three-form reward scoring
    tick_rate = 10
    engagement_scale = CROSSOVER_ENG_SCALE_MULT / (tick_rate * 60)
    per_ep_aggregates = []
    for t in trajectories:
        steps = t["steps"]
        css_vals = [s["css"] for s in steps]
        per_ep_aggregates.append({
            "episode": t["episode"],
            "n_steps": len(steps),
            "engagement_ticks": sum(s["engagement_tick"] for s in steps),
            "css_sum": float(sum(css_vals)),
            "high_css_ticks": sum(1 for c in css_vals if c >= HIGH_CSS_THRESHOLD),
            "max_css": float(max(css_vals)) if css_vals else 0.0,
            "opt_outs": sum(1 for s in steps if s["new_opt_out"]),
        })

    def score(form, agg):
        eng = engagement_scale * agg["engagement_ticks"]
        opt = CROSSOVER_BETA * agg["opt_outs"]
        if form == "adr0002_max_css":
            css_term = CROSSOVER_ALPHA * agg["max_css"]
        elif form == "mean_css":
            css_term = CROSSOVER_ALPHA * (agg["css_sum"] / max(1, agg["n_steps"]))
        elif form == "high_css_share":
            css_term = CROSSOVER_ALPHA * (agg["high_css_ticks"] / max(1, agg["n_steps"]))
        else:
            raise ValueError(form)
        return eng - css_term - opt

    forms = ["adr0002_max_css", "mean_css", "high_css_share"]
    per_form_returns = {f: [score(f, a) for a in per_ep_aggregates] for f in forms}

    return {
        "n_episodes": len(trajectories),
        "n_steps_total": n_steps,
        "type_marginal": type_marginal,
        "type_counts": type_counts,
        "idle_share": idle_share,
        "non_idle_share": non_idle_share,
        "mean_engagement_intensity": mean_eng_intensity,
        "engagement_step_count": len(eng_intensities),
        "action_type_entropy_bits": type_entropy_bits,
        "state_visits": state_visits,
        "per_state_tvd": per_state_tvd,
        "mean_state_conditional_tvd": mean_state_tvd,
        "per_form_returns": {
            f: {
                "mean": float(np.mean(rs)),
                "median": float(np.median(rs)),
                "min": float(np.min(rs)),
                "max": float(np.max(rs)),
                "std": float(np.std(rs)),
            }
            for f, rs in per_form_returns.items()
        },
    }


def classify(m: dict) -> tuple[str, str]:
    if m["idle_share"] > IDLE_OUT_THRESHOLD:
        return "IDLE_OUT", (
            f"idle_share={m['idle_share']:.3f} > {IDLE_OUT_THRESHOLD} threshold "
            f"— agent essentially never acts"
        )
    if (m["non_idle_share"] > PUSH_NON_IDLE_THRESHOLD
        and m["mean_engagement_intensity"] > PUSH_INTENSITY_THRESHOLD):
        return "PUSH_THE_CAT", (
            f"non_idle_share={m['non_idle_share']:.3f} > {PUSH_NON_IDLE_THRESHOLD} "
            f"AND mean_engagement_intensity={m['mean_engagement_intensity']:.3f} "
            f"> {PUSH_INTENSITY_THRESHOLD} "
            f"— agent over-engages at high intensity"
        )
    if m["action_type_entropy_bits"] < TRIVIAL_ENTROPY_THRESHOLD:
        return "TRIVIAL", (
            f"action_type_entropy={m['action_type_entropy_bits']:.3f} bits "
            f"< {TRIVIAL_ENTROPY_THRESHOLD} — agent essentially picks one type"
        )
    if m["mean_state_conditional_tvd"] < TRIVIAL_TVD_THRESHOLD:
        return "TRIVIAL", (
            f"mean_state_conditional_tvd={m['mean_state_conditional_tvd']:.4f} "
            f"< {TRIVIAL_TVD_THRESHOLD} — agent does not condition on cat state"
        )
    return "NON_TRIVIAL", (
        f"non_idle_share={m['non_idle_share']:.3f} ∈ "
        f"[{1 - IDLE_OUT_THRESHOLD}, {PUSH_NON_IDLE_THRESHOLD}], "
        f"entropy={m['action_type_entropy_bits']:.3f} bits ≥ {TRIVIAL_ENTROPY_THRESHOLD}, "
        f"state_TVD={m['mean_state_conditional_tvd']:.4f} ≥ {TRIVIAL_TVD_THRESHOLD}"
    )


def main():
    args = parse_args()
    model_path = Path(args.model_path)
    if not model_path.exists():
        print(f"model not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else model_path.parent / "grid_scan"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"loading model: {model_path}")
    print(f"running {args.episodes} evaluation episodes, master_seed={args.seed}")
    print(f"reward regime (matches training): adr0002_max_css, "
          f"α={CROSSOVER_ALPHA} β={CROSSOVER_BETA} scale_mult={CROSSOVER_ENG_SCALE_MULT}")
    print()

    # Need an env instance to size Agent; not used otherwise here.
    sizing_env = ChatcatGymContinuousEnv(
        reward_alpha=CROSSOVER_ALPHA, reward_beta=CROSSOVER_BETA,
        reward_engagement_scale_mult=CROSSOVER_ENG_SCALE_MULT,
    )
    sizing_vec = gym.vector.SyncVectorEnv([lambda: sizing_env])
    agent = load_agent(model_path, sizing_vec)
    sizing_vec.close()

    start = time.time()
    trajectories = run_evaluation(agent, args.episodes, args.seed)
    elapsed = time.time() - start

    metrics = compute_metrics(trajectories)
    label, reason = classify(metrics)

    summary = {
        "model_path": str(model_path),
        "episodes": args.episodes,
        "master_seed": args.seed,
        "wall_seconds": elapsed,
        "reward_regime": {
            "form": "adr0002_max_css",
            "alpha": CROSSOVER_ALPHA, "beta": CROSSOVER_BETA,
            "engagement_scale_mult": CROSSOVER_ENG_SCALE_MULT,
        },
        "classification": label,
        "classification_reason": reason,
        "pre_registered_thresholds": {
            "IDLE_OUT_THRESHOLD": IDLE_OUT_THRESHOLD,
            "PUSH_NON_IDLE_THRESHOLD": PUSH_NON_IDLE_THRESHOLD,
            "PUSH_INTENSITY_THRESHOLD": PUSH_INTENSITY_THRESHOLD,
            "TRIVIAL_ENTROPY_THRESHOLD": TRIVIAL_ENTROPY_THRESHOLD,
            "TRIVIAL_TVD_THRESHOLD": TRIVIAL_TVD_THRESHOLD,
            "MIN_STATE_VISITS": MIN_STATE_VISITS,
        },
        "metrics": metrics,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    # Per-episode JSONL (compact)
    with open(output_dir / "trajectories.jsonl", "w") as f:
        for t in trajectories:
            f.write(json.dumps({
                "episode": t["episode"],
                "env_seed": t["env_seed"],
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

    print("=" * 64)
    print(f"CLASSIFICATION: {label}")
    print(f"  reason: {reason}")
    print("=" * 64)
    print()
    print("─── Action distribution ───")
    print(f"  idle_share:                {metrics['idle_share']:.4f}")
    print(f"  non_idle_share:            {metrics['non_idle_share']:.4f}")
    print(f"  action_type_entropy:       {metrics['action_type_entropy_bits']:.4f} bits "
          f"(max = {math.log2(N_TYPES):.4f})")
    print(f"  mean_engagement_intensity: {metrics['mean_engagement_intensity']:.4f}")
    print(f"  type marginal:")
    for at in ACTION_TYPES:
        print(f"    {at:<14} {metrics['type_marginal'][at]:.4f}  "
              f"({metrics['type_counts'][at]:>6} steps)")
    print()
    print("─── State-conditional behaviour ───")
    print(f"  mean_state_conditional_tvd: {metrics['mean_state_conditional_tvd']:.4f}")
    print(f"  per-state TVD (states with ≥ {MIN_STATE_VISITS} visits):")
    for st in SIMCAT_STATES:
        v = metrics["state_visits"][st]
        if v >= MIN_STATE_VISITS:
            tvd = metrics["per_state_tvd"][st]
            print(f"    {st:<16} TVD={tvd:.4f}  ({v} visits)")
        else:
            print(f"    {st:<16} (only {v} visits — excluded from TVD avg)")
    print()
    print("─── Three-form reward scoring (on trained-agent trajectories) ───")
    print(f"  α={CROSSOVER_ALPHA}, β={CROSSOVER_BETA}, scale_mult={CROSSOVER_ENG_SCALE_MULT}")
    print(f"  {'form':<20} {'mean':>9} {'median':>9} {'min':>9} {'max':>9} {'std':>9}")
    for f in ["adr0002_max_css", "mean_css", "high_css_share"]:
        s = metrics["per_form_returns"][f]
        print(f"  {f:<20} {s['mean']:>9.3f} {s['median']:>9.3f} "
              f"{s['min']:>9.3f} {s['max']:>9.3f} {s['std']:>9.3f}")
    print()
    print(f"wall time: {elapsed:.1f}s")
    print(f"output:    {output_dir}")
    print(f"summary:   {output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
