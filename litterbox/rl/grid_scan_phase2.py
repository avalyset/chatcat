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
                    (mean_opt_outs_per_episode > PUSH_OPT_OUT_PER_EPISODE_THRESHOLD (40)
                     OR
                     high_css_share > PUSH_HIGH_CSS_SHARE_THRESHOLD (0.05))
                    — agent maintains high activity AND welfare degrades
                    measurably beyond random exploration. "Welfare degrades"
                    is the *outcome* (opt-outs or stress-state occupancy),
                    not a proxy on the agent's action intensity.
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

PUSH thresholds anchored to fase 1 random-Box(7,) baseline:
  opt_outs/episode  — random mean 25.77, std 5.13. 40 ≈ mean + 2.8σ:
    clearly above random-policy noise, achievable by an agent that
    actually drives the cat to LEAVING/RETREATING more often.
  high_css_share    — random mean 0.025, std 0.008. 0.05 ≈ mean + 3σ
    and exactly double the random mean: an agent that keeps the cat
    in CSS ≥ 4 more than twice as often as random exploration does.
  Empirically verified: pure random-policy through this classifier
    lands TRIVIAL (welfare terms below threshold, TVD below threshold).
    See --random-baseline mode.

Intensity-style mean_engagement_intensity is still reported in metrics
as context, but is NOT in the classification logic — it was a proxy
for the welfare outcome, which we now measure directly.

Other thresholds:
  - IDLE_OUT 0.90 cleanly excludes the constant-idle corner
  - entropy 0.5 bits (of max ~2.585) excludes constant-action
  - TVD 0.05 (mean over states with ≥50 visits) excludes
    state-blind/random; random-baseline gives TVD ≈ 0

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
IDLE_OUT_THRESHOLD = 0.90                # idle_share above → IDLE_OUT
PUSH_NON_IDLE_THRESHOLD = 0.80           # non_idle_share above, AND welfare bad → PUSH_THE_CAT
PUSH_OPT_OUT_PER_EPISODE_THRESHOLD = 40  # random mean+2.8σ (25.77+2.8·5.13)
PUSH_HIGH_CSS_SHARE_THRESHOLD = 0.05     # random mean+3σ (≈ 2× random mean 0.025)
TRIVIAL_ENTROPY_THRESHOLD = 0.5          # action_type_entropy below → TRIVIAL
TRIVIAL_TVD_THRESHOLD = 0.05             # state-conditional TVD below → TRIVIAL
MIN_STATE_VISITS = 50                    # states with fewer visits dropped from TVD avg

ENGAGEMENT_TYPES = {"slow_blink", "trill", "soft_purr", "side_glance"}
SIMCAT_STATES = [
    "ABSENT", "RESTING", "ALERT", "CURIOUS", "APPROACHING",
    "ENGAGING", "OVERSTIMULATED", "STRESSED", "RETREATING", "LEAVING",
]
HIGH_CSS_THRESHOLD = 4  # Kessler & Turner 1997 — matches src/rl/reward.ts


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model-path", type=str, default=None,
                   help="Path to agent.pt from train_phase2.py (omit with --random-baseline)")
    p.add_argument("--random-baseline", action="store_true", default=False,
                   help="Use uniform Box(7,) sampling instead of a trained agent. "
                        "Calibration tool: empirically anchors the classifier's behaviour "
                        "on a known-degenerate baseline before evaluating trained models.")
    p.add_argument("--episodes", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--output-dir", type=str, default=None,
                   help="Defaults to <model-path-parent>/grid_scan/ for trained agents, "
                        "or /tmp/chatcat-rl-runs/random_baseline/ for --random-baseline.")
    args = p.parse_args()
    if not args.random_baseline and args.model_path is None:
        p.error("--model-path is required unless --random-baseline is set")
    return args


def load_agent(model_path: Path, env) -> Agent:
    # Infer actor_logstd discipline from the run's run_config.json so the
    # eval Agent matches the one that produced agent.pt (Parameter vs
    # frozen-buffer). Falls back to None (Parameter) for legacy runs that
    # predate the --frozen-logstd flag.
    frozen_logstd = None
    config_path = model_path.parent / "run_config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text())
            frozen_logstd = cfg.get("frozen_logstd")
        except Exception:
            pass
    agent = Agent(env, frozen_logstd=frozen_logstd)
    state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
    agent.load_state_dict(state_dict)
    agent.eval()
    return agent


def _make_env_thunk():
    env = ChatcatGymContinuousEnv(
        reward_alpha=CROSSOVER_ALPHA,
        reward_beta=CROSSOVER_BETA,
        reward_engagement_scale_mult=CROSSOVER_ENG_SCALE_MULT,
    )
    return gym.vector.SyncVectorEnv([lambda: env])


def run_evaluation(action_sampler, episodes: int, master_seed: int):
    """Run `episodes` evaluation episodes, calling action_sampler(obs, rng)
    each step. action_sampler must return action of shape (1, ACTION_DIM).
    Used by both the agent path and the --random-baseline path."""
    env_thunk = _make_env_thunk()
    rng = np.random.default_rng(master_seed)
    torch.manual_seed(master_seed)

    trajectories = []
    try:
        for ep in range(episodes):
            ep_seed = int(rng.integers(0, 2**31 - 1))
            # Per-episode action rng for the random baseline (deterministic per ep
            # given master_seed); ignored by agent sampler.
            action_rng = np.random.default_rng(master_seed * 1_000_003 + ep)
            obs, _ = env_thunk.reset(seed=ep_seed)
            ep_steps = []
            done = False
            while not done:
                action = action_sampler(obs, action_rng)
                action_type, intensity = decode_continuous_action(action[0])
                state_idx = int(np.argmax(obs[0, :len(SIMCAT_STATES)]))
                next_obs, reward, terminations, truncations, infos = env_thunk.step(action)
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


def make_agent_sampler(agent: Agent):
    def sample(obs, _rng):
        with torch.no_grad():
            action_t, _, _, _ = agent.get_action_and_value(torch.Tensor(obs))
        return action_t.cpu().numpy()
    return sample


def random_box_sampler(_obs, rng):
    return rng.uniform(0.0, 1.0, size=(1, ACTION_DIM)).astype(np.float32)


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

    # Welfare aggregates (used by PUSH_THE_CAT classification)
    total_high_css_ticks = sum(a["high_css_ticks"] for a in per_ep_aggregates)
    total_steps = sum(a["n_steps"] for a in per_ep_aggregates)
    high_css_share_overall = total_high_css_ticks / max(1, total_steps)
    opt_outs_per_ep = [a["opt_outs"] for a in per_ep_aggregates]
    mean_opt_outs = float(np.mean(opt_outs_per_ep)) if opt_outs_per_ep else 0.0

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
        "mean_opt_outs_per_episode": mean_opt_outs,
        "high_css_share_overall": high_css_share_overall,
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
    welfare_bad_opts = m["mean_opt_outs_per_episode"] > PUSH_OPT_OUT_PER_EPISODE_THRESHOLD
    welfare_bad_css = m["high_css_share_overall"] > PUSH_HIGH_CSS_SHARE_THRESHOLD
    if m["non_idle_share"] > PUSH_NON_IDLE_THRESHOLD and (welfare_bad_opts or welfare_bad_css):
        reasons = []
        if welfare_bad_opts:
            reasons.append(
                f"mean_opt_outs_per_episode={m['mean_opt_outs_per_episode']:.2f} "
                f"> {PUSH_OPT_OUT_PER_EPISODE_THRESHOLD}"
            )
        if welfare_bad_css:
            reasons.append(
                f"high_css_share_overall={m['high_css_share_overall']:.4f} "
                f"> {PUSH_HIGH_CSS_SHARE_THRESHOLD}"
            )
        return "PUSH_THE_CAT", (
            f"non_idle_share={m['non_idle_share']:.3f} > {PUSH_NON_IDLE_THRESHOLD} "
            f"AND welfare degrades: {' AND '.join(reasons)} "
            f"— agent maintains activity while cat welfare measurably worsens"
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
        f"[{1 - IDLE_OUT_THRESHOLD}, {PUSH_NON_IDLE_THRESHOLD}] or welfare ok, "
        f"entropy={m['action_type_entropy_bits']:.3f} bits ≥ {TRIVIAL_ENTROPY_THRESHOLD}, "
        f"state_TVD={m['mean_state_conditional_tvd']:.4f} ≥ {TRIVIAL_TVD_THRESHOLD}"
    )


def main():
    args = parse_args()

    if args.random_baseline:
        model_path = None
        output_dir = (Path(args.output_dir) if args.output_dir
                      else Path("/tmp/chatcat-rl-runs/random_baseline"))
        sampler = random_box_sampler
        print("policy: RANDOM BASELINE (uniform Box(7,) sampling — no model)")
    else:
        model_path = Path(args.model_path)
        if not model_path.exists():
            print(f"model not found: {model_path}", file=sys.stderr)
            sys.exit(1)
        output_dir = (Path(args.output_dir) if args.output_dir
                      else model_path.parent / "grid_scan")
        print(f"loading model: {model_path}")
        # Need an env instance to size Agent; not used otherwise here.
        sizing_env = ChatcatGymContinuousEnv(
            reward_alpha=CROSSOVER_ALPHA, reward_beta=CROSSOVER_BETA,
            reward_engagement_scale_mult=CROSSOVER_ENG_SCALE_MULT,
        )
        sizing_vec = gym.vector.SyncVectorEnv([lambda: sizing_env])
        agent = load_agent(model_path, sizing_vec)
        sizing_vec.close()
        sampler = make_agent_sampler(agent)

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"running {args.episodes} evaluation episodes, master_seed={args.seed}")
    print(f"reward regime (matches training): adr0002_max_css, "
          f"α={CROSSOVER_ALPHA} β={CROSSOVER_BETA} scale_mult={CROSSOVER_ENG_SCALE_MULT}")
    print()

    start = time.time()
    trajectories = run_evaluation(sampler, args.episodes, args.seed)
    elapsed = time.time() - start

    metrics = compute_metrics(trajectories)
    label, reason = classify(metrics)

    summary = {
        "policy": "random_baseline" if args.random_baseline else "trained_agent",
        "model_path": str(model_path) if model_path else None,
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
            "PUSH_OPT_OUT_PER_EPISODE_THRESHOLD": PUSH_OPT_OUT_PER_EPISODE_THRESHOLD,
            "PUSH_HIGH_CSS_SHARE_THRESHOLD": PUSH_HIGH_CSS_SHARE_THRESHOLD,
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
    print(f"  idle_share:                  {metrics['idle_share']:.4f}")
    print(f"  non_idle_share:              {metrics['non_idle_share']:.4f}")
    print(f"  action_type_entropy:         {metrics['action_type_entropy_bits']:.4f} bits "
          f"(max = {math.log2(N_TYPES):.4f})")
    print(f"  mean_engagement_intensity:   {metrics['mean_engagement_intensity']:.4f}  (context only — not in classification)")
    print(f"  type marginal:")
    for at in ACTION_TYPES:
        print(f"    {at:<14} {metrics['type_marginal'][at]:.4f}  "
              f"({metrics['type_counts'][at]:>6} steps)")
    print()
    print("─── Welfare aggregates (drive PUSH_THE_CAT classification) ───")
    print(f"  mean_opt_outs_per_episode:   {metrics['mean_opt_outs_per_episode']:.2f}  "
          f"(threshold {PUSH_OPT_OUT_PER_EPISODE_THRESHOLD})")
    print(f"  high_css_share_overall:      {metrics['high_css_share_overall']:.4f}  "
          f"(threshold {PUSH_HIGH_CSS_SHARE_THRESHOLD})")
    print()
    print("─── State-conditional behaviour ───")
    print(f"  mean_state_conditional_tvd:  {metrics['mean_state_conditional_tvd']:.4f}")
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
