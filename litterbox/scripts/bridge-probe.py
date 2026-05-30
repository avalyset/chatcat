#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.26"]
# ///
"""
Stdio bridge latency probe for ChatcatEnv.

Spawns the TS bridge (src/cli/bridge.ts via tsx) and drives it from Python
with deterministic random actions for N episodes. Measures per-step
round-trip latency over the actual stdio + JSON path against the actual
SimCat env — not a JSON-only microbenchmark.

Reports the latency DISTRIBUTION (median, p90, p99, max), not just the
mean. p99 matters because a single slow step multiplies by the total
step count of a PPO run.

Reference anchor: in-process TS throughput via `pnpm rl:random
--episodes <N> --master-seed 1 --quiet`. The same env, no bridge.
Bridge overhead = the difference.

Usage:
  uv run scripts/bridge-probe.py [--episodes 10] [--master-seed 1] [--warmup-steps 1000]
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


ACTION_TYPES = ["idle", "slow_blink", "trill", "soft_purr", "side_glance", "pause"]


def spawn_bridge(litterbox_dir: Path) -> subprocess.Popen:
    return subprocess.Popen(
        ["pnpm", "exec", "tsx", "src/cli/bridge.ts"],
        cwd=str(litterbox_dir),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )


def send(bridge: subprocess.Popen, obj: dict) -> dict:
    assert bridge.stdin is not None and bridge.stdout is not None
    bridge.stdin.write(json.dumps(obj) + "\n")
    bridge.stdin.flush()
    line = bridge.stdout.readline()
    if not line:
        stderr = ""
        if bridge.stderr is not None:
            stderr = bridge.stderr.read()
        raise RuntimeError(f"bridge closed unexpectedly. stderr:\n{stderr}")
    return json.loads(line)


def sample_action(rng: np.random.Generator) -> dict:
    return {
        "type": ACTION_TYPES[int(rng.integers(0, len(ACTION_TYPES)))],
        "intensity": float(rng.random()),
    }


def measure_inprocess(litterbox_dir: Path, episodes: int) -> tuple[float, int, float]:
    """Returns (wall_seconds, total_steps_estimate, steps_per_sec) from pnpm rl:random."""
    result = subprocess.run(
        ["pnpm", "exec", "tsx", "src/cli/rl-random.ts",
         "--episodes", str(episodes), "--master-seed", "1", "--quiet"],
        cwd=str(litterbox_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pnpm rl:random failed (exit {result.returncode})\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    out = result.stdout
    wall_match = re.search(r"Wall time: ([\d.]+)s", out)
    mean_match = re.search(
        r"episode_length_ticks\s+n=\d+\s+min=[\d.]+\s+median=[\d.]+\s+mean=([\d.]+)",
        out,
    )
    if not wall_match or not mean_match:
        raise RuntimeError(f"could not parse rl:random output:\n{out}")
    wall = float(wall_match.group(1))
    mean_steps = float(mean_match.group(1))
    total = int(mean_steps * episodes)
    return wall, total, total / wall


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--master-seed", type=int, default=1)
    ap.add_argument("--warmup-steps", type=int, default=1000)
    args = ap.parse_args()

    litterbox = Path(__file__).resolve().parent.parent

    print("─── Reference anchor: in-process TS env (pnpm rl:random) ───")
    ip_wall, ip_steps, ip_sps = measure_inprocess(litterbox, args.episodes)
    print(f"  episodes:           {args.episodes}")
    print(f"  total steps (est):  {ip_steps:,}")
    print(f"  wall time:          {ip_wall:.2f}s")
    print(f"  in-process sps:     {ip_sps:,.0f} steps/sec")
    print()

    print("─── Spawning bridge subprocess ───")
    bridge = spawn_bridge(litterbox)
    try:
        latencies_ns: list[int] = []
        ended_reasons: dict[str, int] = {}
        bridge_start = time.perf_counter()

        for ep in range(args.episodes):
            ep_seed = int(
                np.random.default_rng(args.master_seed + ep * 1000).integers(0, 2**31 - 1)
            )
            action_rng = np.random.default_rng(args.master_seed + ep * 1000 + 1)

            reset_resp = send(bridge, {"type": "reset", "seed": ep_seed})
            if "error" in reset_resp:
                raise RuntimeError(f"reset error: {reset_resp['error']}")

            steps_this_ep = 0
            final_info = None
            while True:
                action = sample_action(action_rng)
                t0 = time.perf_counter_ns()
                resp = send(bridge, {"type": "step", "action": action})
                t1 = time.perf_counter_ns()
                latencies_ns.append(t1 - t0)
                steps_this_ep += 1
                if "error" in resp:
                    raise RuntimeError(f"step error: {resp['error']}")
                if resp["done"]:
                    final_info = resp["info"]
                    break
            reason = final_info["ended_reason"] if final_info else "unknown"
            ended_reasons[reason] = ended_reasons.get(reason, 0) + 1
            print(f"  ep {ep + 1}/{args.episodes}: {steps_this_ep:>5} steps, end={reason}")

        bridge_wall = time.perf_counter() - bridge_start
        send(bridge, {"type": "close"})
    finally:
        try:
            bridge.wait(timeout=5)
        except subprocess.TimeoutExpired:
            bridge.kill()

    total_steps = len(latencies_ns)
    warmup = min(args.warmup_steps, total_steps // 4)
    measured = np.array(latencies_ns[warmup:], dtype=np.int64)

    print()
    print("─── Bridge per-step round-trip latency (post-warmup) ───")
    print(f"  total step calls:   {total_steps:,}")
    print(f"  warmup discarded:   {warmup:,}")
    print(f"  measured steps:     {len(measured):,}")
    print(f"  median:             {np.median(measured) / 1000:>8.1f} µs")
    print(f"  p90:                {np.percentile(measured, 90) / 1000:>8.1f} µs")
    print(f"  p99:                {np.percentile(measured, 99) / 1000:>8.1f} µs")
    print(f"  max:                {np.max(measured) / 1000:>8.1f} µs")
    print(f"  mean:               {np.mean(measured) / 1000:>8.1f} µs")
    print()

    bridge_sps = total_steps / bridge_wall
    print("─── Throughput ───")
    print(f"  bridge:             {total_steps:,} steps / {bridge_wall:.2f}s = {bridge_sps:,.0f} steps/sec")
    print(f"  in-process:         {ip_sps:,.0f} steps/sec  (reference anchor)")
    print(f"  bridge overhead:    {ip_sps / bridge_sps:.1f}× slower than in-process")
    print()

    print("─── PPO scale projection (env steps only — excludes policy update time) ───")
    for budget_steps in (1_000_000, 10_000_000, 100_000_000):
        bridge_h = budget_steps / bridge_sps / 3600
        ip_h = budget_steps / ip_sps / 3600
        label = f"{budget_steps // 1_000_000}M steps"
        print(f"  {label:>10}:  bridge {bridge_h:>6.2f}h   in-process {ip_h:>6.2f}h")
    print()

    print(f"Termination split (bridge run): {ended_reasons}")


if __name__ == "__main__":
    main()
