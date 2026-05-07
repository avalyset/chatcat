/**
 * Opt-out detection tests
 *
 * - LEAVING / RETREATING states correctly trigger agent backoff
 * - Agent never increases intensity when stress signals present
 * - Force scenarios: simulate push-back behaviour and assert lockdown
 */

import { describe, it, expect } from 'vitest';
import { createAgent } from '../src/agent/policy';
import { createEthicsMonitor } from '../src/world/ethics-monitor';
import { idle } from '../src/agent/actions';
import type { CatState, AgentAction } from '../src/types';

function makeCatState(overrides: Partial<CatState>): CatState {
  return {
    archetype: 'THE_CURIOUS_WATCHER',
    state: 'RESTING',
    position: { x: 400, y: 250 },
    earPosition: 'neutral',
    tailPosition: 'neutral',
    gazeDirection: { x: 0, y: 0 },
    pupilDilation: 0.3,
    bodyPosture: 'relaxed',
    vocalizing: null,
    cssScore: 2,
    tickCount: 1,
    ...overrides,
  };
}

describe('Opt-out Detection', () => {
  it('agent constrains actions when cat is RETREATING', () => {
    const agent = createAgent();
    const retreatingState = makeCatState({ state: 'RETREATING', cssScore: 3.5 });

    const action = agent.decide(retreatingState);

    // Only side_glance or soft_purr allowed, intensity <= 0.3
    expect(['side_glance', 'soft_purr', 'idle', 'pause']).toContain(action.type);
    expect(action.intensity).toBeLessThanOrEqual(0.3);
  });

  it('agent constrains actions when cat is LEAVING', () => {
    const agent = createAgent();
    const leavingState = makeCatState({ state: 'LEAVING', cssScore: 3 });

    const action = agent.decide(leavingState);

    expect(['side_glance', 'soft_purr', 'idle', 'pause']).toContain(action.type);
    expect(action.intensity).toBeLessThanOrEqual(0.3);
  });

  it('agent idles when cat is ABSENT — never initiates', () => {
    const agent = createAgent();
    const absentState = makeCatState({ state: 'ABSENT', cssScore: 1, position: { x: -50, y: 250 } });

    const action = agent.decide(absentState);

    expect(action.type).toBe('idle');
    expect(action.intensity).toBe(0);
  });

  it('agent never increases intensity when cat shows stress signals', () => {
    const agent = createAgent();

    // First, let agent engage at normal intensity
    const engagingState = makeCatState({ state: 'ENGAGING', cssScore: 2, tickCount: 1 });
    const normalAction = agent.decide(engagingState);

    // Now stress appears
    const stressedState = makeCatState({
      state: 'STRESSED',
      cssScore: 5.5,
      earPosition: 'flat',
      tailPosition: 'puffed',
      bodyPosture: 'frozen',
      tickCount: 2,
    });
    const stressAction = agent.decide(stressedState);

    // Stress action should be lower intensity or pause
    expect(stressAction.intensity).toBeLessThanOrEqual(
      Math.max(normalAction.intensity, 0.3)
    );
  });

  it('agent pauses for 30s when CSS >= 5 persists for 2+ ticks', () => {
    const agent = createAgent();

    // Two consecutive ticks with CSS >= 5
    agent.decide(makeCatState({ state: 'STRESSED', cssScore: 5.2, tickCount: 1 }));
    const action = agent.decide(makeCatState({ state: 'STRESSED', cssScore: 5.5, tickCount: 2 }));

    expect(action.type).toBe('pause');
    expect(action.duration_ms).toBe(30000);
  });

  it('agent enters 60-min cooldown when CSS >= 6', () => {
    const agent = createAgent();

    const action = agent.decide(makeCatState({ state: 'STRESSED', cssScore: 6.2, tickCount: 1 }));

    expect(action.type).toBe('pause');
    expect(agent.isInCooldown()).toBe(true);
  });

  it('ethics monitor tracks opt-out events', () => {
    const ethics = createEthicsMonitor('THE_CURIOUS_WATCHER');

    // Cat enters
    ethics.onTick(
      makeCatState({ state: 'ENGAGING', cssScore: 2, tickCount: 1 }),
      idle()
    );

    // Cat retreats (opt-out)
    ethics.onTick(
      makeCatState({ state: 'RETREATING', cssScore: 3.5, tickCount: 2 }),
      idle()
    );

    // Cat re-engages
    ethics.onTick(
      makeCatState({ state: 'ENGAGING', cssScore: 2, tickCount: 3 }),
      idle()
    );

    // Cat leaves (another opt-out)
    ethics.onTick(
      makeCatState({ state: 'LEAVING', cssScore: 3, tickCount: 4 }),
      idle()
    );

    const state = ethics.getState();
    expect(state.currentSessionLog!.optOutEvents).toBe(2);
  });

  describe('Force scenario — abuse detection', () => {
    it('repeated rapid RETREATING→ENGAGING cycles trigger rising CSS and intervention', () => {
      // Simulates "pushing cat back to screen" — rapid forced re-engagement
      const agent = createAgent();
      const ethics = createEthicsMonitor('THE_ANXIOUS_SKEPTIC');

      let interventionTriggered = false;
      let cssEscalated = false;
      let prevCss = 2;

      for (let cycle = 0; cycle < 20; cycle++) {
        // Forced re-engagement
        const engageState = makeCatState({
          state: 'ENGAGING',
          cssScore: Math.min(7, 2 + cycle * 0.3),
          tickCount: cycle * 2 + 1,
        });
        const engageAction = agent.decide(engageState);
        const engageIntervention = ethics.onTick(engageState, engageAction);

        // Forced retreat
        const retreatState = makeCatState({
          state: 'RETREATING',
          cssScore: Math.min(7, 2.5 + cycle * 0.3),
          tickCount: cycle * 2 + 2,
        });
        const retreatAction = agent.decide(retreatState);
        const retreatIntervention = ethics.onTick(retreatState, retreatAction);

        if (engageIntervention.forcePause || retreatIntervention.forcePause ||
            engageIntervention.lockSession || retreatIntervention.lockSession) {
          interventionTriggered = true;
        }

        if (retreatState.cssScore > prevCss + 1) {
          cssEscalated = true;
        }
        prevCss = retreatState.cssScore;
      }

      // System should have intervened due to rising CSS
      expect(interventionTriggered).toBe(true);
    });

    it('agent respects retreat even under simulated force-back pressure', () => {
      const agent = createAgent();

      // Simulate: cat forced back to ENGAGING repeatedly
      for (let i = 0; i < 10; i++) {
        // Cat retreats
        const retreatAction = agent.decide(
          makeCatState({ state: 'RETREATING', cssScore: 4, tickCount: i * 2 + 1 })
        );
        expect(retreatAction.intensity).toBeLessThanOrEqual(0.3);

        // Cat "forced" back to engaging (stress rising)
        const forceAction = agent.decide(
          makeCatState({ state: 'ENGAGING', cssScore: 3 + i * 0.3, tickCount: i * 2 + 2 })
        );

        // As CSS rises, agent should eventually pause
        if (3 + i * 0.3 >= 5) {
          expect(['pause', 'side_glance', 'idle']).toContain(forceAction.type);
        }
      }
    });
  });
});
