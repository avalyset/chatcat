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
Phase 2 PPO training — ADR 0007 crossover regime.

Built on CleanRL's ppo_continuous_action.py (algorithm unchanged). Reward
parameters set to ADR 0007's crossover starting point (the only grid
point where neither reward component is pre-deleted from the gradient
under random exploration):

  reward form        = adr0002_max_css   (TS env default)
  α (max_CSS coef)   = 1.0
  β (opt_outs coef)  = 0.5
  engagement_scale   = 5 / (tick_rate * 60)   (i.e. scale_mult = 5.0)

These are forwarded to the TS bridge via CHATCAT_ALPHA / CHATCAT_BETA /
CHATCAT_ENG_SCALE_MULT env vars (bridge.ts reads them at startup) — so
the reward formulation lives in exactly one place (src/rl/env.ts) and
ADR 0007's calibration choice is reproducible from this file alone.

PPO hyperparameters follow CleanRL's ppo_continuous_action.py reference
defaults (num_steps=2048, num_minibatches=32, update_epochs=10,
learning_rate=3e-4) — not the smoke-test's smaller-batch settings.

Default --total-timesteps = 5_000_000 ≈ 42 min wall time on the
fase 0-measured 2k sps (PPO loop inclusive of bridge + gradients).
Rationale:
  - CleanRL ppo_continuous benchmarks on simple Box envs typically need
    1–3M steps for convergence; 5M is generous without being wasteful.
  - Within ADR 0002's $10–50 compute budget by 100× margin on CPU.
  - Short enough to iterate same-day if the first run is non-trivial
    but suboptimal.
  - User can override with --total-timesteps for longer runs.

Output: /tmp/chatcat-rl-runs/phase2__seed{S}__{timestamp}/
  agent.pt           — final model state_dict (loaded by grid_scan_phase2.py)
  metrics.jsonl      — one row per PPO update (loss, sps, ep stats)
  run_config.json    — full args + reward params for reproducibility

Determinism: same --seed → bit-identical agent.pt across re-runs.

Usage (autonomous; CC runs and reports once at the end):
  cd litterbox
  uv run rl/train_phase2.py --seed 1
  # ≈ 30–90 min on Apple Silicon, then run grid_scan_phase2.py against agent.pt
"""

import argparse
import hashlib
import json
import random
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions.normal import Normal

import gymnasium as gym  # noqa: E402
from env_continuous import ChatcatGymContinuousEnv  # noqa: E402

# ADR 0007 crossover regime — pre-registered. Changing these requires an
# ADR 0007 revision, not an edit here.
CROSSOVER_ALPHA = 1.0
CROSSOVER_BETA = 0.5
CROSSOVER_ENG_SCALE_MULT = 5.0


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--exp-name", type=str, default="phase2")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--total-timesteps", type=int, default=5_000_000)
    p.add_argument("--learning-rate", type=float, default=3e-4)
    p.add_argument("--num-envs", type=int, default=1)
    p.add_argument("--num-steps", type=int, default=2048)
    p.add_argument("--anneal-lr", action="store_true", default=True)
    p.add_argument("--gamma", type=float, default=0.99)
    p.add_argument("--gae-lambda", type=float, default=0.95)
    p.add_argument("--num-minibatches", type=int, default=32)
    p.add_argument("--update-epochs", type=int, default=10)
    p.add_argument("--norm-adv", action="store_true", default=True)
    p.add_argument("--clip-coef", type=float, default=0.2)
    p.add_argument("--clip-vloss", action="store_true", default=True)
    p.add_argument("--ent-coef", type=float, default=0.0)
    p.add_argument("--vf-coef", type=float, default=0.5)
    p.add_argument("--max-grad-norm", type=float, default=0.5)
    p.add_argument("--output-dir", type=str, default="/tmp/chatcat-rl-runs")
    p.add_argument("--frozen-logstd", type=float, default=None,
                   help="If set, actor_logstd is registered as a fixed buffer at this value "
                        "(per-dim) instead of a learnable Parameter. Used for ablation tests "
                        "where the policy variance must not drift. When unset (default), "
                        "actor_logstd is a learnable Parameter initialised to 0.0 — the "
                        "CleanRL ppo_continuous_action.py convention, and the baseline regime "
                        "that produced run 1's agent.pt.")
    args = p.parse_args()
    args.batch_size = args.num_envs * args.num_steps
    args.minibatch_size = args.batch_size // args.num_minibatches
    return args


def make_env(seed):
    def thunk():
        env = ChatcatGymContinuousEnv(
            reward_alpha=CROSSOVER_ALPHA,
            reward_beta=CROSSOVER_BETA,
            reward_engagement_scale_mult=CROSSOVER_ENG_SCALE_MULT,
        )
        env.action_space.seed(seed)
        return env
    return thunk


def layer_init(layer, std=np.sqrt(2), bias_const=0.0):
    torch.nn.init.orthogonal_(layer.weight, std)
    torch.nn.init.constant_(layer.bias, bias_const)
    return layer


class Agent(nn.Module):
    def __init__(self, envs, frozen_logstd: float | None = None):
        """
        frozen_logstd:
          None  → actor_logstd is a learnable Parameter initialised to 0.0
                  (CleanRL ppo_continuous_action.py default; run 1 regime).
          float → actor_logstd is a non-learnable buffer filled with the
                  given value across all action dims. Used for ablation
                  tests where policy variance must not drift during
                  training. Saved in state_dict; restored on load.
        """
        super().__init__()
        obs_dim = int(np.array(envs.single_observation_space.shape).prod())
        action_dim = int(np.prod(envs.single_action_space.shape))
        self.critic = nn.Sequential(
            layer_init(nn.Linear(obs_dim, 64)),
            nn.Tanh(),
            layer_init(nn.Linear(64, 64)),
            nn.Tanh(),
            layer_init(nn.Linear(64, 1), std=1.0),
        )
        self.actor_mean = nn.Sequential(
            layer_init(nn.Linear(obs_dim, 64)),
            nn.Tanh(),
            layer_init(nn.Linear(64, 64)),
            nn.Tanh(),
            layer_init(nn.Linear(64, action_dim), std=0.01),
        )
        self.logstd_is_frozen = frozen_logstd is not None
        if frozen_logstd is None:
            self.actor_logstd = nn.Parameter(torch.zeros(1, action_dim))
        else:
            self.register_buffer(
                "actor_logstd",
                torch.full((1, action_dim), float(frozen_logstd), dtype=torch.float32),
            )

    def get_value(self, x):
        return self.critic(x)

    def get_action_and_value(self, x, action=None):
        action_mean = self.actor_mean(x)
        action_logstd = self.actor_logstd.expand_as(action_mean)
        action_std = torch.exp(action_logstd)
        probs = Normal(action_mean, action_std)
        if action is None:
            action = probs.sample()
        return (
            action,
            probs.log_prob(action).sum(1),
            probs.entropy().sum(1),
            self.critic(x),
        )


def state_dict_hash(sd) -> str:
    h = hashlib.sha256()
    for k in sorted(sd.keys()):
        h.update(k.encode())
        h.update(sd[k].cpu().numpy().tobytes())
    return h.hexdigest()


def main():
    args = parse_args()
    run_name = f"{args.exp_name}__seed{args.seed}__{int(time.time())}"
    output_dir = Path(args.output_dir) / run_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Persist config + reward params for reproducibility.
    config = {
        **vars(args),
        "reward": {
            "form": "adr0002_max_css",
            "alpha": CROSSOVER_ALPHA,
            "beta": CROSSOVER_BETA,
            "engagement_scale_mult": CROSSOVER_ENG_SCALE_MULT,
            "adr_reference": "ADR 0007 crossover regime",
        },
    }
    (output_dir / "run_config.json").write_text(json.dumps(config, indent=2))

    metrics_file = open(output_dir / "metrics.jsonl", "w")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.use_deterministic_algorithms(True, warn_only=True)

    device = torch.device("cpu")

    envs = gym.vector.SyncVectorEnv(
        [make_env(args.seed + i) for i in range(args.num_envs)]
    )
    assert isinstance(envs.single_action_space, gym.spaces.Box)

    agent = Agent(envs, frozen_logstd=args.frozen_logstd).to(device)
    optimizer = optim.Adam(agent.parameters(), lr=args.learning_rate, eps=1e-5)
    if agent.logstd_is_frozen:
        print(f"actor_logstd FROZEN at {args.frozen_logstd} (per-dim std ≈ "
              f"{float(np.exp(args.frozen_logstd)):.4f})")

    obs_shape = envs.single_observation_space.shape
    act_shape = envs.single_action_space.shape
    obs = torch.zeros((args.num_steps, args.num_envs) + obs_shape).to(device)
    actions = torch.zeros((args.num_steps, args.num_envs) + act_shape).to(device)
    logprobs = torch.zeros((args.num_steps, args.num_envs)).to(device)
    rewards = torch.zeros((args.num_steps, args.num_envs)).to(device)
    dones = torch.zeros((args.num_steps, args.num_envs)).to(device)
    values = torch.zeros((args.num_steps, args.num_envs)).to(device)

    global_step = 0
    start_time = time.time()
    next_obs, _ = envs.reset(seed=args.seed)
    next_obs = torch.Tensor(next_obs).to(device)
    next_done = torch.zeros(args.num_envs).to(device)
    num_updates = args.total_timesteps // args.batch_size

    cur_return = np.zeros(args.num_envs, dtype=np.float64)
    cur_length = np.zeros(args.num_envs, dtype=np.int64)
    recent_returns: list[float] = []
    nan_detected = False
    last_loss = float("nan")
    interrupted = False

    def handle_interrupt(_signum, _frame):
        nonlocal interrupted
        interrupted = True
        print("\n[interrupted — saving current model and exiting cleanly]")
    signal.signal(signal.SIGINT, handle_interrupt)

    print(f"phase 2 training starting: {num_updates} updates × "
          f"{args.batch_size} batch = {args.total_timesteps} total env steps")
    print(f"output: {output_dir}")
    print(f"reward: adr0002_max_css α={CROSSOVER_ALPHA} β={CROSSOVER_BETA} "
          f"scale_mult={CROSSOVER_ENG_SCALE_MULT}")
    print()

    for update in range(1, num_updates + 1):
        if interrupted:
            break
        if args.anneal_lr:
            frac = 1.0 - (update - 1.0) / num_updates
            optimizer.param_groups[0]["lr"] = frac * args.learning_rate

        for step in range(args.num_steps):
            global_step += args.num_envs
            obs[step] = next_obs
            dones[step] = next_done
            with torch.no_grad():
                action, logprob, _, value = agent.get_action_and_value(next_obs)
                values[step] = value.flatten()
            actions[step] = action
            logprobs[step] = logprob

            next_obs_np, reward, terminations, truncations, _ = envs.step(
                action.cpu().numpy()
            )
            next_done_np = np.logical_or(terminations, truncations)
            rewards[step] = torch.tensor(reward, dtype=torch.float32).to(device).view(-1)

            cur_return += reward
            cur_length += 1
            for env_idx in range(args.num_envs):
                if next_done_np[env_idx]:
                    recent_returns.append(float(cur_return[env_idx]))
                    if len(recent_returns) > 100:
                        recent_returns.pop(0)
                    cur_return[env_idx] = 0
                    cur_length[env_idx] = 0

            next_obs = torch.Tensor(next_obs_np).to(device)
            next_done = torch.Tensor(next_done_np.astype(np.float32)).to(device)

        with torch.no_grad():
            next_value = agent.get_value(next_obs).reshape(1, -1)
            advantages = torch.zeros_like(rewards).to(device)
            lastgaelam = 0
            for t in reversed(range(args.num_steps)):
                if t == args.num_steps - 1:
                    nextnonterminal = 1.0 - next_done
                    nextvalues = next_value
                else:
                    nextnonterminal = 1.0 - dones[t + 1]
                    nextvalues = values[t + 1]
                delta = rewards[t] + args.gamma * nextvalues * nextnonterminal - values[t]
                advantages[t] = lastgaelam = (
                    delta + args.gamma * args.gae_lambda * nextnonterminal * lastgaelam
                )
            returns = advantages + values

        b_obs = obs.reshape((-1,) + obs_shape)
        b_logprobs = logprobs.reshape(-1)
        b_actions = actions.reshape((-1,) + act_shape)
        b_advantages = advantages.reshape(-1)
        b_returns = returns.reshape(-1)
        b_values = values.reshape(-1)

        b_inds = np.arange(args.batch_size)
        for _epoch in range(args.update_epochs):
            np.random.shuffle(b_inds)
            for start in range(0, args.batch_size, args.minibatch_size):
                end = start + args.minibatch_size
                mb_inds = b_inds[start:end]
                _, newlogprob, entropy, newvalue = agent.get_action_and_value(
                    b_obs[mb_inds], b_actions[mb_inds]
                )
                logratio = newlogprob - b_logprobs[mb_inds]
                ratio = logratio.exp()
                mb_advantages = b_advantages[mb_inds]
                if args.norm_adv:
                    mb_advantages = (mb_advantages - mb_advantages.mean()) / (mb_advantages.std() + 1e-8)
                pg_loss1 = -mb_advantages * ratio
                pg_loss2 = -mb_advantages * torch.clamp(ratio, 1 - args.clip_coef, 1 + args.clip_coef)
                pg_loss = torch.max(pg_loss1, pg_loss2).mean()
                newvalue = newvalue.view(-1)
                if args.clip_vloss:
                    v_loss_unclipped = (newvalue - b_returns[mb_inds]) ** 2
                    v_clipped = b_values[mb_inds] + torch.clamp(
                        newvalue - b_values[mb_inds], -args.clip_coef, args.clip_coef,
                    )
                    v_loss_clipped = (v_clipped - b_returns[mb_inds]) ** 2
                    v_loss = 0.5 * torch.max(v_loss_unclipped, v_loss_clipped).mean()
                else:
                    v_loss = 0.5 * ((newvalue - b_returns[mb_inds]) ** 2).mean()
                entropy_loss = entropy.mean()
                loss = pg_loss - args.ent_coef * entropy_loss + v_loss * args.vf_coef
                if torch.isnan(loss):
                    nan_detected = True
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(agent.parameters(), args.max_grad_norm)
                optimizer.step()

        last_loss = float(loss.item())
        elapsed = time.time() - start_time
        sps = int(global_step / max(1e-6, elapsed))
        ep_mean = float(np.mean(recent_returns)) if recent_returns else float("nan")
        metrics_file.write(json.dumps({
            "update": update, "global_step": global_step, "elapsed_s": elapsed,
            "sps": sps, "loss": last_loss,
            "policy_loss": float(pg_loss.item()),
            "value_loss": float(v_loss.item()),
            "entropy": float(entropy_loss.item()),
            "lr": float(optimizer.param_groups[0]["lr"]),
            "ep_return_mean_recent": ep_mean,
            "ep_return_n_recent": len(recent_returns),
        }) + "\n")
        metrics_file.flush()
        if update % 10 == 0 or update == 1 or update == num_updates:
            print(f"update={update}/{num_updates}  step={global_step}  "
                  f"sps={sps}  loss={last_loss:.4f}  "
                  f"ep_ret_mean(N={len(recent_returns)})={ep_mean:.2f}")

    model_path = output_dir / "agent.pt"
    torch.save(agent.state_dict(), str(model_path))
    envs.close()
    metrics_file.close()

    elapsed = time.time() - start_time
    sd_sha = state_dict_hash(agent.state_dict())

    print()
    if nan_detected:
        print("=== TRAINING FAILED — NaN detected in loss ===")
        sys.exit(2)
    print("=== TRAINING COMPLETE ===")
    print(f"interrupted:           {interrupted}")
    print(f"total_timesteps:       {global_step}")
    print(f"completed_updates:     ~{global_step // args.batch_size}/{num_updates}")
    print(f"wall_time:             {elapsed/60:.1f} min ({elapsed:.0f}s)")
    print(f"avg_sps:               {int(global_step / elapsed)}")
    print(f"episodes_completed:    {len(recent_returns)} (last 100 in buffer)")
    if recent_returns:
        print(f"ep_return (last 100):  min={min(recent_returns):.2f} "
              f"max={max(recent_returns):.2f} mean={np.mean(recent_returns):.2f}")
    print(f"final_loss:            {last_loss:.4f}")
    print(f"model_saved:           {model_path}")
    print(f"metrics:               {output_dir / 'metrics.jsonl'}")
    print(f"state_dict_sha256:     {sd_sha}")
    print()
    print(f"Next step: grid_scan_phase2.py --model-path {model_path}")


if __name__ == "__main__":
    main()
