/**
 * Determinism cross-check: in-process env vs same env through stdio bridge.
 *
 * Runs N steps in-process with a fixed action sequence + seed; runs the
 * same N steps through a subprocess of bridge.ts with the same seed and
 * same actions; diffs the two trajectories. The bridge is "lossless" iff
 * (reward, done, obs[0..36], css) match exactly at every step.
 *
 * If the serialisation layer drops float precision, that is the same
 * drift class we ruled out for SimCat itself in ADR 0006 — just moved one
 * layer down. This script is the guardrail.
 *
 * Run: tsx src/cli/bridge-determinism.ts  (from litterbox/)
 */

import { spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createEnv } from '../rl/env';

const __dirname = dirname(fileURLToPath(import.meta.url));
import { ACTION_DURATION_MS, ACTION_TYPES } from '../rl/encoders';
import type { AgentAction } from '../types';

function mulberry32(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function sampleAction(rng: () => number): AgentAction {
  const type = ACTION_TYPES[Math.floor(rng() * ACTION_TYPES.length)];
  return { type, intensity: rng(), duration_ms: ACTION_DURATION_MS[type] };
}

interface StepRecord {
  reward: number;
  done: boolean;
  obs: number[];
  css: number;
  tick: number;
}

function runInProcess(seed: number, actions: AgentAction[]): StepRecord[] {
  const env = createEnv();
  env.reset(seed);
  const trajectory: StepRecord[] = [];
  for (const action of actions) {
    const r = env.step(action);
    trajectory.push({
      reward: r.reward,
      done: r.done,
      obs: Array.from(r.obs),
      css: r.info.per_step_css,
      tick: r.info.tick,
    });
    if (r.done) break;
  }
  return trajectory;
}

function runViaBridge(seed: number, actions: AgentAction[]): Promise<StepRecord[]> {
  return new Promise((res, rej) => {
    const bridgePath = resolve(__dirname, 'bridge.ts');
    const proc = spawn('tsx', [bridgePath], { stdio: ['pipe', 'pipe', 'pipe'] });

    const responseQueue: unknown[] = [];
    const waiters: Array<(v: unknown) => void> = [];
    let buffer = '';

    proc.stdout.on('data', (chunk: Buffer) => {
      buffer += chunk.toString();
      let nl: number;
      while ((nl = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, nl);
        buffer = buffer.slice(nl + 1);
        const msg = JSON.parse(line);
        if (waiters.length > 0) waiters.shift()!(msg);
        else responseQueue.push(msg);
      }
    });
    proc.stderr.on('data', (chunk: Buffer) => {
      process.stderr.write('[bridge stderr] ' + chunk.toString());
    });
    proc.on('error', rej);

    function send(msg: object): Promise<any> {
      proc.stdin.write(JSON.stringify(msg) + '\n');
      return new Promise((resolve) => {
        if (responseQueue.length > 0) resolve(responseQueue.shift());
        else waiters.push(resolve);
      });
    }

    (async () => {
      try {
        const resetResp: any = await send({ type: 'reset', seed });
        if (resetResp.error) throw new Error(resetResp.error);

        const trajectory: StepRecord[] = [];
        for (const action of actions) {
          const r: any = await send({
            type: 'step',
            action: { type: action.type, intensity: action.intensity },
          });
          if (r.error) throw new Error(r.error);
          trajectory.push({
            reward: r.reward,
            done: r.done,
            obs: r.obs,
            css: r.info.per_step_css,
            tick: r.info.tick,
          });
          if (r.done) break;
        }
        await send({ type: 'close' });
        proc.on('exit', () => res(trajectory));
      } catch (e) {
        proc.kill();
        rej(e);
      }
    })();
  });
}

function diffTrajectories(a: StepRecord[], b: StepRecord[]): { ok: boolean; where?: string } {
  if (a.length !== b.length) {
    return { ok: false, where: `length mismatch: in-process=${a.length} bridge=${b.length}` };
  }
  for (let i = 0; i < a.length; i++) {
    const x = a[i], y = b[i];
    if (x.reward !== y.reward) return { ok: false, where: `step ${i} reward: ${x.reward} vs ${y.reward}` };
    if (x.done !== y.done) return { ok: false, where: `step ${i} done: ${x.done} vs ${y.done}` };
    if (x.css !== y.css) return { ok: false, where: `step ${i} css: ${x.css} vs ${y.css}` };
    if (x.tick !== y.tick) return { ok: false, where: `step ${i} tick: ${x.tick} vs ${y.tick}` };
    if (x.obs.length !== y.obs.length) return { ok: false, where: `step ${i} obs length: ${x.obs.length} vs ${y.obs.length}` };
    for (let j = 0; j < x.obs.length; j++) {
      if (x.obs[j] !== y.obs[j]) {
        return { ok: false, where: `step ${i} obs[${j}]: ${x.obs[j]} vs ${y.obs[j]}` };
      }
    }
  }
  return { ok: true };
}

async function main() {
  const seed = 42;
  const N = 500;
  const actionRng = mulberry32(0xdeadbeef);
  const actions = Array.from({ length: N }, () => sampleAction(actionRng));

  console.log(`seed=${seed} action_seed=0xdeadbeef N=${N}`);
  console.log('running in-process...');
  const inProc = runInProcess(seed, actions);
  console.log(`  ${inProc.length} steps`);

  console.log('running through bridge subprocess...');
  const bridge = await runViaBridge(seed, actions);
  console.log(`  ${bridge.length} steps`);

  const verdict = diffTrajectories(inProc, bridge);
  if (verdict.ok) {
    console.log(`BIT-IDENTICAL — ${inProc.length} steps, all (reward, done, obs[0..36], css, tick) match exactly.`);
  } else {
    console.log(`DIVERGED: ${verdict.where}`);
    process.exit(1);
  }
}

main().catch(err => { console.error(err); process.exit(1); });
