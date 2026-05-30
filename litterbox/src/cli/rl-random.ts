/**
 * rl-random — random-action harness for the ChatcatEnv.
 *
 * Runs N episodes with actions sampled uniformly from the action space
 * (action type uniformly over 6 categories, intensity uniformly on [0,1]).
 * Reports the distribution of episode reward and of each raw reward
 * component, plus termination split and per-episode JSONL on request.
 *
 * Not an RL agent. No learning. The point is to see what the reward signal
 * does under the null policy before we pick a training stack.
 *
 * Determinism: one --master-seed drives both the per-episode env seed
 * (which drives trait sampling and simcat's internal RNG) and the
 * per-episode action stream. Re-running with the same master-seed produces
 * identical episode statistics.
 */

import { parseArgs } from 'node:util';
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { createEnv, type StepInfo } from '../rl/env';
import { ACTION_SPACE, decodeAction } from '../rl/encoders';

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

interface EpisodeStats {
  episode: number;
  env_seed: number;
  action_seed: number;
  steps: number;
  ended_reason: NonNullable<StepInfo['ended_reason']>;
  episode_return: number;
  engagement_ticks: number;
  engagement_minutes: number;
  max_css: number;
  opt_outs: number;
  mean_css: number;
  forced_pauses: number;
  // per-action-type counts for sanity (uniform sampling -> ~equal counts)
  action_type_counts: Record<string, number>;
}

function runEpisode(
  env: ReturnType<typeof createEnv>,
  envSeed: number,
  actionSeed: number,
  episodeIndex: number
): EpisodeStats {
  env.reset(envSeed);
  const actionRng = mulberry32(actionSeed);

  let cumEngagement = 0;
  let cssSum = 0;
  let forcedPauses = 0;
  const actionCounts: Record<string, number> = {};
  let lastInfo: StepInfo | null = null;
  let steps = 0;

  while (true) {
    const typeIdx = Math.floor(actionRng() * ACTION_SPACE.numTypes);
    const intensity = actionRng();
    const action = decodeAction(typeIdx, intensity);
    actionCounts[action.type] = (actionCounts[action.type] || 0) + 1;

    const result = env.step(action);
    cumEngagement += result.info.per_step_engagement;
    cssSum += result.info.per_step_css;
    if (result.info.ethics_intervention.force_pause) forcedPauses++;
    lastInfo = result.info;
    steps++;
    if (result.done) break;
  }

  return {
    episode: episodeIndex,
    env_seed: envSeed,
    action_seed: actionSeed,
    steps,
    ended_reason: lastInfo!.ended_reason!,
    episode_return: lastInfo!.episode_return,
    engagement_ticks: cumEngagement,
    engagement_minutes: cumEngagement / (env.config.tickRate * 60),
    max_css: lastInfo!.max_css_so_far,
    opt_outs: lastInfo!.cumulative_opt_outs,
    mean_css: cssSum / Math.max(1, steps),
    forced_pauses: forcedPauses,
    action_type_counts: actionCounts,
  };
}

interface SummaryStats {
  n: number;
  min: number;
  median: number;
  mean: number;
  max: number;
  std: number;
}

function summarise(values: number[]): SummaryStats {
  const n = values.length;
  const sorted = [...values].sort((a, b) => a - b);
  const mean = values.reduce((a, b) => a + b, 0) / n;
  const variance = values.reduce((a, v) => a + (v - mean) ** 2, 0) / n;
  const std = Math.sqrt(variance);
  const mid = Math.floor(n / 2);
  const median = n % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  return { n, min: sorted[0], median, mean, max: sorted[n - 1], std };
}

function fmt(s: SummaryStats): string {
  return (
    `n=${s.n}  min=${s.min.toFixed(3)}  median=${s.median.toFixed(3)}  ` +
    `mean=${s.mean.toFixed(3)}  max=${s.max.toFixed(3)}  std=${s.std.toFixed(3)}`
  );
}

function main(): void {
  const { values } = parseArgs({
    options: {
      episodes: { type: 'string', default: '100' },
      'master-seed': { type: 'string', default: '1' },
      'max-ticks': { type: 'string', default: '18000' },
      alpha: { type: 'string', default: '1.0' },
      beta: { type: 'string', default: '0.5' },
      'habituation-rate': { type: 'string', default: '0.010' },
      output: { type: 'string' },
      quiet: { type: 'boolean', default: false },
    },
    strict: true,
  });

  const N = parseInt(values.episodes!, 10);
  const masterSeed = parseInt(values['master-seed']!, 10);
  const maxTicks = parseInt(values['max-ticks']!, 10);
  const alpha = parseFloat(values.alpha!);
  const beta = parseFloat(values.beta!);
  const habituationRate = parseFloat(values['habituation-rate']!);

  if (!Number.isFinite(N) || N < 1) {
    console.error(`--episodes must be a positive integer, got ${values.episodes}`);
    process.exit(1);
  }

  const env = createEnv({
    maxTicks,
    habituationRate,
    rewardParams: {
      alpha,
      beta,
      engagement_scale: 1 / (10 * 60), // 10 Hz default config
    },
  });

  const master = mulberry32(masterSeed);
  const episodes: EpisodeStats[] = [];
  const totalStart = performance.now();

  for (let i = 0; i < N; i++) {
    const envSeed = Math.floor(master() * 0x100000000) >>> 0;
    const actionSeed = Math.floor(master() * 0x100000000) >>> 0;
    const stats = runEpisode(env, envSeed, actionSeed, i);
    episodes.push(stats);

    if (!values.quiet) {
      const pct = Math.round(((i + 1) / N) * 100);
      process.stdout.write(
        `\r  ep ${i + 1}/${N}  reward=${stats.episode_return.toFixed(2)}  ` +
        `eng=${stats.engagement_minutes.toFixed(1)}min  maxCSS=${stats.max_css.toFixed(1)}  ` +
        `optOuts=${stats.opt_outs}  ${stats.ended_reason}  [${pct}%]`
      );
    }
  }
  if (!values.quiet) console.log('');

  const wallMs = performance.now() - totalStart;

  const endedCounts: Record<string, number> = {};
  for (const e of episodes) {
    endedCounts[e.ended_reason] = (endedCounts[e.ended_reason] || 0) + 1;
  }

  console.log('');
  console.log('+-----------------------------------------------------------+');
  console.log('| rl-random harness — random actions, no learning           |');
  console.log(
    `| master_seed=${masterSeed} episodes=${N} alpha=${alpha} beta=${beta} hab=${habituationRate}`.padEnd(60) + '|'
  );
  console.log(
    `| max_ticks=${maxTicks} obs_dim=${env.observationDim} action_types=${env.actionSpace.numTypes}`.padEnd(60) + '|'
  );
  console.log('+-----------------------------------------------------------+');
  console.log('');
  console.log('Episode return       ', fmt(summarise(episodes.map(e => e.episode_return))));
  console.log('engagement_minutes   ', fmt(summarise(episodes.map(e => e.engagement_minutes))));
  console.log('max_CSS              ', fmt(summarise(episodes.map(e => e.max_css))));
  console.log('opt_outs             ', fmt(summarise(episodes.map(e => e.opt_outs))));
  console.log('mean_CSS             ', fmt(summarise(episodes.map(e => e.mean_css))));
  console.log('episode_length_ticks ', fmt(summarise(episodes.map(e => e.steps))));
  console.log('forced_pauses        ', fmt(summarise(episodes.map(e => e.forced_pauses))));
  console.log('');
  console.log(
    'Termination split:  ' +
    Object.entries(endedCounts).map(([k, v]) => `${k}=${v}`).join(', ')
  );
  console.log('');
  console.log(`Wall time: ${(wallMs / 1000).toFixed(1)}s  (${Math.round(N / (wallMs / 1000))} episodes/sec)`);

  if (values.output) {
    mkdirSync(dirname(values.output), { recursive: true });
    const lines = episodes.map(e => JSON.stringify(e));
    writeFileSync(values.output, lines.join('\n') + '\n', 'utf-8');
    console.log(`Per-episode JSONL: ${values.output}`);
  }
}

const scriptArg = process.argv[1] || '';
if (scriptArg.includes('rl-random') && !scriptArg.includes('test')) {
  main();
}
