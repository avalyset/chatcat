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
CleanRL PPO smoke test for ChatcatGymContinuousEnv (Box(7,) action).

Adapted from CleanRL's reference single-file ppo_continuous_action.py
(https://github.com/vwxyzjn/cleanrl). The algorithm is unchanged — only
env construction, the run-name format, and output paths differ. This is
a separate file from ppo_chatcat.py (Discrete smoke), not a modification
of it, per the "no algorithm modification" rule.

Purpose: prove the continuous training path works end-to-end before fase
2. Same checklist as fase 1:
  - gradients computed without NaN
  - process runs to completion without crash or hang
  - bridge subprocess survives a full run
  - model is saved
  - same --seed gives bit-identical results
    (trajectory_sha256 + state_dict_sha256)

NOT training. --total-timesteps default 10000 = ~78 updates with
num_steps=128. Reward shaping owned by the TS env (ADR 0007 crossover:
adr0002_max_css, α=1.0, β=0.5, engagement_scale=5/(10*60)).

Usage:
  uv run rl/ppo_chatcat_continuous.py [--seed 1] [--total-timesteps 10000]
"""

import argparse
import hashlib
import json
import random
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


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--exp-name", type=str, default="ppo_chatcat_continuous_smoke")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--total-timesteps", type=int, default=10_000)
    p.add_argument("--learning-rate", type=float, default=3e-4)
    p.add_argument("--num-envs", type=int, default=1)
    p.add_argument("--num-steps", type=int, default=128)
    p.add_argument("--anneal-lr", action="store_true", default=True)
    p.add_argument("--gamma", type=float, default=0.99)
    p.add_argument("--gae-lambda", type=float, default=0.95)
    p.add_argument("--num-minibatches", type=int, default=4)
    p.add_argument("--update-epochs", type=int, default=4)
    p.add_argument("--norm-adv", action="store_true", default=True)
    p.add_argument("--clip-coef", type=float, default=0.2)
    p.add_argument("--clip-vloss", action="store_true", default=True)
    p.add_argument("--ent-coef", type=float, default=0.0)
    p.add_argument("--vf-coef", type=float, default=0.5)
    p.add_argument("--max-grad-norm", type=float, default=0.5)
    p.add_argument("--output-dir", type=str, default="/tmp/chatcat-rl-runs",
                   help="parent dir for run artefacts (kept out of repo)")
    args = p.parse_args()
    args.batch_size = args.num_envs * args.num_steps
    args.minibatch_size = args.batch_size // args.num_minibatches
    return args


def make_env(seed):
    def thunk():
        env = ChatcatGymContinuousEnv()
        env.action_space.seed(seed)
        return env
    return thunk


def layer_init(layer, std=np.sqrt(2), bias_const=0.0):
    torch.nn.init.orthogonal_(layer.weight, std)
    torch.nn.init.constant_(layer.bias, bias_const)
    return layer


class Agent(nn.Module):
    def __init__(self, envs):
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
        self.actor_logstd = nn.Parameter(torch.zeros(1, action_dim))

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
    traj_path = output_dir / "trajectory.jsonl"
    traj_file = open(traj_path, "w")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.use_deterministic_algorithms(True, warn_only=True)

    device = torch.device("cpu")

    envs = gym.vector.SyncVectorEnv(
        [make_env(args.seed + i) for i in range(args.num_envs)]
    )
    assert isinstance(envs.single_action_space, gym.spaces.Box), (
        f"expected Box action space, got {type(envs.single_action_space)}"
    )

    agent = Agent(envs).to(device)
    optimizer = optim.Adam(agent.parameters(), lr=args.learning_rate, eps=1e-5)

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
    episodes_done = []

    nan_detected = False
    last_loss = float("nan")

    for update in range(1, num_updates + 1):
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
                traj_file.write(json.dumps({
                    "global_step": global_step - args.num_envs + env_idx + 1,
                    "env": env_idx,
                    # Action vector to 8 decimal places — enough for SHA-256
                    # determinism comparison without bloating the file.
                    "action": [round(float(v), 8) for v in action[env_idx].tolist()],
                    "reward": float(reward[env_idx]),
                    "done": bool(next_done_np[env_idx]),
                }) + "\n")
                if next_done_np[env_idx]:
                    episodes_done.append({
                        "global_step": global_step,
                        "env": env_idx,
                        "return": float(cur_return[env_idx]),
                        "length": int(cur_length[env_idx]),
                    })
                    cur_return[env_idx] = 0
                    cur_length[env_idx] = 0

            next_obs = torch.Tensor(next_obs_np).to(device)
            next_done = torch.Tensor(next_done_np.astype(np.float32)).to(device)

        # GAE
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
                delta = (
                    rewards[t]
                    + args.gamma * nextvalues * nextnonterminal
                    - values[t]
                )
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
                    mb_advantages = (
                        (mb_advantages - mb_advantages.mean())
                        / (mb_advantages.std() + 1e-8)
                    )

                pg_loss1 = -mb_advantages * ratio
                pg_loss2 = -mb_advantages * torch.clamp(
                    ratio, 1 - args.clip_coef, 1 + args.clip_coef
                )
                pg_loss = torch.max(pg_loss1, pg_loss2).mean()

                newvalue = newvalue.view(-1)
                if args.clip_vloss:
                    v_loss_unclipped = (newvalue - b_returns[mb_inds]) ** 2
                    v_clipped = b_values[mb_inds] + torch.clamp(
                        newvalue - b_values[mb_inds],
                        -args.clip_coef,
                        args.clip_coef,
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
        sps = int(global_step / max(1e-6, time.time() - start_time))
        print(
            f"update={update}/{num_updates}  global_step={global_step}  "
            f"sps={sps}  loss={last_loss:.4f}  "
            f"episodes_done={len(episodes_done)}"
        )

    model_path = output_dir / "agent.pt"
    torch.save(agent.state_dict(), str(model_path))

    envs.close()
    traj_file.close()

    h = hashlib.sha256()
    with open(traj_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    traj_sha = h.hexdigest()
    sd_sha = state_dict_hash(agent.state_dict())

    elapsed = time.time() - start_time
    print()
    if nan_detected:
        print("=== SMOKE TEST FAILED — NaN detected in loss ===")
        sys.exit(2)
    print("=== SMOKE TEST CLEAN ===")
    print(f"total_timesteps:      {global_step}")
    print(f"num_updates:          {num_updates}")
    print(f"wall_time:            {elapsed:.1f}s")
    print(f"avg_sps:              {int(global_step / elapsed)}")
    print(f"episodes_completed:   {len(episodes_done)}")
    if episodes_done:
        returns = [e['return'] for e in episodes_done]
        lengths = [e['length'] for e in episodes_done]
        print(f"episode_return:       min={min(returns):.2f} max={max(returns):.2f} mean={np.mean(returns):.2f}")
        print(f"episode_length:       min={min(lengths)} max={max(lengths)} mean={int(np.mean(lengths))}")
    print(f"final_loss:           {last_loss:.4f}")
    print(f"model_saved:          {model_path}")
    print(f"trajectory_jsonl:     {traj_path}")
    print(f"trajectory_sha256:    {traj_sha}")
    print(f"state_dict_sha256:    {sd_sha}")


if __name__ == "__main__":
    main()
