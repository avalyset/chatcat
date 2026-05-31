/**
 * ChatcatEnv — gym-style env wrapper around SimCat + EthicsMonitor.
 *
 * Sits DIRECTLY on top of SimCat and EthicsMonitor; does NOT go through
 * TickRunner, which remains the reference path for the rule-based
 * ChatCatAgent. Splitting the RL path off here lets us drive simcat with
 * externally-supplied actions (RL-style push) without touching TickRunner's
 * agent.decide()-style pull contract.
 *
 * Contract:
 *   const env = createEnv({ ... });
 *   const { obs, info } = env.reset(seed);
 *   const { obs, reward, done, info } = env.step(action);
 *
 * Episode termination matches batch.ts where applicable:
 *   - intervention.lockSession                          -> 'lockout'
 *   - SimCat in LEAVING for >= 100 consecutive ticks    -> 'leaving'
 *   - tick >= maxTicks                                  -> 'max_ticks'
 *
 * `cooldown_exhausted` from the rule-based batch path is intentionally NOT
 * mirrored — that termination is specific to the rule-based agent's
 * internal cooldown timer (policy.ts), which an RL agent does not have.
 *
 * Per-step info exposes the RAW reward components (engagement tick, CSS,
 * cumulative opt-outs, max-CSS-so-far) UNCOMBINED, alongside the aggregated
 * reward — so callers can re-derive any reward function without re-running
 * the simulation.
 */

import type {
  AgentAction,
  Archetype,
  ArchetypeName,
  FelineFive,
  SimCatStateName,
  SimConfig,
} from '../types';
import { createSimCat, type SimCat } from '../simcat/state-machine';
import { createEthicsMonitor, type EthicsMonitor } from '../world/ethics-monitor';
import { createPersonality } from '../simcat/personality';
import {
  ACTION_SPACE,
  encodeObservation,
  OBS_DIM,
  type ActionSpace,
} from './encoders';
import {
  adr0002Reward,
  type RewardComponents,
  type RewardFn,
  type RewardParams,
} from './reward';

// Synthetic label for env-driven sessions. Same convention as batch.ts
// continuous mode: the label flows only into log strings, never into a
// preset-keyed lookup.
const RL_ENV_LABEL = 'CONTINUOUS_SAMPLE' as unknown as ArchetypeName;

// Match batch.ts continuous-mode termination: LEAVING sustained for 10s at 10 Hz.
const LEAVING_CONSECUTIVE_END = 100;

// Local Mulberry32 — same family as batch.ts and state-machine. Pure,
// deterministic. Replicated here to keep the RL path's PRNG choice
// independent of batch.ts internals.
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

function sampleTraits(rng: () => number): FelineFive {
  return createPersonality(rng(), rng(), rng(), rng(), rng());
}

export interface EnvOptions {
  config?: SimConfig;
  rewardFn?: RewardFn;
  rewardParams?: RewardParams;
  maxTicks?: number;
  /**
   * Habituation rate for sampled sessions. ADR 0003 documents that values
   * are placeholders in [0.005, 0.015]; 0.010 is the midpoint used by the
   * ADR 0006 continuous run, kept here as the default so RL training is
   * comparable to that baseline.
   */
  habituationRate?: number;
}

export interface ResetInfo {
  traits: FelineFive;
  habituation_rate: number;
  seed: number;
  simcat_seed: number;
}

export interface StepInfo {
  // — RAW components (the four the user asked for, uncombined) —
  per_step_engagement: number;
  per_step_css: number;
  cumulative_opt_outs: number;
  max_css_so_far: number;
  // — derived helpers consumed by reward.ts —
  new_opt_out: boolean;
  delta_max_css: number;
  // — bookkeeping —
  tick: number;
  episode_return: number;
  ethics_intervention: {
    force_pause: boolean;
    lock_session: boolean;
    daily_cap: boolean;
  };
  // — ADR 0009: per-tick record of whether the agent's action was capped
  // by the ethics-monitor's enforce() step. cap_applied=false means the
  // action was a pass-through; original_intensity equals enforced_intensity.
  ethics_enforcement: {
    cap_applied: boolean;
    original_intensity: number;
    enforced_intensity: number;
    original_action_type: string;
    enforced_action_type: string;
    rule: string;
  };
  ended_reason: 'leaving' | 'max_ticks' | 'lockout' | null;
}

export interface StepResult {
  obs: Float32Array;
  reward: number;
  done: boolean;
  info: StepInfo;
}

export interface ChatcatEnv {
  reset(seed: number, traits?: FelineFive): { obs: Float32Array; info: ResetInfo };
  step(action: AgentAction): StepResult;
  readonly observationDim: number;
  readonly actionSpace: ActionSpace;
  readonly maxTicks: number;
  readonly rewardParams: RewardParams;
  readonly config: SimConfig;
}

const DEFAULT_CONFIG: SimConfig = {
  tickRate: 10,
  simSpeed: 1,
  arenaWidth: 800,
  arenaHeight: 500,
};

export function createEnv(opts: EnvOptions = {}): ChatcatEnv {
  const config = opts.config ?? DEFAULT_CONFIG;
  const maxTicks = opts.maxTicks ?? 18000;
  const habRate = opts.habituationRate ?? 0.010;
  const rewardFn = opts.rewardFn ?? adr0002Reward;
  const rewardParams: RewardParams = opts.rewardParams ?? {
    alpha: 1.0,
    beta: 0.5,
    engagement_scale: 1 / (config.tickRate * 60),
  };

  let simcat: SimCat | null = null;
  let ethicsMonitor: EthicsMonitor | null = null;
  let tick = 0;
  let prevState: SimCatStateName | null = null;
  let maxCss = 0;
  let cumulativeOptOuts = 0;
  let episodeReturn = 0;
  let leavingConsecutive = 0;
  let terminated = false;

  function reset(seed: number, traits?: FelineFive): { obs: Float32Array; info: ResetInfo } {
    const rng = mulberry32(seed);
    const traitsResolved = traits ?? sampleTraits(rng);
    // Always consume one extra draw so that the seed -> simcat-seed mapping
    // is independent of whether `traits` was provided. This keeps the
    // reset() contract stable: same seed -> same simcat behaviour, modulo
    // the explicit traits override.
    const simcatSeed = Math.floor(rng() * 0x100000000) >>> 0;

    const archetype: Archetype = {
      name: RL_ENV_LABEL,
      personality: traitsResolved,
      habituation_rate: habRate,
    };

    simcat = createSimCat(archetype, config, simcatSeed);
    ethicsMonitor = createEthicsMonitor(RL_ENV_LABEL);
    tick = 0;
    prevState = null;
    maxCss = 0;
    cumulativeOptOuts = 0;
    episodeReturn = 0;
    leavingConsecutive = 0;
    terminated = false;

    const initialState = simcat.getState();
    const obs = encodeObservation(initialState, config, 0);
    return {
      obs,
      info: {
        traits: traitsResolved,
        habituation_rate: habRate,
        seed,
        simcat_seed: simcatSeed,
      },
    };
  }

  function step(action: AgentAction): StepResult {
    if (!simcat || !ethicsMonitor) {
      throw new Error('ChatcatEnv.step() called before reset().');
    }
    if (terminated) {
      throw new Error('ChatcatEnv.step() called after episode terminated. Call reset().');
    }

    // ADR 0009: enforce hard welfare constraints BEFORE the action reaches
    // simcat. The enforced action is what gets ticked AND logged; the
    // original is captured in capInfo for empirical traceability of
    // attempted overshoots (RL agents can be measured for how often their
    // raw policy outputs would have violated welfare invariants).
    const stateBeforeTick = simcat.getState();
    const { enforced, capInfo } = ethicsMonitor.enforce(stateBeforeTick, action);

    const catState = simcat.tick(enforced);
    const intervention = ethicsMonitor.onTick(catState, enforced);

    // Per-step engagement: 1 iff this tick was spent ENGAGING.
    const engagementTick = catState.state === 'ENGAGING' ? 1 : 0;

    // Per-step CSS.
    const cssNow = catState.cssScore;

    // Opt-out: transition INTO LEAVING or RETREATING from any other state.
    // Matches the definition the ethics-monitor uses internally
    // (world/ethics-monitor.ts: `previousState !== 'LEAVING' && previousState !== 'RETREATING'`),
    // so this counter agrees with ethics-monitor's optOutEvents up to
    // session-boundary edge cases.
    const inOptOutState = catState.state === 'LEAVING' || catState.state === 'RETREATING';
    const prevWasOptOut = prevState === 'LEAVING' || prevState === 'RETREATING';
    const newOptOut = inOptOutState && !prevWasOptOut;
    if (newOptOut) cumulativeOptOuts++;

    // Max-CSS tracking + monotone delta.
    const deltaMaxCss = Math.max(0, cssNow - maxCss);
    if (cssNow > maxCss) maxCss = cssNow;

    const components: RewardComponents = {
      engagement_tick: engagementTick,
      css_now: cssNow,
      new_opt_out: newOptOut,
      delta_max_css: deltaMaxCss,
    };
    const reward = rewardFn(components, rewardParams);
    episodeReturn += reward;

    // Termination tracking.
    if (catState.state === 'LEAVING') {
      leavingConsecutive++;
    } else {
      leavingConsecutive = 0;
    }

    tick++;

    let endedReason: StepInfo['ended_reason'] = null;
    let done = false;
    if (intervention.lockSession) {
      done = true;
      endedReason = 'lockout';
    } else if (leavingConsecutive >= LEAVING_CONSECUTIVE_END) {
      done = true;
      endedReason = 'leaving';
    } else if (tick >= maxTicks) {
      done = true;
      endedReason = 'max_ticks';
    }
    terminated = done;

    prevState = catState.state;

    const episodeProgress = Math.min(1, tick / maxTicks);
    const obs = encodeObservation(catState, config, episodeProgress);

    return {
      obs,
      reward,
      done,
      info: {
        per_step_engagement: engagementTick,
        per_step_css: cssNow,
        cumulative_opt_outs: cumulativeOptOuts,
        max_css_so_far: maxCss,
        new_opt_out: newOptOut,
        delta_max_css: deltaMaxCss,
        tick,
        episode_return: episodeReturn,
        ethics_intervention: {
          force_pause: intervention.forcePause,
          lock_session: intervention.lockSession,
          daily_cap: intervention.dailyCapReached,
        },
        ethics_enforcement: {
          cap_applied: capInfo.cap_applied,
          original_intensity: capInfo.original_intensity,
          enforced_intensity: capInfo.enforced_intensity,
          original_action_type: capInfo.original_action_type,
          enforced_action_type: capInfo.enforced_action_type,
          rule: capInfo.rule,
        },
        ended_reason: endedReason,
      },
    };
  }

  return {
    reset,
    step,
    observationDim: OBS_DIM,
    actionSpace: ACTION_SPACE,
    maxTicks,
    rewardParams,
    config,
  };
}
