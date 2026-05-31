"""
BaselineNormalizedChatcatEnv — ADR 0008.

Subclass of ChatcatGymContinuousEnv. On each reset, queries the TS bridge
(via the new `rule_based_episode` message type) for the v0.1 rule-based
ChatCatAgent's total episode reward on the SAME (traits, simcat_seed)
the RL env derives from `seed`. Stores it as `self.current_baseline_reward`.

On step, when the episode terminates, subtracts the baseline reward from
the final step's reward — equivalent in expectation to distributing
-baseline/episode_steps across all steps, but cleaner.

Sum of per-step rewards across the episode therefore equals
    R_agent_total - R_baseline(seed)
which is positive iff the agent outperformed the rule-based reference
on that cat, zero iff matched, negative iff worse. This is the
emergence-preserving signal ADR 0008 pre-registered.

info dict additions:
  - reset: `baseline_reward`, `baseline_steps`, `baseline_ended_reason`
    so the caller can record what the reference scored on this cat.
  - step (terminal): `baseline_reward` (same value), so the caller can
    diff agent vs reference directly without re-querying.
"""

import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from env_continuous import ChatcatGymContinuousEnv  # noqa: E402


class BaselineNormalizedChatcatEnv(ChatcatGymContinuousEnv):
    def __init__(
        self,
        litterbox_dir: Optional[Path] = None,
        reward_alpha: Optional[float] = None,
        reward_beta: Optional[float] = None,
        reward_engagement_scale_mult: Optional[float] = None,
    ) -> None:
        super().__init__(
            litterbox_dir=litterbox_dir,
            reward_alpha=reward_alpha,
            reward_beta=reward_beta,
            reward_engagement_scale_mult=reward_engagement_scale_mult,
        )
        self.current_baseline_reward: float = 0.0
        self.current_baseline_steps: int = 0
        self.current_baseline_ended_reason: str = ""

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ):
        # Let the base class do its usual reset (initialises np_random,
        # derives a concrete seed if seed=None, sends reset to the bridge,
        # records info["seed"] = the actually-used integer seed).
        obs, info = super().reset(seed=seed, options=options)
        actual_seed = int(info["seed"])

        # Query the rule-based reference policy's episode reward on the
        # SAME (traits, simcat_seed) the bridge just derived for the
        # RL env. Subprocess and reward parameters are inherited from
        # the base; the bridge uses the same env-var-derived alpha/beta/
        # scale_mult for the baseline rollout as for the RL env, so
        # subtraction is in the same units.
        baseline_resp = self._send({
            "type": "rule_based_episode",
            "seed": actual_seed,
        })
        if "error" in baseline_resp:
            raise RuntimeError(f"bridge rule_based_episode error: {baseline_resp['error']}")

        self.current_baseline_reward = float(baseline_resp["reward"])
        self.current_baseline_steps = int(baseline_resp["steps"])
        self.current_baseline_ended_reason = str(baseline_resp["ended_reason"])

        info["baseline_reward"] = self.current_baseline_reward
        info["baseline_steps"] = self.current_baseline_steps
        info["baseline_ended_reason"] = self.current_baseline_ended_reason
        return obs, info

    def step(self, action: Any):
        obs, reward, terminated, truncated, info = super().step(action)
        done = bool(terminated or truncated)
        if done:
            # Subtract the entire-episode baseline reward at the terminal
            # step. Per-step rewards earlier in the episode are unchanged;
            # this is a sparse adjustment at the end so the episode sum
            # equals R_agent_total - R_baseline(seed).
            reward = float(reward) - self.current_baseline_reward
            info["baseline_reward"] = self.current_baseline_reward
        return obs, reward, terminated, truncated, info
