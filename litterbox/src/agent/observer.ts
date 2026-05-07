/**
 * Agent observer — reads SimCat state and provides structured observations
 * for the policy module. The agent only acts on what it can observe.
 */

import type { CatState, SimCatStateName } from '../types';

export interface Observation {
  state: SimCatStateName;
  cssScore: number;
  isStressed: boolean;
  isRetreating: boolean;
  isEngaging: boolean;
  isAbsent: boolean;
  isApproaching: boolean;
  isCurious: boolean;
  isResting: boolean;
  distanceToAgent: number;
  vocalType: string | null;
  consecutiveHighCssTicks: number;
}

export interface Observer {
  observe(catState: CatState, agentX: number, agentY: number): Observation;
}

export function createObserver(): Observer {
  let consecutiveHighCssTicks = 0;

  function observe(catState: CatState, agentX: number, agentY: number): Observation {
    if (catState.cssScore >= 5) {
      consecutiveHighCssTicks++;
    } else {
      consecutiveHighCssTicks = 0;
    }

    const dx = catState.position.x - agentX;
    const dy = catState.position.y - agentY;
    const distance = Math.sqrt(dx * dx + dy * dy);

    return {
      state: catState.state,
      cssScore: catState.cssScore,
      isStressed: catState.state === 'STRESSED' || catState.state === 'OVERSTIMULATED',
      isRetreating: catState.state === 'RETREATING' || catState.state === 'LEAVING',
      isEngaging: catState.state === 'ENGAGING',
      isAbsent: catState.state === 'ABSENT',
      isApproaching: catState.state === 'APPROACHING',
      isCurious: catState.state === 'CURIOUS',
      isResting: catState.state === 'RESTING',
      distanceToAgent: distance,
      vocalType: catState.vocalizing?.type ?? null,
      consecutiveHighCssTicks,
    };
  }

  return { observe };
}
