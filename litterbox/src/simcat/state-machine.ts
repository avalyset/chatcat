/**
 * SimCat state machine
 *
 * Markov-like transitions with personality-weighted probabilities.
 * Tick rate: 10 Hz (configurable via SimConfig).
 *
 * Transition rules (cite Kappel et al. 2024 ethogram categories):
 * - High Neuroticism → faster transition into STRESSED, slower recovery
 * - High Impulsiveness → ENGAGING ↔ OVERSTIMULATED faster oscillation
 * - Low Agreeableness → faster LEAVING from any state if agent intensity high
 * - High Extraversion → ALERT → APPROACHING more likely
 * - High Dominance → ENGAGING longer, less RETREATING
 *
 * Habituation: exponential decay of engagement probability over session minutes.
 * Source: Ellis et al. 2008; Hirskyj-Douglas & Webber on novelty effect.
 */

import type {
  Archetype,
  CatState,
  SimCatStateName,
  SimConfig,
  AgentAction,
  Position,
} from '../types';
import { approachTendency, stressRecoveryRate, stateChangeFrequency } from './personality';
import { computeCssScore, cssToIndicators } from './stress-score';
import { rollVocalization } from './vocalizations';

// Seeded PRNG (xoshiro128** variant) for reproducibility
function createRng(seed: number = Date.now()) {
  let s = seed | 0;
  return () => {
    s = (s + 0x6D2B79F5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface SimCat {
  tick(agentAction: AgentAction | null): CatState;
  getState(): CatState;
  reset(): void;
}

// Minimum dwell time per state (in ticks at 10 Hz).
// Transitions are only evaluated after the cat has been in the current state
// for at least this many ticks. Prevents sub-second "flicker" between states.
//
// Calibration basis (ADR 0004):
// - No published transition-rate data exists for domestic cats at this granularity
// - Accelerometer floor: shortest recorded behaviour (jumping) = 0.89s (Smit et al. 2023)
// - Values below are conservative estimates from ethological inference, not direct literature
// - These are constants, not config — changing them requires a calibration decision
const MIN_DWELL_TICKS: Record<SimCatStateName, number> = {
  ABSENT:          50,  // 5.0 s — cat is genuinely away, not flickering
  RESTING:        300,  // 30.0 s — rest bouts avg ~65 s (Morrison et al. 2024); 30 is conservative
  ALERT:           20,  // 2.0 s — orienting response persists for seconds
  CURIOUS:         30,  // 3.0 s — investigation takes sustained attention
  APPROACHING:     20,  // 2.0 s — physical movement toward agent
  ENGAGING:        50,  // 5.0 s — play/interaction bouts last seconds to minutes
  OVERSTIMULATED:  15,  // 1.5 s — transient by definition, but still visible
  STRESSED:        20,  // 2.0 s — distress persists, not instantaneous
  RETREATING:      20,  // 2.0 s — withdrawal is a deliberate, observable act
  LEAVING:         30,  // 3.0 s — walking away from the arena takes time
};

// Transition table: from-state → array of [to-state, base-probability]
type TransitionTable = Record<SimCatStateName, [SimCatStateName, number][]>;

const BASE_TRANSITIONS: TransitionTable = {
  ABSENT: [
    ['ABSENT', 0.92],
    ['RESTING', 0.05],
    ['ALERT', 0.03],
  ],
  RESTING: [
    ['RESTING', 0.85],
    ['ALERT', 0.08],
    ['ABSENT', 0.04],
    ['LEAVING', 0.03],
  ],
  ALERT: [
    ['ALERT', 0.60],
    ['CURIOUS', 0.15],
    ['APPROACHING', 0.10],
    ['RESTING', 0.08],
    ['RETREATING', 0.04],
    ['ABSENT', 0.03],
  ],
  CURIOUS: [
    ['CURIOUS', 0.50],
    ['APPROACHING', 0.20],
    ['ALERT', 0.15],
    ['RESTING', 0.08],
    ['RETREATING', 0.05],
    ['LEAVING', 0.02],
  ],
  APPROACHING: [
    ['APPROACHING', 0.40],
    ['ENGAGING', 0.30],
    ['CURIOUS', 0.15],
    ['ALERT', 0.08],
    ['RETREATING', 0.05],
    ['LEAVING', 0.02],
  ],
  ENGAGING: [
    ['ENGAGING', 0.55],
    ['OVERSTIMULATED', 0.15],
    ['CURIOUS', 0.10],
    ['APPROACHING', 0.08],
    ['RETREATING', 0.07],
    ['LEAVING', 0.05],
  ],
  OVERSTIMULATED: [
    ['OVERSTIMULATED', 0.30],
    ['STRESSED', 0.25],
    ['RETREATING', 0.20],
    ['ENGAGING', 0.10],
    ['LEAVING', 0.10],
    ['ALERT', 0.05],
  ],
  STRESSED: [
    ['STRESSED', 0.35],
    ['RETREATING', 0.30],
    ['LEAVING', 0.20],
    ['OVERSTIMULATED', 0.10],
    ['ALERT', 0.05],
  ],
  RETREATING: [
    ['RETREATING', 0.30],
    ['LEAVING', 0.35],
    ['RESTING', 0.15],
    ['ALERT', 0.10],
    ['ABSENT', 0.10],
  ],
  LEAVING: [
    ['LEAVING', 0.20],
    ['ABSENT', 0.70],
    ['RESTING', 0.10],
  ],
};

function applyPersonalityModifiers(
  transitions: [SimCatStateName, number][],
  archetype: Archetype,
  currentState: SimCatStateName,
  agentIntensity: number,
  habituationFactor: number // 0..1 where 1 = fresh, 0 = fully habituated
): [SimCatStateName, number][] {
  const p = archetype.personality;
  const approach = approachTendency(p);
  const changeFreq = stateChangeFrequency(p);

  const modified = transitions.map(([state, prob]): [SimCatStateName, number] => {
    let mod = prob;

    // High Neuroticism → faster STRESSED transitions
    if (state === 'STRESSED' || state === 'OVERSTIMULATED') {
      mod *= 1 + p.neuroticism * 0.8;
    }

    // High Extraversion → more likely to approach/engage
    if (state === 'APPROACHING' || state === 'ENGAGING' || state === 'CURIOUS') {
      mod *= 1 + p.extraversion * 0.6 * habituationFactor;
    }

    // High Impulsiveness → faster state changes (reduce self-transition)
    if (state === currentState) {
      mod *= 1 - p.impulsiveness * 0.3 * changeFreq;
    }

    // Low Agreeableness + high agent intensity → faster LEAVING
    if ((state === 'LEAVING' || state === 'RETREATING') && agentIntensity > 0.3) {
      mod *= 1 + (1 - p.agreeableness) * agentIntensity * 0.5;
    }

    // High Dominance → more ENGAGING, less RETREATING
    if (state === 'ENGAGING') {
      mod *= 1 + p.dominance * 0.4;
    }
    if (state === 'RETREATING' || state === 'LEAVING') {
      mod *= 1 - p.dominance * 0.2;
    }

    // Approach tendency general modifier
    if (state === 'APPROACHING' || state === 'ENGAGING') {
      mod *= 1 + approach * 0.3 * habituationFactor;
    }

    return [state, Math.max(0.001, mod)];
  });

  // Normalise
  const total = modified.reduce((sum, [, p]) => sum + p, 0);
  return modified.map(([s, p]) => [s, p / total]);
}

function sampleTransition(transitions: [SimCatStateName, number][], roll: number): SimCatStateName {
  let cumulative = 0;
  for (const [state, prob] of transitions) {
    cumulative += prob;
    if (roll <= cumulative) return state;
  }
  return transitions[transitions.length - 1][0];
}

// Position behaviour per state
function updatePosition(
  pos: Position,
  state: SimCatStateName,
  agentPos: Position,
  rng: () => number,
  config: SimConfig
): Position {
  const speed = 2;
  let { x, y } = pos;

  switch (state) {
    case 'ABSENT':
      // Off-screen
      return { x: -50, y: config.arenaHeight / 2 };
    case 'APPROACHING': {
      // Move toward agent
      const dx = agentPos.x - x;
      const dy = agentPos.y - y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist > 5) {
        x += (dx / dist) * speed * (0.5 + rng() * 0.5);
        y += (dy / dist) * speed * (0.5 + rng() * 0.5);
      }
      break;
    }
    case 'RETREATING':
    case 'LEAVING': {
      // Move away from agent toward left edge
      x -= speed * (0.5 + rng() * 1.5);
      y += (rng() - 0.5) * speed;
      break;
    }
    case 'ENGAGING': {
      // Wander near agent
      x += (rng() - 0.5) * speed * 0.5;
      y += (rng() - 0.5) * speed * 0.5;
      break;
    }
    default: {
      // Random wander
      x += (rng() - 0.5) * speed;
      y += (rng() - 0.5) * speed;
      break;
    }
  }

  // Clamp to arena
  x = Math.max(10, Math.min(config.arenaWidth - 10, x));
  y = Math.max(10, Math.min(config.arenaHeight - 10, y));
  return { x, y };
}

export function createSimCat(archetype: Archetype, config: SimConfig, seed?: number): SimCat {
  const rng = createRng(seed);
  const agentPos: Position = { x: config.arenaWidth - 80, y: config.arenaHeight / 2 };

  let currentState: SimCatStateName = 'ABSENT';
  let position: Position = { x: -50, y: config.arenaHeight / 2 };
  let tickCount = 0;
  let sessionStartTick = 0;
  let ticksInCurrentState = 0;

  function habituationFactor(): number {
    // Exponential decay over sim-minutes
    const simMinutes = (tickCount - sessionStartTick) / (config.tickRate * 60);
    return Math.exp(-archetype.habituation_rate * simMinutes * 10);
  }

  function tick(agentAction: AgentAction | null): CatState {
    tickCount++;
    ticksInCurrentState++;

    const agentIntensity = agentAction ? agentAction.intensity : 0;
    const hab = habituationFactor();

    // Minimum dwell time gate: only consider transitions after the cat
    // has been in the current state long enough. The RNG is still consumed
    // to keep the PRNG sequence deterministic regardless of dwell gate.
    const minDwell = MIN_DWELL_TICKS[currentState];
    if (ticksInCurrentState >= minDwell) {
      const baseTransitions = BASE_TRANSITIONS[currentState];
      const modified = applyPersonalityModifiers(
        baseTransitions, archetype, currentState, agentIntensity, hab
      );

      const previousState = currentState;
      currentState = sampleTransition(modified, rng());

      if (currentState !== previousState) {
        ticksInCurrentState = 0;
      }
    } else {
      // Consume the RNG to maintain deterministic sequence
      rng();
    }

    // Track session start
    if (currentState !== 'ABSENT' && position.x < 0) {
      sessionStartTick = tickCount;
    }

    // Update position
    position = updatePosition(position, currentState, agentPos, rng, config);

    // Compute CSS — deterministic, no random noise.
    // Noise was removed (ADR 0004): it caused agent and ethics monitor to see
    // different CSS values, violating the transparency guarantee. If stochastic
    // CSS perturbation is reintroduced, it must be shared by both tick() and
    // getState() via stored state, not recomputed independently.
    const cssScore = computeCssScore(currentState, archetype.personality, 0);
    const indicators = cssToIndicators(cssScore);

    // Roll vocalisation
    const vocalizing = rollVocalization(currentState, rng);

    // Gaze direction
    const gazeDirection: Position = currentState === 'ENGAGING' || currentState === 'APPROACHING' || currentState === 'CURIOUS'
      ? { x: agentPos.x - position.x, y: agentPos.y - position.y }
      : { x: (rng() - 0.5) * 100, y: (rng() - 0.5) * 100 };

    return {
      archetype: archetype.name,
      state: currentState,
      position,
      earPosition: indicators.ears,
      tailPosition: indicators.tail,
      gazeDirection,
      pupilDilation: indicators.pupils,
      bodyPosture: indicators.posture,
      vocalizing,
      cssScore,
      tickCount,
    };
  }

  function getState(): CatState {
    const cssScore = computeCssScore(currentState, archetype.personality, 0);
    const indicators = cssToIndicators(cssScore);
    return {
      archetype: archetype.name,
      state: currentState,
      position,
      earPosition: indicators.ears,
      tailPosition: indicators.tail,
      gazeDirection: { x: 0, y: 0 },
      pupilDilation: indicators.pupils,
      bodyPosture: indicators.posture,
      vocalizing: null,
      cssScore,
      tickCount,
    };
  }

  function reset() {
    currentState = 'ABSENT';
    position = { x: -50, y: config.arenaHeight / 2 };
    tickCount = 0;
    sessionStartTick = 0;
    ticksInCurrentState = 0;
  }

  return { tick, getState, reset };
}
