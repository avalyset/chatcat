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
ADR 0009 end-to-end verification: load the trained ADR 0008-1 agent
(which we know emitted intensity ~0.70 in RETREATING state) and run a
few episodes through the now-enforced env. Confirm that:

  1. cap_applied=true fires in the info dict whenever the agent attempts
     to overshoot in RETREATING/LEAVING
  2. simcat receives the capped intensity (≤ 0.30 for allowed types,
     idle for disallowed types)
  3. the original (pre-cap) intensity is preserved in info, so empirical
     traceability of attempted overshoots is intact

Runs 5 episodes (fast). Aggregates cap-event counts and prints both raw
counts and a few sample events with original-vs-enforced numbers.
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch
import gymnasium as gym  # noqa: E402

from env_continuous import ChatcatGymContinuousEnv  # noqa: E402
from train_phase2 import Agent  # noqa: E402

MODEL_PATH = Path("/tmp/chatcat-rl-runs/phase2_baseline_norm__seed1__1780210056/agent.pt")
N_EPISODES = 5
SEED = 1


def main():
    if not MODEL_PATH.exists():
        print(f"model not found: {MODEL_PATH}", file=sys.stderr)
        sys.exit(1)

    env = ChatcatGymContinuousEnv()
    env_vec = gym.vector.SyncVectorEnv([lambda: env])

    agent = Agent(env_vec, frozen_logstd=None)
    agent.load_state_dict(torch.load(MODEL_PATH, map_location="cpu", weights_only=True))
    agent.eval()

    rng = np.random.default_rng(SEED)
    torch.manual_seed(SEED)

    total_steps = 0
    cap_count = 0
    cap_by_rule = defaultdict(int)
    overshoot_sum = 0.0
    overshoot_max = 0.0
    samples = []  # first 5 cap-applied events for display

    print(f"loading model: {MODEL_PATH}")
    print(f"running {N_EPISODES} episodes through the ADR-0009-enforced env...")
    print()
    t0 = time.time()
    for ep in range(N_EPISODES):
        ep_seed = int(rng.integers(0, 2**31 - 1))
        obs, _ = env_vec.reset(seed=ep_seed)
        done = False
        ep_steps = 0
        ep_caps = 0
        while not done:
            obs_t = torch.Tensor(obs)
            with torch.no_grad():
                action_t, _, _, _ = agent.get_action_and_value(obs_t)
            action_np = action_t.cpu().numpy()
            next_obs, _, term, trunc, infos = env_vec.step(action_np)
            done = bool(term[0] or trunc[0])
            total_steps += 1
            ep_steps += 1
            cap = infos["ethics_enforcement"]
            cap_applied = bool(cap["cap_applied"][0])
            if cap_applied:
                cap_count += 1
                ep_caps += 1
                rule = str(cap["rule"][0])
                cap_by_rule[rule] += 1
                overshoot = float(cap["original_intensity"][0]) - float(cap["enforced_intensity"][0])
                overshoot_sum += overshoot
                if overshoot > overshoot_max:
                    overshoot_max = overshoot
                if len(samples) < 5:
                    samples.append({
                        "ep": ep,
                        "step": ep_steps,
                        "original_type": str(cap["original_action_type"][0]),
                        "original_intensity": float(cap["original_intensity"][0]),
                        "enforced_type": str(cap["enforced_action_type"][0]),
                        "enforced_intensity": float(cap["enforced_intensity"][0]),
                        "rule": rule,
                    })
            obs = next_obs
        print(f"  ep {ep + 1}/{N_EPISODES}  seed={ep_seed}  steps={ep_steps}  cap_applied_count={ep_caps}")

    elapsed = time.time() - t0
    env_vec.close()

    print()
    print(f"=== ADR 0009 end-to-end verification ===")
    print(f"  episodes:                {N_EPISODES}")
    print(f"  total steps:             {total_steps}")
    print(f"  cap_applied (total):     {cap_count}  ({100 * cap_count / max(1, total_steps):.2f}%)")
    print(f"  cap by rule:")
    for rule, n in sorted(cap_by_rule.items(), key=lambda kv: -kv[1]):
        print(f"    {rule:<30}  {n}")
    if cap_count > 0:
        print(f"  overshoot_sum:           {overshoot_sum:.2f}  (sum of original - enforced intensity)")
        print(f"  overshoot_max:           {overshoot_max:.4f}  (worst single attempted overshoot)")
        print(f"  mean overshoot per cap:  {overshoot_sum / cap_count:.4f}")
    else:
        print(f"  (no caps fired — model never attempted to overshoot in 5 episodes; this would be")
        print(f"   surprising given Q3 in the analysis showed RETREATING intensity 0.70)")
    print()
    print(f"  first {len(samples)} cap events:")
    for s in samples:
        print(f"    ep{s['ep']} step{s['step']}: {s['original_type']}@{s['original_intensity']:.4f} → "
              f"{s['enforced_type']}@{s['enforced_intensity']:.4f}  ({s['rule']})")
    print()
    print(f"wall time: {elapsed:.1f}s")

    # Pass if cap fired at least once (given known agent that overshoots in RETREATING)
    if cap_count == 0:
        print("WARNING: no cap fired — unexpected given the ADR 0008-1 agent's known RETREATING overshoot.")
        sys.exit(2)
    print("VERIFIED: ethics-monitor enforce() intercepts RL agent actions on the RL path.")


if __name__ == "__main__":
    main()
