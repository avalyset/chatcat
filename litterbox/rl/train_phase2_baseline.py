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
Phase 2, ADR 0008 — PPO with baseline-normalised reward.

Trains exactly as train_phase2.py except the env is
BaselineNormalizedChatcatEnv: each episode's terminal reward is
adjusted so the episode sum equals (R_agent − R_baseline_for_seed),
where R_baseline_for_seed is the v0.1 rule-based ChatCatAgent's
total reward on the same (traits, simcat_seed).

All other hyperparameters and the Agent class are imported from
train_phase2.py — algorithm unchanged.

ADR 0008 pre-registered success criteria are checked by
grid_scan_phase2_baseline.py against this run's metrics.jsonl and
saved agent.pt.
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
import torch.optim as optim

import gymnasium as gym  # noqa: E402
from env_continuous_baseline import BaselineNormalizedChatcatEnv  # noqa: E402
from train_phase2 import (  # noqa: E402
    Agent,
    CROSSOVER_ALPHA,
    CROSSOVER_BETA,
    CROSSOVER_ENG_SCALE_MULT,
    state_dict_hash,
)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--exp-name", type=str, default="phase2_baseline_norm")
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
    args = p.parse_args()
    args.batch_size = args.num_envs * args.num_steps
    args.minibatch_size = args.batch_size // args.num_minibatches
    return args


def make_env(seed):
    def thunk():
        env = BaselineNormalizedChatcatEnv(
            reward_alpha=CROSSOVER_ALPHA,
            reward_beta=CROSSOVER_BETA,
            reward_engagement_scale_mult=CROSSOVER_ENG_SCALE_MULT,
        )
        env.action_space.seed(seed)
        return env
    return thunk


def main():
    args = parse_args()
    run_name = f"{args.exp_name}__seed{args.seed}__{int(time.time())}"
    output_dir = Path(args.output_dir) / run_name
    output_dir.mkdir(parents=True, exist_ok=True)

    config = {
        **vars(args),
        "reward": {
            "form": "adr0002_max_css",
            "alpha": CROSSOVER_ALPHA,
            "beta": CROSSOVER_BETA,
            "engagement_scale_mult": CROSSOVER_ENG_SCALE_MULT,
            "baseline_normalization": True,
            "baseline_source": "rule-based ChatCatAgent (src/agent/policy.ts)",
            "adr_reference": "ADR 0008 (crossover regime, baseline-normalised)",
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

    agent = Agent(envs, frozen_logstd=None).to(device)
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
    recent_returns: list[float] = []
    nan_detected = False
    last_loss = float("nan")
    interrupted = False

    def handle_interrupt(_s, _f):
        nonlocal interrupted
        interrupted = True
        print("\n[interrupted — saving current model and exiting cleanly]")
    signal.signal(signal.SIGINT, handle_interrupt)

    print(f"phase 2 (ADR 0008) baseline-normalised PPO starting: "
          f"{num_updates} updates × {args.batch_size} batch = "
          f"{args.total_timesteps} total env steps")
    print(f"output: {output_dir}")
    print(f"reward: adr0002_max_css α={CROSSOVER_ALPHA} β={CROSSOVER_BETA} "
          f"scale_mult={CROSSOVER_ENG_SCALE_MULT} (baseline-normalised at terminal step)")
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

            next_obs_np, reward, terminations, truncations, _ = envs.step(action.cpu().numpy())
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
                torch.nn.utils.clip_grad_norm_(agent.parameters(), args.max_grad_norm)
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
    print("=== TRAINING COMPLETE (ADR 0008 baseline-normalised) ===")
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
    print(f"Next step: grid_scan_phase2_baseline.py --model-path {model_path}")


if __name__ == "__main__":
    main()
