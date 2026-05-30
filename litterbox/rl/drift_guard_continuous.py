#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.26", "gymnasium>=0.29,<2"]
# ///
"""
Drift guard for the continuous Python gym wrapper.

The continuous wrapper adds a new potential drift surface vs the Discrete
fase 1 wrapper: the Box(7,) → (type_idx via argmax, intensity via clip)
decoding. This guard verifies that decoding is consistent between the
gym wrapper and a direct-bridge path that executes the IDENTICAL decode
(imported from env_continuous.decode_continuous_action).

If they diverge, the drift is in the wrapper's step() implementation —
e.g., a missing dtype cast, an off-by-one slice, or an accidental
mutation of the action array before decode.

Test actions include values outside [0,1] (sampled from Normal(0.5, 0.5))
to simulate what PPO actually emits — CleanRL samples from an unbounded
Normal during rollouts, so we want the guard to cover those regimes.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from env_continuous import (  # noqa: E402
    ACTION_DIM,
    ChatcatGymContinuousEnv,
    decode_continuous_action,
    find_litterbox_dir,
)


def generate_actions(seed: int, n: int):
    """Mix bounded and unbounded samples to exercise both decode paths."""
    rng = np.random.default_rng(seed)
    # Half in-bounds uniform [0,1], half wider Normal — covers what PPO
    # actually emits during training (unclipped Normal samples).
    uniforms = rng.uniform(0.0, 1.0, size=(n // 2, ACTION_DIM)).astype(np.float32)
    normals = rng.normal(0.5, 0.5, size=(n - n // 2, ACTION_DIM)).astype(np.float32)
    return list(uniforms) + list(normals)


def run_via_wrapper(env_seed: int, actions):
    env = ChatcatGymContinuousEnv()
    try:
        obs, info = env.reset(seed=env_seed)
        traj = [{"obs": obs.tolist(), "reward": None, "done": False, "tick": 0}]
        for action in actions:
            obs, reward, terminated, truncated, info = env.step(action)
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
        for action in actions:
            # Use the SAME decode as the wrapper, so the test is "does the
            # wrapper actually invoke this decode and send the result" —
            # not "are two different decoders accidentally equivalent".
            action_type, intensity = decode_continuous_action(action)
            resp = send({
                "type": "step",
                "action": {"type": action_type, "intensity": intensity},
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

    print(f"env_seed={env_seed} action_seed=0xdeadbeef N={n_actions}  "
          f"(half uniform[0,1]^7, half Normal(0.5, 0.5)^7)")
    print("running through ChatcatGymContinuousEnv (Python gym wrapper)...")
    wrapper_traj = run_via_wrapper(env_seed, actions)
    print(f"  {len(wrapper_traj) - 1} steps")

    print("running through bridge subprocess directly (shared decode)...")
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
