/**
 * Agent action space
 *
 * Constraints (HARD-CODED ethical safeguards, not configurable):
 * - No prey-mimicry actions (explicitly out of scope for v0)
 * - Intensity capped at 0.3 when cat is RETREATING/LEAVING
 * - Slow blink protocol: Humphrey et al. 2020, Scientific Reports 10:16503
 *   Half-blink → eye narrow → eye closure
 */

import type { AgentAction, AgentActionType } from '../types';

export function createAction(
  type: AgentActionType,
  intensity: number,
  duration_ms: number
): AgentAction {
  return {
    type,
    intensity: Math.max(0, Math.min(1, intensity)),
    duration_ms: Math.max(0, duration_ms),
  };
}

export function idle(): AgentAction {
  return createAction('idle', 0, 0);
}

// Humphrey et al. 2020: half-blink → eye narrow → eye closure sequence
export function slowBlink(intensity: number): AgentAction {
  return createAction('slow_blink', intensity, 2000);
}

export function trill(intensity: number): AgentAction {
  return createAction('trill', intensity, 500);
}

export function softPurr(intensity: number): AgentAction {
  return createAction('soft_purr', intensity, 3000);
}

export function sideGlance(intensity: number): AgentAction {
  return createAction('side_glance', intensity, 1000);
}

export function pause(duration_ms: number): AgentAction {
  return createAction('pause', 0, duration_ms);
}

// Cap intensity for stress/retreat states (HARD LIMIT)
export function capIntensityForRetreat(action: AgentAction): AgentAction {
  if (action.type === 'side_glance' || action.type === 'soft_purr') {
    return { ...action, intensity: Math.min(0.3, action.intensity) };
  }
  // Only side_glance and soft_purr allowed during retreat
  return idle();
}
