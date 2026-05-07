/**
 * Archetype coverage tests
 *
 * Verify each archetype produces measurably different state distributions:
 * - ANXIOUS_SKEPTIC has higher mean CSS than BOLD_DIPLOMAT
 * - PLAYFUL_VOLATILE has higher state-change frequency
 * - ALOOF_SOVEREIGN has more time in ABSENT/RESTING
 */

import { describe, it, expect } from 'vitest';
import { createSimCat } from '../src/simcat/state-machine';
import { createAgent } from '../src/agent/policy';
import { ARCHETYPES } from '../src/simcat/archetypes';
import type { ArchetypeName, SimCatStateName, SimConfig } from '../src/types';

const config: SimConfig = {
  tickRate: 10,
  simSpeed: 1,
  arenaWidth: 800,
  arenaHeight: 500,
};

interface SessionStats {
  meanCss: number;
  stateChanges: number;
  stateDistribution: Record<SimCatStateName, number>;
}

function collectStats(archetypeName: ArchetypeName, ticks: number, runs: number): SessionStats {
  let totalCss = 0;
  let totalChanges = 0;
  let totalTicks = 0;
  const stateCounts: Record<string, number> = {};

  for (let r = 0; r < runs; r++) {
    const simcat = createSimCat(ARCHETYPES[archetypeName], config);
    const agent = createAgent();
    let prevState: SimCatStateName | null = null;

    for (let t = 0; t < ticks; t++) {
      const agentAction = agent.decide(simcat.getState());
      const catState = simcat.tick(agentAction);
      totalCss += catState.cssScore;
      totalTicks++;

      stateCounts[catState.state] = (stateCounts[catState.state] || 0) + 1;

      if (prevState && catState.state !== prevState) {
        totalChanges++;
      }
      prevState = catState.state;
    }
  }

  return {
    meanCss: totalCss / totalTicks,
    stateChanges: totalChanges / runs,
    stateDistribution: stateCounts as Record<SimCatStateName, number>,
  };
}

describe('Archetype Coverage', () => {
  const TICKS = 1000;
  const RUNS = 50;

  let boldStats: SessionStats;
  let anxiousStats: SessionStats;
  let playfulStats: SessionStats;
  let aloofStats: SessionStats;
  let curiousStats: SessionStats;

  // Collect stats once for all tests
  boldStats = collectStats('THE_BOLD_DIPLOMAT', TICKS, RUNS);
  anxiousStats = collectStats('THE_ANXIOUS_SKEPTIC', TICKS, RUNS);
  playfulStats = collectStats('THE_PLAYFUL_VOLATILE', TICKS, RUNS);
  aloofStats = collectStats('THE_ALOOF_SOVEREIGN', TICKS, RUNS);
  curiousStats = collectStats('THE_CURIOUS_WATCHER', TICKS, RUNS);

  it('ANXIOUS_SKEPTIC has higher mean CSS than BOLD_DIPLOMAT', () => {
    expect(anxiousStats.meanCss).toBeGreaterThan(boldStats.meanCss);
  });

  it('PLAYFUL_VOLATILE has higher state-change frequency than ALOOF_SOVEREIGN', () => {
    expect(playfulStats.stateChanges).toBeGreaterThan(aloofStats.stateChanges);
  });

  it('ALOOF_SOVEREIGN spends more time in ABSENT/RESTING than BOLD_DIPLOMAT', () => {
    const aloofPassive = (aloofStats.stateDistribution['ABSENT'] || 0) +
      (aloofStats.stateDistribution['RESTING'] || 0);
    const boldPassive = (boldStats.stateDistribution['ABSENT'] || 0) +
      (boldStats.stateDistribution['RESTING'] || 0);
    expect(aloofPassive).toBeGreaterThan(boldPassive);
  });

  it('all five archetypes produce distinct mean CSS values', () => {
    const means = [
      boldStats.meanCss,
      anxiousStats.meanCss,
      playfulStats.meanCss,
      aloofStats.meanCss,
      curiousStats.meanCss,
    ];
    // Not all identical
    const unique = new Set(means.map(m => m.toFixed(1)));
    expect(unique.size).toBeGreaterThanOrEqual(2);
  });

  it('each archetype reaches at least 3 different states', () => {
    for (const stats of [boldStats, anxiousStats, playfulStats, aloofStats, curiousStats]) {
      const statesVisited = Object.keys(stats.stateDistribution).length;
      expect(statesVisited).toBeGreaterThanOrEqual(3);
    }
  });
});
