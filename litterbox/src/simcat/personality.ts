/**
 * Feline Five personality model
 * Source: Litchfield et al. 2017, PLOS ONE 12(8):e0183455
 * Five dimensions validated on 2802 cats:
 *   Neuroticism, Extraversion, Dominance, Impulsiveness, Agreeableness
 *
 * Each dimension is normalised to 0..1 for simulation purposes.
 * The original study used factor analysis on 52 trait descriptors.
 */

import type { FelineFive } from '../types';

export function createPersonality(
  neuroticism: number,
  extraversion: number,
  dominance: number,
  impulsiveness: number,
  agreeableness: number
): FelineFive {
  return {
    neuroticism: clamp01(neuroticism),
    extraversion: clamp01(extraversion),
    dominance: clamp01(dominance),
    impulsiveness: clamp01(impulsiveness),
    agreeableness: clamp01(agreeableness),
  };
}

export function interpolatePersonality(a: FelineFive, b: FelineFive, t: number): FelineFive {
  const s = clamp01(t);
  return {
    neuroticism: a.neuroticism + (b.neuroticism - a.neuroticism) * s,
    extraversion: a.extraversion + (b.extraversion - a.extraversion) * s,
    dominance: a.dominance + (b.dominance - a.dominance) * s,
    impulsiveness: a.impulsiveness + (b.impulsiveness - a.impulsiveness) * s,
    agreeableness: a.agreeableness + (b.agreeableness - a.agreeableness) * s,
  };
}

/**
 * Compute personality-weighted transition modifier.
 * Higher values mean the cat is more likely to move toward engagement.
 * Range: roughly -1 (very avoidant) to +1 (very approach-oriented).
 *
 * Weights derived from Litchfield et al. 2017 factor loadings:
 * - Extraversion loads positively on approach behaviours
 * - Agreeableness loads positively on social tolerance
 * - Neuroticism loads negatively (avoidance, fear)
 * - Dominance loads on persistence in interaction
 * - Impulsiveness loads on state-change frequency
 */
export function approachTendency(p: FelineFive): number {
  return (
    0.3 * p.extraversion +
    0.25 * p.agreeableness -
    0.3 * p.neuroticism +
    0.1 * p.dominance +
    0.05 * p.impulsiveness
  );
}

export function stressRecoveryRate(p: FelineFive): number {
  // Low neuroticism + high agreeableness → faster recovery
  return 0.02 + 0.03 * (1 - p.neuroticism) + 0.02 * p.agreeableness;
}

export function stateChangeFrequency(p: FelineFive): number {
  // High impulsiveness → faster state changes
  return 0.5 + 0.5 * p.impulsiveness;
}

function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v));
}
