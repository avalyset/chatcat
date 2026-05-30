"""
ChatcatGymEnv — gymnasium.Env wrapper around the stdio bridge
(litterbox/src/cli/bridge.ts, fase 0 commit 437d056).

Action space: Discrete(N_TYPES * N_INTENSITY_BINS) = Discrete(24).
  Each int decodes to (action_type_index, intensity_bin_index). Intensity
  bin centres are midpoints of 4 equal intervals in [0, 1]:
  0.125, 0.375, 0.625, 0.875. Rationale: the underlying TS env action
  space is (6 discrete types × continuous intensity), but CleanRL's
  ppo.py uses Categorical (Discrete only). Discretising the intensity
  axis keeps us on CleanRL's standard ppo.py without algorithm
  modifications. For real training (fase 2) the choice is between
  continuous-PPO (Box(7,) — one-hot type + intensity) or a library
  with native Tuple/MultiDiscrete support (SB3). Both are out of scope
  for the smoke test.

Observation space: Box(low=-inf, high=+inf, shape=(37,), dtype=float32).
  The actual ranges are bounded (most components in [0,1], gaze in
  [-1,1]) but we leave +/-inf so the wrapper does not pre-bake encoder
  assumptions. The encoder is src/rl/encoders.ts.

Reward: comes from the TS env across the bridge. Python does NOT compute
  reward. ADR 0007's crossover parameters (form adr0002_max_css,
  alpha=1.0, beta=0.5, engagement_scale=5/(tick_rate*60)) live in
  src/rl/env.ts as the env's default rewardParams — so they live in
  exactly one place.

Bridge lifecycle: each ChatcatGymEnv instance owns its own bridge
  subprocess. close() shuts it down cleanly via {"type": "close"}.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Optional, Tuple

import gymnasium as gym
import numpy as np
from gymnasium import spaces

ACTION_TYPES = ["idle", "slow_blink", "trill", "soft_purr", "side_glance", "pause"]
N_TYPES = len(ACTION_TYPES)
N_INTENSITY_BINS = 4
INTENSITY_BIN_CENTERS = np.array([0.125, 0.375, 0.625, 0.875], dtype=np.float64)
OBS_DIM = 37


def find_litterbox_dir() -> Path:
    """Resolves litterbox/ assuming this file is litterbox/rl/env.py."""
    return Path(__file__).resolve().parent.parent


class ChatcatGymEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, litterbox_dir: Optional[Path] = None) -> None:
        super().__init__()
        self.litterbox_dir = litterbox_dir or find_litterbox_dir()
        self.action_space = spaces.Discrete(N_TYPES * N_INTENSITY_BINS)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(OBS_DIM,), dtype=np.float32
        )
        self.proc: Optional[subprocess.Popen] = None
        self._closed = False

    def _ensure_started(self) -> None:
        if self.proc is None:
            self.proc = subprocess.Popen(
                ["pnpm", "exec", "tsx", "src/cli/bridge.ts"],
                cwd=str(self.litterbox_dir),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

    def _send(self, msg: dict) -> dict:
        assert (
            self.proc is not None
            and self.proc.stdin is not None
            and self.proc.stdout is not None
        )
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            stderr = self.proc.stderr.read() if self.proc.stderr else ""
            raise RuntimeError(
                f"bridge closed unexpectedly. stderr:\n{stderr}"
            )
        return json.loads(line)

    def _decode_action(self, action: Any) -> Tuple[str, float]:
        a = int(action)
        type_idx = a // N_INTENSITY_BINS
        bin_idx = a % N_INTENSITY_BINS
        return ACTION_TYPES[type_idx], float(INTENSITY_BIN_CENTERS[bin_idx])

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ):
        super().reset(seed=seed)
        self._ensure_started()
        if seed is None:
            seed = int(self.np_random.integers(0, 2**31 - 1))
        resp = self._send({"type": "reset", "seed": int(seed)})
        if "error" in resp:
            raise RuntimeError(f"bridge reset error: {resp['error']}")
        obs = np.asarray(resp["obs"], dtype=np.float32)
        return obs, resp["info"]

    def step(self, action: Any):
        action_type, intensity = self._decode_action(action)
        resp = self._send(
            {"type": "step", "action": {"type": action_type, "intensity": intensity}}
        )
        if "error" in resp:
            raise RuntimeError(f"bridge step error: {resp['error']}")
        obs = np.asarray(resp["obs"], dtype=np.float32)
        reward = float(resp["reward"])
        terminated = bool(resp["done"])
        truncated = False  # bridge's `done` covers all termination conditions
        return obs, reward, terminated, truncated, resp["info"]

    def close(self) -> None:
        if self.proc is not None and not self._closed:
            try:
                self._send({"type": "close"})
            except Exception:
                pass
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self._closed = True
            self.proc = None
