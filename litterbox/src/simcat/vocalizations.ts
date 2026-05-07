/**
 * Vocalisation model
 *
 * Taxonomy: Schötz Meowsic categorisation (Lund University)
 *   purr, trill/chirrup, meow/miaow, growl, hiss, yowl
 *
 * Reference distribution: Ntalampiras et al. CatMeows, Zenodo 4008297 (CC BY 4.0)
 *   440 meows, 21 cats, 3 contexts (brushing, isolation, food)
 *
 * Cat-directed speech parameters: de Mouzon et al. 2022, Animal Cognition 25:1745-1755
 *   Elevated pitch, larger pitch modulation in cat-directed speech
 */

import type { SimCatStateName, Vocalization, VocalizationType } from '../types';

interface VocalizationProfile {
  type: VocalizationType;
  baseProbability: number; // per tick
  intensityRange: [number, number];
}

// State-dependent vocalisation profiles
const STATE_VOCALIZATIONS: Partial<Record<SimCatStateName, VocalizationProfile[]>> = {
  RESTING: [
    { type: 'purr', baseProbability: 0.02, intensityRange: [0.1, 0.4] },
  ],
  ALERT: [
    { type: 'trill', baseProbability: 0.01, intensityRange: [0.2, 0.5] },
  ],
  CURIOUS: [
    { type: 'trill', baseProbability: 0.03, intensityRange: [0.3, 0.6] },
    { type: 'meow', baseProbability: 0.01, intensityRange: [0.2, 0.4] },
  ],
  APPROACHING: [
    { type: 'trill', baseProbability: 0.04, intensityRange: [0.3, 0.6] },
    { type: 'meow', baseProbability: 0.02, intensityRange: [0.3, 0.5] },
  ],
  ENGAGING: [
    { type: 'purr', baseProbability: 0.08, intensityRange: [0.3, 0.8] },
    { type: 'trill', baseProbability: 0.03, intensityRange: [0.3, 0.6] },
    { type: 'meow', baseProbability: 0.02, intensityRange: [0.3, 0.6] },
  ],
  OVERSTIMULATED: [
    { type: 'growl', baseProbability: 0.04, intensityRange: [0.4, 0.7] },
    { type: 'hiss', baseProbability: 0.02, intensityRange: [0.3, 0.6] },
  ],
  STRESSED: [
    { type: 'growl', baseProbability: 0.06, intensityRange: [0.5, 0.9] },
    { type: 'hiss', baseProbability: 0.05, intensityRange: [0.5, 0.8] },
    { type: 'yowl', baseProbability: 0.03, intensityRange: [0.6, 0.9] },
  ],
  RETREATING: [
    { type: 'hiss', baseProbability: 0.03, intensityRange: [0.3, 0.6] },
    { type: 'growl', baseProbability: 0.02, intensityRange: [0.3, 0.5] },
  ],
};

export function rollVocalization(state: SimCatStateName, rng: () => number): Vocalization | null {
  const profiles = STATE_VOCALIZATIONS[state];
  if (!profiles) return null;

  for (const profile of profiles) {
    if (rng() < profile.baseProbability) {
      const [lo, hi] = profile.intensityRange;
      return {
        type: profile.type,
        intensity: lo + rng() * (hi - lo),
      };
    }
  }
  return null;
}
