/**
 * Stdio NDJSON bridge over ChatcatEnv.
 *
 * Protocol — one JSON object per line, in both directions.
 *
 * Requests (Python → bridge, on stdin):
 *   {"type": "reset", "seed": <int>, "traits"?: [N, E, D, I, A]}
 *   {"type": "step",  "action": {"type": <string>, "intensity": <float>}}
 *   {"type": "close"}
 *
 * Responses (bridge → Python, on stdout):
 *   reset:  {"obs": <float[37]>, "info": {"traits": [..], "habituation_rate": <float>, "seed": <int>, "simcat_seed": <int>}}
 *   step:   {"obs": <float[37]>, "reward": <float>, "done": <bool>, "info": {<StepInfo>}}
 *   close:  {"ok": true}
 *   error:  {"error": <string>}
 *
 * Action durations are looked up from ACTION_DURATION_MS (mirrors
 * src/agent/actions.ts) so callers only need to send {type, intensity}.
 *
 * This is a minimal, honest implementation. No batching, no shared memory,
 * no protocol optimisation — the probe is meant to measure what the
 * straightforward stdio path actually costs.
 */

import * as readline from 'node:readline';
import { createEnv } from '../rl/env';
import { ACTION_DURATION_MS, ACTION_TYPES } from '../rl/encoders';
import type { AgentAction, AgentActionType, FelineFive } from '../types';

// Reward-parameter overrides from the spawning process.
//
// If any of CHATCAT_ALPHA / CHATCAT_BETA / CHATCAT_ENG_SCALE_MULT is set,
// they override the env.ts default rewardParams. Defaults unchanged when
// all three are unset — so the fase 1/1b smoke-test hashes still
// reproduce bit-identically.
//
// CHATCAT_ENG_SCALE_MULT is a multiplier on the canonical scale
// 1/(tickRate * 60); ADR 0007's crossover regime sets it to 5.0.
const envAlpha = process.env.CHATCAT_ALPHA;
const envBeta = process.env.CHATCAT_BETA;
const envScaleMult = process.env.CHATCAT_ENG_SCALE_MULT;
const hasRewardOverride =
  envAlpha !== undefined || envBeta !== undefined || envScaleMult !== undefined;

const TICK_RATE = 10; // matches DEFAULT_CONFIG in src/rl/env.ts

const env = hasRewardOverride
  ? createEnv({
      rewardParams: {
        alpha: envAlpha !== undefined ? parseFloat(envAlpha) : 1.0,
        beta: envBeta !== undefined ? parseFloat(envBeta) : 0.5,
        engagement_scale:
          (envScaleMult !== undefined ? parseFloat(envScaleMult) : 1.0)
          / (TICK_RATE * 60),
      },
    })
  : createEnv();

function write(obj: unknown): void {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function obsArray(obs: Float32Array): number[] {
  // Float32 values widened to float64 for JSON; JSON's shortest-roundtrip
  // decimal serialisation preserves them exactly.
  const out = new Array(obs.length);
  for (let i = 0; i < obs.length; i++) out[i] = obs[i];
  return out;
}

function buildAction(raw: { type: string; intensity: number }): AgentAction {
  if (!ACTION_TYPES.includes(raw.type as AgentActionType)) {
    throw new Error(`unknown action type: ${raw.type}`);
  }
  const type = raw.type as AgentActionType;
  return {
    type,
    intensity: Math.max(0, Math.min(1, raw.intensity)),
    duration_ms: ACTION_DURATION_MS[type],
  };
}

const rl = readline.createInterface({ input: process.stdin });

rl.on('line', (line: string) => {
  try {
    const msg = JSON.parse(line);
    if (msg.type === 'reset') {
      const traits: FelineFive | undefined = msg.traits ? {
        neuroticism:   msg.traits[0],
        extraversion:  msg.traits[1],
        dominance:     msg.traits[2],
        impulsiveness: msg.traits[3],
        agreeableness: msg.traits[4],
      } : undefined;
      const { obs, info } = env.reset(msg.seed, traits);
      write({
        obs: obsArray(obs),
        info: {
          traits: [
            info.traits.neuroticism,
            info.traits.extraversion,
            info.traits.dominance,
            info.traits.impulsiveness,
            info.traits.agreeableness,
          ],
          habituation_rate: info.habituation_rate,
          seed: info.seed,
          simcat_seed: info.simcat_seed,
        },
      });
    } else if (msg.type === 'step') {
      const action = buildAction(msg.action);
      const result = env.step(action);
      write({
        obs: obsArray(result.obs),
        reward: result.reward,
        done: result.done,
        info: result.info,
      });
    } else if (msg.type === 'close') {
      write({ ok: true });
      rl.close();
      process.exit(0);
    } else {
      write({ error: `unknown message type: ${msg.type}` });
    }
  } catch (e) {
    write({ error: String(e) });
  }
});
