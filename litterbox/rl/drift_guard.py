#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.26", "gymnasium>=0.29"]
# ///
"""
Drift guard for the Python gym wrapper.

Fase 0 proved bridge.ts is lossless (BIT-IDENTICAL trajectories
in-process vs through the stdio + JSON layer). This guard verifies the
Python gym wrapper layer (env.py) does not introduce drift through
action conversion (Discrete -> (type, intensity)) or obs reshaping
(list -> np.float32 array).

Procedure: generate a fixed action sequence as (type_idx, bin_idx) pairs
seeded deterministically. Run them through TWO paths:
  1. ChatcatGymEnv: encode as Discrete(24) int = type_idx * 4 + bin_idx.
  2. Direct bridge subprocess: send (ACTION_TYPES[type_idx],
     INTENSITY_BIN_CENTERS[bin_idx]) as the bridge JSON contract.
Both should produce identical trajectories given the same env-seed.

If they diverge, the divergence is in the wrapper layer — exactly the
class of bug fase 0 ruled out for the bridge.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from env import (  # noqa: E402
    ACTION_TYPES,
    INTENSITY_BIN_CENTERS,
    N_INTENSITY_BINS,
    N_TYPES,
    ChatcatGymEnv,
    find_litterbox_dir,
)


def generate_actions(seed: int, n: int):
    rng = np.random.default_rng(seed)
    type_idxs = rng.integers(0, N_TYPES, size=n)
    bin_idxs = rng.integers(0, N_INTENSITY_BINS, size=n)
    return list(zip(type_idxs.tolist(), bin_idxs.tolist()))


def run_via_wrapper(env_seed: int, actions):
    env = ChatcatGymEnv()
    try:
        obs, info = env.reset(seed=env_seed)
        traj = [{"obs": obs.tolist(), "reward": None, "done": False, "tick": 0}]
        for type_idx, bin_idx in actions:
            a = type_idx * N_INTENSITY_BINS + bin_idx
            obs, reward, terminated, truncated, info = env.step(a)
            done = terminated or truncated
            traj.append({
                "obs": obs.tolist(),
                "reward": reward,
                "done": done,
                "tick": info["tick"],
            })
            if done:
                break
    finally:
        env.close()
    return traj


def run_via_bridge(litterbox_dir: Path, env_seed: int, actions):
    proc = subprocess.Popen(
        ["pnpm", "exec", "tsx", "src/cli/bridge.ts"],
        cwd=str(litterbox_dir),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )

    def send(msg):
        assert proc.stdin is not None and proc.stdout is not None
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    try:
        reset_resp = send({"type": "reset", "seed": env_seed})
        traj = [{
            "obs": reset_resp["obs"],
            "reward": None,
            "done": False,
            "tick": 0,
        }]
        for type_idx, bin_idx in actions:
            resp = send({
                "type": "step",
                "action": {
                    "type": ACTION_TYPES[type_idx],
                    "intensity": float(INTENSITY_BIN_CENTERS[bin_idx]),
                },
            })
            traj.append({
                "obs": resp["obs"],
                "reward": resp["reward"],
                "done": resp["done"],
                "tick": resp["info"]["tick"],
            })
            if resp["done"]:
                break
    finally:
        try:
            send({"type": "close"})
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    return traj


def diff(a, b):
    if len(a) != len(b):
        return f"length mismatch: wrapper={len(a)} bridge={len(b)}"
    for i, (x, y) in enumerate(zip(a, b)):
        if x["reward"] != y["reward"]:
            return f"step {i} reward: {x['reward']} vs {y['reward']}"
        if x["done"] != y["done"]:
            return f"step {i} done: {x['done']} vs {y['done']}"
        if x["tick"] != y["tick"]:
            return f"step {i} tick: {x['tick']} vs {y['tick']}"
        ox, oy = x["obs"], y["obs"]
        if len(ox) != len(oy):
            return f"step {i} obs length: {len(ox)} vs {len(oy)}"
        for j in range(len(ox)):
            if ox[j] != oy[j]:
                return f"step {i} obs[{j}]: {ox[j]} vs {oy[j]}"
    return None


def main():
    env_seed = 42
    n_actions = 500
    actions = generate_actions(0xdeadbeef, n_actions)

    print(f"env_seed={env_seed} action_seed=0xdeadbeef N={n_actions}")
    print("running through ChatcatGymEnv (Python gym wrapper)...")
    wrapper_traj = run_via_wrapper(env_seed, actions)
    print(f"  {len(wrapper_traj) - 1} steps")

    print("running through bridge subprocess directly...")
    direct_traj = run_via_bridge(find_litterbox_dir(), env_seed, actions)
    print(f"  {len(direct_traj) - 1} steps")

    verdict = diff(wrapper_traj, direct_traj)
    if verdict is None:
        n = len(wrapper_traj) - 1
        print(f"BIT-IDENTICAL — {n} steps, all (obs[0..36], reward, done, tick) match.")
    else:
        print(f"DIVERGED: {verdict}")
        sys.exit(1)


if __name__ == "__main__":
    main()
