/**
 * Cat Stress Score (CSS)
 * Source: Kessler & Turner 1997, Animal Welfare 6:243-254
 *
 * 7-point scale based on 11 postural/behavioural categories:
 *   1 = fully relaxed
 *   2 = weakly relaxed
 *   3 = weakly tense
 *   4 = very tense
 *   5 = fearful/stiff
 *   6 = very fearful/stiff
 *   7 = terrorised
 *
 * In simulation: CSS is computed from state + personality, not from
 * direct postural observation (since we are generating posture, not reading it).
 */

import type { SimCatStateName, FelineFive } from '../types';

// Base CSS by state — derived from Kessler & Turner 1997 behavioural descriptions
const STATE_BASE_CSS: Record<SimCatStateName, number> = {
  ABSENT: 1,
  RESTING: 1,
  ALERT: 2,
  CURIOUS: 2,
  APPROACHING: 2.5,
  ENGAGING: 2,
  OVERSTIMULATED: 4.5,
  STRESSED: 5.5,
  RETREATING: 4,
  LEAVING: 3,
};

/**
 * Compute CSS from state + personality + noise.
 * Neuroticism shifts the baseline up; agreeableness dampens it slightly.
 */
export function computeCssScore(
  state: SimCatStateName,
  personality: FelineFive,
  noise: number // -1..1 random factor
): number {
  const base = STATE_BASE_CSS[state];
  const neuroticShift = personality.neuroticism * 1.0;
  const agreeableDampen = personality.agreeableness * -0.3;
  const raw = base + neuroticShift + agreeableDampen + noise * 0.3;
  return Math.max(1, Math.min(7, Math.round(raw * 10) / 10));
}

/**
 * Map CSS to body-language indicators for visualisation.
 * Source: Kessler & Turner 1997, Table 1.
 */
export function cssToIndicators(css: number) {
  if (css <= 1.5) {
    return { ears: 'forward' as const, tail: 'up' as const, posture: 'relaxed' as const, pupils: 0.3 };
  } else if (css <= 2.5) {
    return { ears: 'forward' as const, tail: 'neutral' as const, posture: 'relaxed' as const, pupils: 0.4 };
  } else if (css <= 3.5) {
    return { ears: 'neutral' as const, tail: 'neutral' as const, posture: 'relaxed' as const, pupils: 0.5 };
  } else if (css <= 4.5) {
    return { ears: 'sideways' as const, tail: 'low' as const, posture: 'crouched' as const, pupils: 0.6 };
  } else if (css <= 5.5) {
    return { ears: 'flat' as const, tail: 'low' as const, posture: 'frozen' as const, pupils: 0.8 };
  } else if (css <= 6.5) {
    return { ears: 'flat' as const, tail: 'puffed' as const, posture: 'arched' as const, pupils: 0.9 };
  } else {
    return { ears: 'flat' as const, tail: 'puffed' as const, posture: 'frozen' as const, pupils: 1.0 };
  }
}
