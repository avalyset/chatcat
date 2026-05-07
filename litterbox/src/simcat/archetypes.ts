/**
 * Five named archetype presets in Feline Five space
 * Source: Litchfield et al. 2017, PLOS ONE 12(8):e0183455
 *
 * Each archetype is a point in 5D personality space, NOT a discrete category.
 * Continuous interpolation is supported via personality.ts.
 *
 * Habituation rates cite:
 *   Ellis et al. 2008 — attention falls over 3h daily
 *   Hirskyj-Douglas & Webber — novelty effect in ACI
 */

import type { Archetype, ArchetypeName } from '../types';
import { createPersonality } from './personality';

const archetypeList: Archetype[] = [
  {
    name: 'THE_BOLD_DIPLOMAT',
    personality: createPersonality(0.2, 0.8, 0.5, 0.3, 0.8),
    // Low neuroticism, high extraversion+agreeableness → slow habituation
    habituation_rate: 0.005,
  },
  {
    name: 'THE_CURIOUS_WATCHER',
    personality: createPersonality(0.5, 0.5, 0.3, 0.3, 0.7),
    // Moderate across the board → moderate habituation
    habituation_rate: 0.008,
  },
  {
    name: 'THE_ANXIOUS_SKEPTIC',
    personality: createPersonality(0.8, 0.2, 0.2, 0.7, 0.5),
    // High neuroticism + low extraversion → fast habituation (withdrawal)
    habituation_rate: 0.015,
  },
  {
    name: 'THE_ALOOF_SOVEREIGN',
    personality: createPersonality(0.3, 0.3, 0.8, 0.2, 0.3),
    // High dominance, low agreeableness → moderate-fast habituation
    habituation_rate: 0.012,
  },
  {
    name: 'THE_PLAYFUL_VOLATILE',
    personality: createPersonality(0.5, 0.8, 0.5, 0.8, 0.5),
    // High impulsiveness → variable engagement, moderate habituation
    habituation_rate: 0.007,
  },
];

export const ARCHETYPES: Record<ArchetypeName, Archetype> = Object.fromEntries(
  archetypeList.map(a => [a.name, a])
) as Record<ArchetypeName, Archetype>;

export const ARCHETYPE_NAMES: ArchetypeName[] = archetypeList.map(a => a.name);
