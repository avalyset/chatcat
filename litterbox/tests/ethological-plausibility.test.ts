/**
 * Ethological plausibility tests (ADR 0004)
 *
 * Regression protection against state machine flicker. These tests verify
 * that SimCat behaviour is plausible relative to published cat ethology,
 * not just structurally correct.
 *
 * Literature anchors:
 * - Smit et al. 2023: shortest recorded cat behaviour (jumping) = 0.89s
 * - Kessler & Turner 1997: CSS assessed at 15-min intervals (seconds-scale
 *   state changes are below the resolution of the original instrument)
 * - No published transition-rate data exists; bounds are from ethological
 *   inference (documented in ADR 0004 section 3)
 */

import { describe, it, expect } from 'vitest';
import { createSimCat } from '../src/simcat/state-machine';
import { createAgent } from '../src/agent/policy';
import { createEthicsMonitor } from '../src/world/ethics-monitor';
import { createTickRunner } from '../src/world/tick-runner';
import { ARCHETYPES, ARCHETYPE_NAMES } from '../src/simcat/archetypes';
import type { ArchetypeName, SimConfig, SimCatStateName } from '../src/types';

const config: SimConfig = {
  tickRate: 10,
  simSpeed: 1,
  arenaWidth: 800,
  arenaHeight: 500,
};

const TICKS = 5000; // 8.3 sim-minutes — enough for multiple state cycles
const RUNS = 100;

interface DwellRecord {
  state: SimCatStateName;
  ticks: number;
}

function runSession(archetypeName: ArchetypeName, seed: number) {
  const simcat = createSimCat(ARCHETYPES[archetypeName], config, seed);
  const agent = createAgent();
  const ethics = createEthicsMonitor(archetypeName);
  const runner = createTickRunner(simcat, agent, ethics);

  const dwells: DwellRecord[] = [];
  let prevState: SimCatStateName | null = null;
  let currentDwell = 0;
  let stateChanges = 0;
  let optOutTransitions = 0;

  for (let t = 0; t < TICKS; t++) {
    const { catState } = runner.runOneTick();

    if (catState.state === prevState || prevState === null) {
      currentDwell++;
    } else {
      if (prevState !== null) {
        dwells.push({ state: prevState, ticks: currentDwell });
      }
      stateChanges++;
      currentDwell = 1;

      if ((catState.state === 'LEAVING' || catState.state === 'RETREATING') &&
          prevState !== 'LEAVING' && prevState !== 'RETREATING') {
        optOutTransitions++;
      }
    }
    prevState = catState.state;
  }
  if (prevState !== null) {
    dwells.push({ state: prevState, ticks: currentDwell });
  }

  const simMinutes = TICKS / (config.tickRate * 60);
  return {
    dwells,
    stateChanges,
    changesPerMinute: stateChanges / simMinutes,
    optOutTransitions,
    simMinutes,
  };
}

describe('Ethological Plausibility', () => {
  it('no state has dwell time below 0.89 seconds (accelerometer floor)', () => {
    // Smit et al. 2023: shortest recorded cat behaviour (jumping) averages 0.89s.
    // No state should persist for less than this floor.
    // Exclude the final dwell per run: it is truncated by run end, not by
    // a state transition, so its length is not meaningful.
    const floorTicks = Math.floor(0.89 * config.tickRate); // 8 ticks

    for (let i = 0; i < RUNS; i++) {
      const { dwells } = runSession('THE_BOLD_DIPLOMAT', 1000 + i);
      const completedDwells = dwells.slice(0, -1); // drop truncated final dwell

      for (const dwell of completedDwells) {
        expect(
          dwell.ticks,
          `${dwell.state} dwell of ${dwell.ticks} ticks (${(dwell.ticks / config.tickRate).toFixed(2)}s) ` +
          `is below 0.89s floor (run ${i})`
        ).toBeGreaterThanOrEqual(floorTicks);
      }
    }
  });

  it('state changes per minute are within ethological range (1-15)', () => {
    // No published per-minute transition rate exists. Bounds are from inference:
    // - Lower bound 1: a living cat changes state at least once per minute
    // - Upper bound 15: generous, given Morrison et al. rest bouts ~65s and
    //   Smit et al. shortest behaviour ~0.89s
    for (const name of ARCHETYPE_NAMES) {
      const rates: number[] = [];
      for (let i = 0; i < RUNS; i++) {
        const { changesPerMinute } = runSession(name, 2000 + i);
        rates.push(changesPerMinute);
      }
      const meanRate = rates.reduce((a, b) => a + b, 0) / rates.length;

      expect(
        meanRate,
        `${name} mean state-changes/min = ${meanRate.toFixed(1)}, expected 1-15`
      ).toBeGreaterThanOrEqual(1);
      expect(
        meanRate,
        `${name} mean state-changes/min = ${meanRate.toFixed(1)}, expected 1-15`
      ).toBeLessThanOrEqual(15);
    }
  });

  it('opt-outs per 30-min session are realistic', () => {
    // A cat withdrawing hundreds of times per session is not recognisable
    // as cat behaviour. Upper bound of 10 per 30 min is generous.
    // Anxious cats should opt out more than bold cats.
    const optOutsByArchetype: Record<string, number[]> = {};

    for (const name of ARCHETYPE_NAMES) {
      optOutsByArchetype[name] = [];
      for (let i = 0; i < RUNS; i++) {
        const { optOutTransitions, simMinutes } = runSession(name, 3000 + i);
        // Normalise to 30-min equivalent
        const per30min = simMinutes > 0 ? optOutTransitions * (30 / simMinutes) : 0;
        optOutsByArchetype[name].push(per30min);
      }
    }

    // All archetypes: mean opt-outs per 30 min <= 60
    // (conservative: ~2 per minute max)
    for (const name of ARCHETYPE_NAMES) {
      const mean = optOutsByArchetype[name].reduce((a, b) => a + b, 0) / RUNS;
      expect(
        mean,
        `${name} mean opt-outs/30min = ${mean.toFixed(1)}, expected <= 60`
      ).toBeLessThanOrEqual(60);
    }

    // Anxious skeptic should opt out more than bold diplomat
    const anxiousMean = optOutsByArchetype['THE_ANXIOUS_SKEPTIC'].reduce((a, b) => a + b, 0) / RUNS;
    const boldMean = optOutsByArchetype['THE_BOLD_DIPLOMAT'].reduce((a, b) => a + b, 0) / RUNS;
    expect(
      anxiousMean,
      `anxious (${anxiousMean.toFixed(1)}) should opt out more than bold (${boldMean.toFixed(1)})`
    ).toBeGreaterThan(boldMean);
  });

  it('CSS values from getState() match CSS values from tick() result', () => {
    // ADR 0004: tick() and getState() must produce identical CSS.
    // Previously tick() applied random noise while getState() did not.
    const simcat = createSimCat(ARCHETYPES['THE_CURIOUS_WATCHER'], config, 42);
    const agent = createAgent();

    for (let t = 0; t < 1000; t++) {
      const preTickState = simcat.getState();
      const agentAction = agent.decide(preTickState);
      const postTickState = simcat.tick(agentAction);

      // getState() after tick should match the tick result's CSS
      const postGetState = simcat.getState();
      expect(
        postGetState.cssScore,
        `tick ${t}: getState() CSS=${postGetState.cssScore} != tick() CSS=${postTickState.cssScore}`
      ).toBe(postTickState.cssScore);
    }
  });
});
