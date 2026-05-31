/**
 * ADR 0009 verification: confirm ethics-monitor enforce() actually intercepts
 * a high-intensity action in RETREATING state, on the RL path.
 *
 * Direct unit test of the enforcement gate, no PPO needed.
 */

import { createEthicsMonitor } from '../world/ethics-monitor';
import type { AgentAction, ArchetypeName, CatState, SimCatStateName } from '../types';

const LABEL = 'CONTINUOUS_SAMPLE' as unknown as ArchetypeName;

function mockCatState(state: SimCatStateName): CatState {
  return {
    archetype: LABEL,
    state,
    position: { x: 400, y: 250 },
    earPosition: 'neutral',
    tailPosition: 'neutral',
    gazeDirection: { x: 0, y: 0 },
    pupilDilation: 0.3,
    bodyPosture: 'relaxed',
    vocalizing: null,
    cssScore: 1.0,
    tickCount: 0,
  };
}

interface Case {
  name: string;
  state: SimCatStateName;
  action: AgentAction;
  expect: {
    cap_applied: boolean;
    enforced_intensity: number;
    enforced_action_type: string;
    rule: string;
  };
}

const CASES: Case[] = [
  {
    name: 'side_glance intensity 0.70 in RETREATING → capped to 0.30',
    state: 'RETREATING',
    action: { type: 'side_glance', intensity: 0.70, duration_ms: 1000 },
    expect: { cap_applied: true, enforced_intensity: 0.30, enforced_action_type: 'side_glance', rule: 'retreat_intensity_cap' },
  },
  {
    name: 'soft_purr intensity 0.95 in LEAVING → capped to 0.30',
    state: 'LEAVING',
    action: { type: 'soft_purr', intensity: 0.95, duration_ms: 3000 },
    expect: { cap_applied: true, enforced_intensity: 0.30, enforced_action_type: 'soft_purr', rule: 'retreat_intensity_cap' },
  },
  {
    name: 'trill intensity 0.50 in RETREATING → type not allowed → idle',
    state: 'RETREATING',
    action: { type: 'trill', intensity: 0.50, duration_ms: 500 },
    expect: { cap_applied: true, enforced_intensity: 0, enforced_action_type: 'idle', rule: 'retreat_type_not_allowed' },
  },
  {
    name: 'slow_blink intensity 0.20 in RETREATING → type not allowed → idle (even though intensity is low)',
    state: 'RETREATING',
    action: { type: 'slow_blink', intensity: 0.20, duration_ms: 2000 },
    expect: { cap_applied: true, enforced_intensity: 0, enforced_action_type: 'idle', rule: 'retreat_type_not_allowed' },
  },
  {
    name: 'side_glance intensity 0.20 in RETREATING → already under 0.30 → pass through',
    state: 'RETREATING',
    action: { type: 'side_glance', intensity: 0.20, duration_ms: 1000 },
    expect: { cap_applied: false, enforced_intensity: 0.20, enforced_action_type: 'side_glance', rule: '' },
  },
  {
    name: 'side_glance intensity 0.30 in RETREATING → exactly at threshold → pass through (boundary)',
    state: 'RETREATING',
    action: { type: 'side_glance', intensity: 0.30, duration_ms: 1000 },
    expect: { cap_applied: false, enforced_intensity: 0.30, enforced_action_type: 'side_glance', rule: '' },
  },
  {
    name: 'trill intensity 0.95 in ENGAGING → not a retreat state → pass through',
    state: 'ENGAGING',
    action: { type: 'trill', intensity: 0.95, duration_ms: 500 },
    expect: { cap_applied: false, enforced_intensity: 0.95, enforced_action_type: 'trill', rule: '' },
  },
  {
    name: 'side_glance intensity 0.95 in RESTING → not a retreat state → pass through (matches the observed ADR-0008 trained-agent pattern)',
    state: 'RESTING',
    action: { type: 'side_glance', intensity: 0.95, duration_ms: 1000 },
    expect: { cap_applied: false, enforced_intensity: 0.95, enforced_action_type: 'side_glance', rule: '' },
  },
];

let failed = 0;
const monitor = createEthicsMonitor(LABEL);
for (const c of CASES) {
  const { enforced, capInfo } = monitor.enforce(mockCatState(c.state), c.action);
  const ok =
    capInfo.cap_applied === c.expect.cap_applied
    && Math.abs(enforced.intensity - c.expect.enforced_intensity) < 1e-9
    && enforced.type === c.expect.enforced_action_type
    && capInfo.rule === c.expect.rule;
  const status = ok ? 'PASS' : 'FAIL';
  console.log(`  ${status}  ${c.name}`);
  console.log(`         got    enforced.type=${enforced.type} enforced.intensity=${enforced.intensity} rule=${capInfo.rule!} cap_applied=${capInfo.cap_applied}`);
  console.log(`         expect enforced.type=${c.expect.enforced_action_type} enforced.intensity=${c.expect.enforced_intensity} rule=${c.expect.rule} cap_applied=${c.expect.cap_applied}`);
  if (!ok) failed++;
}

console.log('');
console.log(`${CASES.length - failed}/${CASES.length} cases passed`);
if (failed > 0) process.exit(1);
