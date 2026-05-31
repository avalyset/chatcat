/**
 * Stdio NDJSON bridge over ChatcatEnv.
 *
 * Protocol — one JSON object per line, in both directions.
 *
 * Requests (Python → bridge, on stdin):
 *   {"type": "reset", "seed": <int>, "traits"?: [N, E, D, I, A]}
 *   {"type": "step",  "action": {"type": <string>, "intensity": <float>}}
 *   {"type": "rule_based_episode", "seed": <int>}        // ADR 0008
 *   {"type": "close"}
 *
 * Responses (bridge → Python, on stdout):
 *   reset:               {"obs": <float[37]>, "info": {"traits": [..], "habituation_rate": <float>, "seed": <int>, "simcat_seed": <int>}}
 *   step:                {"obs": <float[37]>, "reward": <float>, "done": <bool>, "info": {<StepInfo>}}
 *   rule_based_episode:  {"reward": <float>, "steps": <int>, "ended_reason": <string>}
 *   close:               {"ok": true}
 *   error:               {"error": <string>}
 *
 * Action durations are looked up from ACTION_DURATION_MS (mirrors
 * src/agent/actions.ts) so callers only need to send {type, intensity}.
 *
 * rule_based_episode runs the canonical rule-based ChatCatAgent
 * (src/agent/policy.ts) on the SAME (traits, simcat_seed) derived from
 * `seed` that the RL env would derive — so the returned reward is the
 * v0.1 reference policy's performance on the cat the RL agent is about
 * to face. Used by ADR 0008's baseline-normalised reward.
 *
 * This is a minimal, honest implementation. No batching, no shared memory,
 * no protocol optimisation — the probe is meant to measure what the
 * straightforward stdio path actually costs.
 */

import * as readline from 'node:readline';
import { createEnv } from '../rl/env';
import { ACTION_DURATION_MS, ACTION_TYPES } from '../rl/encoders';
import { createSimCat } from '../simcat/state-machine';
import { createAgent } from '../agent/policy';
import { createEthicsMonitor } from '../world/ethics-monitor';
import { createTickRunner } from '../world/tick-runner';
import { createPersonality } from '../simcat/personality';
import type {
  AgentAction,
  AgentActionType,
  Archetype,
  ArchetypeName,
  FelineFive,
  SimCatStateName,
} from '../types';

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

const REWARD_ALPHA = envAlpha !== undefined ? parseFloat(envAlpha) : 1.0;
const REWARD_BETA = envBeta !== undefined ? parseFloat(envBeta) : 0.5;
const REWARD_ENG_SCALE_MULT = envScaleMult !== undefined ? parseFloat(envScaleMult) : 1.0;
const REWARD_ENG_SCALE = REWARD_ENG_SCALE_MULT / (TICK_RATE * 60);

const env = hasRewardOverride
  ? createEnv({
      rewardParams: {
        alpha: REWARD_ALPHA,
        beta: REWARD_BETA,
        engagement_scale: REWARD_ENG_SCALE,
      },
    })
  : createEnv();

// ─── ADR 0008: rule-based baseline episode runner ─────────────────────
//
// Derives (traits, simcat_seed) from seed via the SAME mulberry32 flow
// as src/rl/env.ts createEnv().reset(), then runs the rule-based
// ChatCatAgent through the existing TickRunner for a full episode.
// Returns the total reward in adr0002_max_css form with the same
// (alpha, beta, engagement_scale) as the RL env's reward — so the
// baseline is computed in the SAME units as the agent's reward, and
// subtraction (RL_total − rule_based_total) is meaningful.
//
// Duplicates the seed-derivation logic and the per-step reward
// decomposition from src/rl/env.ts; documented as duplication for
// audit. Centralising would require exposing internal SimCat state
// from createEnv(), which conflates RL env and baseline runner.

const RULE_LABEL = 'CONTINUOUS_SAMPLE' as unknown as ArchetypeName;
const HAB_RATE = 0.010;
const MAX_TICKS = 18000;
const LEAVING_CONSECUTIVE_END = 100;

function mulberry32(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const ALL_STATES: SimCatStateName[] = [
  'ABSENT', 'RESTING', 'ALERT', 'CURIOUS', 'APPROACHING',
  'ENGAGING', 'OVERSTIMULATED', 'STRESSED', 'RETREATING', 'LEAVING',
];
const ENGAGEMENT_TYPES = new Set<AgentActionType>(['slow_blink', 'trill', 'soft_purr', 'side_glance']);
const HIGH_CSS_THRESHOLD = 4;

function runRuleBasedEpisode(envSeed: number) {
  const rng = mulberry32(envSeed);
  const traits = createPersonality(rng(), rng(), rng(), rng(), rng());
  const simcatSeed = Math.floor(rng() * 0x100000000) >>> 0;

  const archetype: Archetype = {
    name: RULE_LABEL,
    personality: traits,
    habituation_rate: HAB_RATE,
  };
  const config = { tickRate: TICK_RATE, simSpeed: 1, arenaWidth: 800, arenaHeight: 500 };
  const simcat = createSimCat(archetype, config, simcatSeed);
  const agent = createAgent();
  const ethicsMonitor = createEthicsMonitor(RULE_LABEL);

  // Inline the per-tick loop (NOT TickRunner) so we capture the agent's
  // ORIGINAL decision per tick, not the post-intervention modified one.
  // For policy-shape analysis we want what the rule-based policy CHOSE
  // for each state, not what the ethics monitor over-rode.

  let totalReward = 0;
  let maxCss = 0;
  let engagementTicks = 0;
  let optOuts = 0;
  let highCssTicks = 0;
  let prevState: SimCatStateName | null = null;
  let leavingConsec = 0;
  let endedReason = 'max_ticks';
  let tick = 0;

  const perStateVisits: Record<string, number> = {};
  const perStateTypeCounts: Record<string, Record<string, number>> = {};
  const perStateEngIntensitySum: Record<string, number> = {};
  const perStateEngIntensityCount: Record<string, number> = {};
  for (const s of ALL_STATES) {
    perStateVisits[s] = 0;
    perStateTypeCounts[s] = {};
    for (const at of ACTION_TYPES) perStateTypeCounts[s][at] = 0;
    perStateEngIntensitySum[s] = 0;
    perStateEngIntensityCount[s] = 0;
  }

  for (tick = 0; tick < MAX_TICKS; tick++) {
    const stateBefore = simcat.getState();
    // ADR 0009: same enforce()-before-tick contract as env.ts and
    // TickRunner. For the rule-based agent this is a no-op (policy.ts
    // caps already), but applying it here makes runRuleBasedEpisode
    // symmetric with every other action path in the system.
    const rawAction = agent.decide(stateBefore);
    const agentAction = ethicsMonitor.enforce(stateBefore, rawAction).enforced;
    const catState = simcat.tick(agentAction);
    const intervention = ethicsMonitor.onTick(catState, agentAction);

    // Per-step aggregates against catState (the state observed AFTER tick).
    // Use stateBefore for the per-state attribution of the action: the
    // rule-based policy chose `agentAction` GIVEN stateBefore.
    perStateVisits[stateBefore.state]++;
    perStateTypeCounts[stateBefore.state][agentAction.type]++;
    if (ENGAGEMENT_TYPES.has(agentAction.type)) {
      perStateEngIntensitySum[stateBefore.state] += agentAction.intensity;
      perStateEngIntensityCount[stateBefore.state]++;
    }

    const engagementTick = catState.state === 'ENGAGING' ? 1 : 0;
    engagementTicks += engagementTick;
    const inOptOutState = catState.state === 'LEAVING' || catState.state === 'RETREATING';
    const prevWasOptOut = prevState === 'LEAVING' || prevState === 'RETREATING';
    const newOptOut = inOptOutState && !prevWasOptOut;
    if (newOptOut) optOuts++;
    const deltaMaxCss = Math.max(0, catState.cssScore - maxCss);
    if (catState.cssScore > maxCss) maxCss = catState.cssScore;
    if (catState.cssScore >= HIGH_CSS_THRESHOLD) highCssTicks++;

    totalReward +=
      REWARD_ENG_SCALE * engagementTick
      - REWARD_ALPHA * deltaMaxCss
      - REWARD_BETA * (newOptOut ? 1 : 0);

    if (catState.state === 'LEAVING') {
      leavingConsec++;
      if (leavingConsec >= LEAVING_CONSECUTIVE_END) { tick++; endedReason = 'leaving'; break; }
    } else { leavingConsec = 0; }
    if (intervention.lockSession) { tick++; endedReason = 'lockout'; break; }
    prevState = catState.state;
  }

  return {
    reward: totalReward,
    steps: tick,
    ended_reason: endedReason,
    engagement_ticks: engagementTicks,
    max_css: maxCss,
    opt_outs: optOuts,
    high_css_ticks: highCssTicks,
    per_state_visits: perStateVisits,
    per_state_type_counts: perStateTypeCounts,
    per_state_eng_intensity_sum: perStateEngIntensitySum,
    per_state_eng_intensity_count: perStateEngIntensityCount,
  };
}

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
    } else if (msg.type === 'rule_based_episode') {
      const result = runRuleBasedEpisode(msg.seed);
      write(result);
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
