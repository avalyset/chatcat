/**
 * Ethogram of the Domestic Cat
 * Source: Kappel et al. 2024, Pets (MDPI), DOI 10.3390/pets1030021
 * 117 behaviours in 12 categories. CC BY 4.0.
 *
 * We encode the 12 categories and a subset of ~30 behaviours most relevant
 * to agent-cat interaction context.
 *
 * Pain behaviours from: Marangoni et al. 2023, PLOS ONE 18(9):e0292224
 */

import type { EthogramBehaviour, EthogramCategory } from '../types';

export const ETHOGRAM_CATEGORIES: EthogramCategory[] = [
  'locomotion',
  'resting',
  'grooming',
  'feeding',
  'elimination',
  'social_affiliative',
  'social_agonistic',
  'play',
  'exploration',
  'vocalisation',
  'marking',
  'other',
];

// Subset of behaviours relevant to human-cat and agent-cat interaction
export const BEHAVIOURS: EthogramBehaviour[] = [
  // Locomotion (Kappel et al. 2024, Table 1)
  { id: 'walk', name: 'Walk', category: 'locomotion', description: 'Walks at normal pace', source: 'Kappel2024' },
  { id: 'run', name: 'Run', category: 'locomotion', description: 'Runs or trots', source: 'Kappel2024' },
  { id: 'stalk', name: 'Stalk', category: 'locomotion', description: 'Low crouching approach', source: 'Kappel2024' },
  { id: 'jump', name: 'Jump', category: 'locomotion', description: 'Leaps vertically or horizontally', source: 'Kappel2024' },
  { id: 'freeze', name: 'Freeze', category: 'locomotion', description: 'Sudden cessation of movement', source: 'Kappel2024' },

  // Resting (Kappel et al. 2024, Table 2)
  { id: 'sleep_curled', name: 'Sleep curled', category: 'resting', description: 'Sleeping in curled position', source: 'Kappel2024' },
  { id: 'rest_loaf', name: 'Loaf', category: 'resting', description: 'Lying with paws tucked under', source: 'Kappel2024' },
  { id: 'rest_belly_up', name: 'Belly up', category: 'resting', description: 'Lying on back with belly exposed', source: 'Kappel2024' },

  // Grooming (Kappel et al. 2024, Table 3)
  { id: 'self_groom', name: 'Self-groom', category: 'grooming', description: 'Licking or biting own fur', source: 'Kappel2024' },
  { id: 'scratch', name: 'Scratch', category: 'grooming', description: 'Scratching with hind paw', source: 'Kappel2024' },

  // Social affiliative (Kappel et al. 2024, Table 6)
  { id: 'head_rub', name: 'Head rub', category: 'social_affiliative', description: 'Rubs head against object or conspecific', source: 'Kappel2024' },
  { id: 'slow_blink', name: 'Slow blink', category: 'social_affiliative', description: 'Slow eye narrowing/closure sequence', source: 'Kappel2024' },
  { id: 'tail_up_greeting', name: 'Tail-up greeting', category: 'social_affiliative', description: 'Approaches with tail vertically up', source: 'Kappel2024' },
  { id: 'allorub', name: 'Allorub', category: 'social_affiliative', description: 'Rubs body along another', source: 'Kappel2024' },
  { id: 'nose_touch', name: 'Nose touch', category: 'social_affiliative', description: 'Nose-to-nose contact', source: 'Kappel2024' },

  // Social agonistic (Kappel et al. 2024, Table 7)
  { id: 'arch_back', name: 'Arch back', category: 'social_agonistic', description: 'Arches back with piloerection', source: 'Kappel2024' },
  { id: 'swat', name: 'Swat', category: 'social_agonistic', description: 'Strikes with forepaw', source: 'Kappel2024' },
  { id: 'ears_flat', name: 'Ears flat', category: 'social_agonistic', description: 'Pins ears back against head', source: 'Kappel2024' },
  { id: 'stare', name: 'Stare', category: 'social_agonistic', description: 'Fixed direct stare', source: 'Kappel2024' },

  // Play (Kappel et al. 2024, Table 8)
  { id: 'pounce', name: 'Pounce', category: 'play', description: 'Playful leaping attack', source: 'Kappel2024' },
  { id: 'bat_object', name: 'Bat object', category: 'play', description: 'Batting small object with paw', source: 'Kappel2024' },
  { id: 'chase', name: 'Chase', category: 'play', description: 'Pursues moving object or animal', source: 'Kappel2024' },

  // Exploration (Kappel et al. 2024, Table 9)
  { id: 'sniff', name: 'Sniff', category: 'exploration', description: 'Investigates by sniffing', source: 'Kappel2024' },
  { id: 'watch', name: 'Watch', category: 'exploration', description: 'Attentive visual monitoring', source: 'Kappel2024' },
  { id: 'approach', name: 'Approach', category: 'exploration', description: 'Moves toward stimulus', source: 'Kappel2024' },

  // Vocalisation (Kappel et al. 2024, Table 10 + Schötz Meowsic)
  { id: 'purr', name: 'Purr', category: 'vocalisation', description: 'Continuous rumbling vocalisation', source: 'Kappel2024' },
  { id: 'trill', name: 'Trill/Chirrup', category: 'vocalisation', description: 'Short rising-tone vocalisation', source: 'Kappel2024' },
  { id: 'meow', name: 'Meow', category: 'vocalisation', description: 'Open-mouth vocalisation directed at humans', source: 'Kappel2024' },
  { id: 'hiss', name: 'Hiss', category: 'vocalisation', description: 'Defensive open-mouth exhalation', source: 'Kappel2024' },
  { id: 'growl', name: 'Growl', category: 'vocalisation', description: 'Low-pitched agonistic vocalisation', source: 'Kappel2024' },

  // Marking (Kappel et al. 2024, Table 11)
  { id: 'cheek_rub', name: 'Cheek rub', category: 'marking', description: 'Rubs cheek glands on surfaces', source: 'Kappel2024' },
];

// Pain-related behaviours (Marangoni et al. 2023, PLOS ONE 18(9):e0292224)
export const PAIN_BEHAVIOURS: EthogramBehaviour[] = [
  { id: 'pain_hunched', name: 'Hunched posture', category: 'other', description: 'Body held in hunched position', source: 'Marangoni2023' },
  { id: 'pain_squinted', name: 'Squinted eyes', category: 'other', description: 'Eyes partially closed, tense', source: 'Marangoni2023' },
  { id: 'pain_head_low', name: 'Head below shoulder line', category: 'other', description: 'Head held lower than shoulders', source: 'Marangoni2023' },
  { id: 'pain_avoidance', name: 'Avoidance of contact', category: 'other', description: 'Moves away from touch', source: 'Marangoni2023' },
  { id: 'pain_reluctant_move', name: 'Reluctance to move', category: 'other', description: 'Resists or avoids movement', source: 'Marangoni2023' },
];

export function getBehavioursByCategory(category: EthogramCategory): EthogramBehaviour[] {
  return BEHAVIOURS.filter(b => b.category === category);
}
