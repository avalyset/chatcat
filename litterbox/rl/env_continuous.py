"""
ChatcatGymContinuousEnv — gymnasium.Env with continuous Box(7,) action.

This is the training-path env (fase 2 onward). ChatcatGymEnv (Discrete(24))
in env.py was fase 1 smoke scaffolding and is kept for reference only.

Action shape: Box(low=0, high=1, shape=(7,), dtype=float32).
  - dim 0..5: action-type scores. argmax decodes to action_type_index.
    Bounds [0,1] are ADVISORY here — CleanRL's ppo_continuous_action.py
    samples from an unbounded Normal(μ, exp(logstd)), so values may go
    negative or exceed 1. argmax over the raw 6 scores is invariant to
    those bounds (clip(0, ·) would push all-negative scores to a degenerate
    "all-zero → argmax=0=idle" initial regime — we deliberately do not
    clip the type scores).
  - dim 6: intensity. Bounds [0,1] are EXACT. Wrapper clips to [0,1] before
    sending to the bridge, so the agent can target the 0.3 ethics threshold
    (capIntensityForRetreat) with float precision rather than the 4-bin
    approximation the Discrete(24) smoke env had.

Observation space, reward, and bridge lifecycle: identical to env.py.

Why a 7-dim Box and not e.g. Box(2,) = (type_as_float, intensity)?
  The action types in encoders.ts (idle, slow_blink, trill, soft_purr,
  side_glance, pause) are a categorical axis with no natural ordering or
  continuum. Rounding a single float to a type index produces
  discontinuous gradients at bin boundaries and starves the PPO actor of
  signal between two adjacent types. The 6-logit + argmax form is the
  standard "categorical via continuous logits" trick for Box-only envs.
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
ACTION_DIM = N_TYPES + 1  # 6 type scores + 1 intensity
OBS_DIM = 37


def find_litterbox_dir() -> Path:
    """Resolves litterbox/ assuming this file is litterbox/rl/env_continuous.py."""
    return Path(__file__).resolve().parent.parent


def decode_continuous_action(action: Any) -> Tuple[str, float]:
    """Shared decode used by both the env step and the drift guard's
    direct-bridge path, so both paths execute identical decoding logic."""
    a = np.asarray(action, dtype=np.float64)
    if a.shape != (ACTION_DIM,):
        raise ValueError(f"expected action shape ({ACTION_DIM},), got {a.shape}")
    type_idx = int(np.argmax(a[:N_TYPES]))
    intensity = float(np.clip(a[N_TYPES], 0.0, 1.0))
    return ACTION_TYPES[type_idx], intensity


class ChatcatGymContinuousEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, litterbox_dir: Optional[Path] = None) -> None:
        super().__init__()
        self.litterbox_dir = litterbox_dir or find_litterbox_dir()
        self.action_space = spaces.Box(
            low=0.0, high=1.0, shape=(ACTION_DIM,), dtype=np.float32
        )
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
            raise RuntimeError(f"bridge closed unexpectedly. stderr:\n{stderr}")
        return json.loads(line)

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
        action_type, intensity = decode_continuous_action(action)
        resp = self._send(
            {"type": "step", "action": {"type": action_type, "intensity": intensity}}
        )
        if "error" in resp:
            raise RuntimeError(f"bridge step error: {resp['error']}")
        obs = np.asarray(resp["obs"], dtype=np.float32)
        reward = float(resp["reward"])
        terminated = bool(resp["done"])
        truncated = False
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
