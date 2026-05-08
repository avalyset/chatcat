/**
 * Batch runner tests
 *
 * 1. Smoke run completes without errors
 * 2. Ethics guarantee holds across batch
 * 3. Deterministic with same seed
 * 4. Archetype distributions are distinct
 */

import { describe, it, expect } from 'vitest';
import { runOneSession, type SessionRecord } from '../src/cli/batch';
import { ARCHETYPE_NAMES } from '../src/simcat/archetypes';
import type { ArchetypeName } from '../src/types';

const MAX_TICKS = 18000;

function runBatch(
  archetypeName: ArchetypeName,
  sessions: number,
  baseSeed: number = 1,
  maxTicks: number = MAX_TICKS
): SessionRecord[] {
  const records: SessionRecord[] = [];
  for (let i = 0; i < sessions; i++) {
    const seed = baseSeed + i * 1000;
    records.push(runOneSession(archetypeName, seed, maxTicks));
  }
  return records;
}

describe('Batch Runner', () => {
  it('smoke run completes without errors (5 sessions per archetype)', () => {
    const allRecords: SessionRecord[] = [];

    for (const name of ARCHETYPE_NAMES) {
      for (let i = 0; i < 5; i++) {
        const seed = 1 + i * 1000 + ARCHETYPE_NAMES.indexOf(name);
        const record = runOneSession(name, seed, MAX_TICKS);
        allRecords.push(record);
      }
    }

    // 25 records total
    expect(allRecords).toHaveLength(25);

    // All records are valid JSON-serializable with required fields
    for (const r of allRecords) {
      const parsed = JSON.parse(JSON.stringify(r));
      expect(parsed.session_id).toBeTruthy();
      expect(parsed.archetype).toBeTruthy();
      expect(typeof parsed.seed).toBe('number');
      expect(parsed.started_at).toBeTruthy();
      expect(parsed.ended_at).toBeTruthy();
      expect(typeof parsed.wall_ms).toBe('number');
      expect(typeof parsed.duration_ticks).toBe('number');
      expect(parsed.duration_ticks).toBeGreaterThan(0);
      expect(typeof parsed.sim_minutes).toBe('number');
      expect(['leaving', 'max_ticks', 'lockout', 'cooldown_exhausted']).toContain(parsed.ended_reason);
      expect(typeof parsed.css.max).toBe('number');
      expect(typeof parsed.css.mean).toBe('number');
      expect(typeof parsed.css.median).toBe('number');
      expect(parsed.css.ticks_at_each_level).toBeTruthy();
      expect(parsed.states).toBeTruthy();
      expect(typeof parsed.agent.actions_total).toBe('number');
      expect(parsed.agent.actions_by_type).toBeTruthy();
      expect(typeof parsed.agent.mean_intensity).toBe('number');
      expect(typeof parsed.ethics.opt_outs).toBe('number');
      expect(typeof parsed.ethics.forced_pauses).toBe('number');
      expect(parsed.personality_at_start).toBeTruthy();
      expect(typeof parsed.personality_at_start.N).toBe('number');
    }
  });

  it('ethics guarantee holds across 100 anxious_skeptic sessions', () => {
    const records = runBatch('THE_ANXIOUS_SKEPTIC', 100, 42);

    for (const r of records) {
      // The ethics monitor intervenes at CSS >= 6 on the first tick.
      // CSS >= 6 may persist for a few ticks while the SimCat state
      // machine transitions away, but the ethics intervention is always
      // active during those ticks.
      // A max streak > 10 without lockout would indicate a failure.
      if (r.ethics.max_consecutive_high_css_ticks > 10) {
        expect(r.ethics.lockout_triggered).toBe(true);
      }
    }
  }, 30000);

  it('deterministic with same seed', () => {
    const run1: SessionRecord[] = [];
    const run2: SessionRecord[] = [];

    for (let i = 0; i < 10; i++) {
      const seed = 42 + i * 1000;
      run1.push(runOneSession('THE_BOLD_DIPLOMAT', seed, MAX_TICKS));
      run2.push(runOneSession('THE_BOLD_DIPLOMAT', seed, MAX_TICKS));
    }

    for (let i = 0; i < 10; i++) {
      // Strip timestamps (they differ between runs)
      const r1 = { ...run1[i], started_at: '', ended_at: '', wall_ms: 0, session_id: '' };
      const r2 = { ...run2[i], started_at: '', ended_at: '', wall_ms: 0, session_id: '' };
      expect(r1).toEqual(r2);
    }
  });

  it('archetype distributions are distinct', () => {
    const boldRecords = runBatch('THE_BOLD_DIPLOMAT', 50, 1);
    const anxiousRecords = runBatch('THE_ANXIOUS_SKEPTIC', 50, 1);

    const boldMeanMaxCss =
      boldRecords.reduce((s, r) => s + r.css.max, 0) / boldRecords.length;
    const anxiousMeanMaxCss =
      anxiousRecords.reduce((s, r) => s + r.css.max, 0) / anxiousRecords.length;

    // Anxious skeptic should have higher max CSS than bold diplomat
    expect(anxiousMeanMaxCss).toBeGreaterThan(boldMeanMaxCss);

    const boldMeanDuration =
      boldRecords.reduce((s, r) => s + r.sim_minutes, 0) / boldRecords.length;
    const anxiousMeanDuration =
      anxiousRecords.reduce((s, r) => s + r.sim_minutes, 0) / anxiousRecords.length;

    // Anxious skeptic sessions should be shorter on average
    // (more likely to hit cooldown/lockout or LEAVING early)
    expect(anxiousMeanDuration).toBeLessThan(boldMeanDuration);
  }, 60000);
});
