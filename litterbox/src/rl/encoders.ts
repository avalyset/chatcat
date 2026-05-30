/**
 * Observation and action encoders for the RL env wrapper.
 *
 * - Observation: CatState -> Float32Array of dimension OBS_DIM.
 * - Action: (typeIndex, intensity) -> AgentAction. Duration is derived from
 *   the action type via a fixed table that matches src/agent/actions.ts so
 *   RL-driven actions are directly comparable to the rule-based path. The
 *   duration is therefore NOT a free RL parameter; this avoids exposing a
 *   knob the agent has no real semantic handle on for v0.
 *
 * The encoders are pure functions over the existing CatState/AgentAction
 * types — they do not import simcat/ethics state, and they introduce no
 * implicit RL-framework conventions. Plugging in gymnasium/SB3 later is a
 * wrapper task on top of this, not a refactor of this.
 */

import type {
  AgentAction,
  AgentActionType,
  BodyPosture,
  CatState,
  EarPosition,
  SimCatStateName,
  SimConfig,
  TailPosition,
  VocalizationType,
} from '../types';

// ─── Action space ──────────────────────────────────────────────────────

export const ACTION_TYPES: AgentActionType[] = [
  'idle',
  'slow_blink',
  'trill',
  'soft_purr',
  'side_glance',
  'pause',
];

// Mirrors src/agent/actions.ts. Keep in sync if those values change.
// `pause` is ethics-driven in the rule-based path (30s/60s); for an
// RL-initiated pause we use a 5s default — small enough to be a deliberate
// per-step beat, large enough to be distinct from idle.
export const ACTION_DURATION_MS: Record<AgentActionType, number> = {
  idle: 0,
  slow_blink: 2000,
  trill: 500,
  soft_purr: 3000,
  side_glance: 1000,
  pause: 5000,
};

export interface ActionSpace {
  numTypes: number;
  intensityRange: [number, number];
}

export const ACTION_SPACE: ActionSpace = {
  numTypes: ACTION_TYPES.length,
  intensityRange: [0, 1],
};

export function decodeAction(typeIdx: number, intensity: number): AgentAction {
  const wrapped = ((typeIdx % ACTION_TYPES.length) + ACTION_TYPES.length) % ACTION_TYPES.length;
  const type = ACTION_TYPES[wrapped];
  return {
    type,
    intensity: Math.max(0, Math.min(1, intensity)),
    duration_ms: ACTION_DURATION_MS[type],
  };
}

// ─── Observation encoder ───────────────────────────────────────────────

const STATE_INDEX: Record<SimCatStateName, number> = {
  ABSENT: 0,
  RESTING: 1,
  ALERT: 2,
  CURIOUS: 3,
  APPROACHING: 4,
  ENGAGING: 5,
  OVERSTIMULATED: 6,
  STRESSED: 7,
  RETREATING: 8,
  LEAVING: 9,
};

const EAR_INDEX: Record<EarPosition, number> = {
  forward: 0,
  neutral: 1,
  sideways: 2,
  flat: 3,
};

const TAIL_INDEX: Record<TailPosition, number> = {
  up: 0,
  neutral: 1,
  low: 2,
  puffed: 3,
  lashing: 4,
};

const POSTURE_INDEX: Record<BodyPosture, number> = {
  relaxed: 0,
  crouched: 1,
  arched: 2,
  frozen: 3,
};

const VOCAL_INDEX: Record<VocalizationType, number> = {
  purr: 0,
  trill: 1,
  meow: 2,
  growl: 3,
  hiss: 4,
  yowl: 5,
};

// Layout (37 floats total):
//   [0..9]   state one-hot (10 SimCat states)
//   [10..13] earPosition one-hot (4)
//   [14..18] tailPosition one-hot (5)
//   [19..22] bodyPosture one-hot (4)
//   [23]     position.x / arenaWidth        (in [0, 1] when on-arena)
//   [24]     position.y / arenaHeight
//   [25]     gazeDirection.x / arenaWidth   (clipped to [-1, 1])
//   [26]     gazeDirection.y / arenaHeight  (clipped to [-1, 1])
//   [27]     pupilDilation                  (in [0, 1])
//   [28]     cssScore / 7                   (Kessler & Turner 1997 scale 1..7)
//   [29..34] vocalizing.type one-hot (6), all zero if null
//   [35]     vocalizing.intensity           (0 if null)
//   [36]     episodeProgress = tick / maxTicks (in [0, 1])
//
// `archetype` and `tickCount` are NOT exposed: the agent should learn from
// observable behaviour, not from the trait label or the absolute clock.
export const OBS_DIM = 10 + 4 + 5 + 4 + 2 + 2 + 1 + 1 + 6 + 1 + 1; // 37

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

export function encodeObservation(
  catState: CatState,
  config: SimConfig,
  episodeProgress: number
): Float32Array {
  const obs = new Float32Array(OBS_DIM);
  let i = 0;

  obs[i + STATE_INDEX[catState.state]] = 1;
  i += 10;

  obs[i + EAR_INDEX[catState.earPosition]] = 1;
  i += 4;

  obs[i + TAIL_INDEX[catState.tailPosition]] = 1;
  i += 5;

  obs[i + POSTURE_INDEX[catState.bodyPosture]] = 1;
  i += 4;

  obs[i++] = catState.position.x / config.arenaWidth;
  obs[i++] = catState.position.y / config.arenaHeight;

  obs[i++] = clamp(catState.gazeDirection.x / config.arenaWidth, -1, 1);
  obs[i++] = clamp(catState.gazeDirection.y / config.arenaHeight, -1, 1);

  obs[i++] = clamp(catState.pupilDilation, 0, 1);

  obs[i++] = catState.cssScore / 7;

  if (catState.vocalizing) {
    obs[i + VOCAL_INDEX[catState.vocalizing.type]] = 1;
  }
  i += 6;
  obs[i++] = catState.vocalizing ? catState.vocalizing.intensity : 0;

  obs[i++] = clamp(episodeProgress, 0, 1);

  return obs;
}
