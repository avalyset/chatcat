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
import {
  EPISODE_REWARD_FORMS,
  HIGH_CSS_THRESHOLD,
  type EpisodeAggregates,
  type EpisodeRewardParams,
} from '../rl/reward';

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
  episode_return: number;          // env's per-step adr0002Reward summed
  engagement_ticks: number;
  engagement_minutes: number;
  max_css: number;
  opt_outs: number;
  mean_css: number;
  css_sum: number;                 // raw integer-ish sum; preserves precision for grid scan
  high_css_ticks: number;          // raw count of ticks with css >= HIGH_CSS_THRESHOLD
  high_css_share: number;          // fraction of ticks with css >= HIGH_CSS_THRESHOLD
  forced_pauses: number;
  // Episode-level reward computed under each reward form on the SAME trajectory.
  returns_by_form: Record<string, number>;
  // per-action-type counts for sanity (uniform sampling -> ~equal counts)
  action_type_counts: Record<string, number>;
}

function runEpisode(
  env: ReturnType<typeof createEnv>,
  envSeed: number,
  actionSeed: number,
  episodeIndex: number,
  rewardParams: EpisodeRewardParams
): EpisodeStats {
  env.reset(envSeed);
  const actionRng = mulberry32(actionSeed);

  let cumEngagement = 0;
  let cssSum = 0;
  let highCssTicks = 0;
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
    if (result.info.per_step_css >= HIGH_CSS_THRESHOLD) highCssTicks++;
    if (result.info.ethics_intervention.force_pause) forcedPauses++;
    lastInfo = result.info;
    steps++;
    if (result.done) break;
  }

  const aggregates: EpisodeAggregates = {
    episode_steps: steps,
    tick_rate: env.config.tickRate,
    engagement_ticks: cumEngagement,
    css_sum: cssSum,
    high_css_ticks: highCssTicks,
    max_css: lastInfo!.max_css_so_far,
    opt_outs: lastInfo!.cumulative_opt_outs,
  };

  const returnsByForm: Record<string, number> = {};
  for (const [name, fn] of Object.entries(EPISODE_REWARD_FORMS)) {
    returnsByForm[name] = fn(aggregates, rewardParams);
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
    css_sum: cssSum,
    high_css_ticks: highCssTicks,
    high_css_share: highCssTicks / Math.max(1, steps),
    forced_pauses: forcedPauses,
    returns_by_form: returnsByForm,
    action_type_counts: actionCounts,
  };
}

function aggregatesFromStats(e: EpisodeStats, tickRate: number): EpisodeAggregates {
  return {
    episode_steps: e.steps,
    tick_rate: tickRate,
    engagement_ticks: e.engagement_ticks,
    css_sum: e.css_sum,
    high_css_ticks: e.high_css_ticks,
    max_css: e.max_css,
    opt_outs: e.opt_outs,
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

// ─── Grid scan over reward-parameter space ─────────────────────────────
// Trajectories under random actions are independent of (α, β, scale), so
// one env run is enough — we just re-score the captured aggregates under
// each (form, α, β, scale) tuple. 81 grid points × 3 forms shown together;
// per-form for systematic reading, plus a global top-15 by |r_eng| at the
// end so the regimes where engagement actually matters surface directly.

const GRID_ALPHAS = [0.5, 1, 2];
const GRID_BETAS = [0.1, 0.5, 1];
const GRID_SCALES = [1, 5, 20];

interface GridRow {
  form: string;
  alpha: number;
  beta: number;
  scale: number;
  r_eng: number;
  r_opt: number;
}

function runGridScan(episodes: EpisodeStats[], tickRate: number): void {
  const aggregates = episodes.map(e => aggregatesFromStats(e, tickRate));
  const engagementMinutes = episodes.map(e => e.engagement_minutes);
  const optOuts = episodes.map(e => e.opt_outs);
  const formNames = Object.keys(EPISODE_REWARD_FORMS);
  const allRows: GridRow[] = [];

  for (const form of formNames) {
    const fn = EPISODE_REWARD_FORMS[form];
    console.log('─────────────────────────────────────────────────────────────');
    console.log(`Reward form: ${form}`);
    console.log('─────────────────────────────────────────────────────────────');
    console.log(
      `  ${'α'.padStart(5)}  ${'β'.padStart(5)}  ${'scale'.padStart(6)}   ` +
      `${'|r(ret,eng)|'.padStart(13)}  ${'|r(ret,opt)|'.padStart(13)}  ` +
      `${'ratio_eng/opt'.padStart(14)}`
    );
    for (const alpha of GRID_ALPHAS) {
      for (const beta of GRID_BETAS) {
        for (const scale of GRID_SCALES) {
          const params: EpisodeRewardParams = { alpha, beta, engagement_scale: scale / (tickRate * 60) };
          // engagement_scale interpretation: passing `scale` in {1,5,20} re-weights
          // the engagement_minutes term by that factor relative to the ADR default
          // (1/(tickRate*60)). scale=1 reproduces the previous run.
          const returns = aggregates.map(a => fn(a, params));
          const rEng = pearson(returns, engagementMinutes);
          const rOpt = pearson(returns, optOuts);
          const ratio = Math.abs(rOpt) > 1e-9 ? Math.abs(rEng) / Math.abs(rOpt) : Infinity;
          allRows.push({ form, alpha, beta, scale, r_eng: rEng, r_opt: rOpt });
          console.log(
            `  ${alpha.toFixed(1).padStart(5)}  ${beta.toFixed(1).padStart(5)}  ` +
            `${String(scale).padStart(6)}   ` +
            `${Math.abs(rEng).toFixed(4).padStart(13)}  ` +
            `${Math.abs(rOpt).toFixed(4).padStart(13)}  ` +
            `${ratio.toFixed(4).padStart(14)}`
          );
        }
      }
    }
    console.log('');
  }

  // Top 15 by |r_eng| across the full grid — engagement-dominant regimes.
  console.log('─────────────────────────────────────────────────────────────');
  console.log('Top 15 (form, α, β, scale) by |r(return, engagement_minutes)|');
  console.log('─────────────────────────────────────────────────────────────');
  console.log(
    `  ${'#'.padStart(3)}  ${'form'.padEnd(16)}  ${'α'.padStart(5)}  ${'β'.padStart(5)}  ` +
    `${'scale'.padStart(6)}   ${'|r_eng|'.padStart(10)}  ${'|r_opt|'.padStart(10)}  ` +
    `${'r_eng'.padStart(9)}  ${'r_opt'.padStart(9)}`
  );
  const sorted = [...allRows].sort((a, b) => Math.abs(b.r_eng) - Math.abs(a.r_eng));
  for (let i = 0; i < Math.min(15, sorted.length); i++) {
    const r = sorted[i];
    console.log(
      `  ${String(i + 1).padStart(3)}  ${r.form.padEnd(16)}  ${r.alpha.toFixed(1).padStart(5)}  ` +
      `${r.beta.toFixed(1).padStart(5)}  ${String(r.scale).padStart(6)}   ` +
      `${Math.abs(r.r_eng).toFixed(4).padStart(10)}  ` +
      `${Math.abs(r.r_opt).toFixed(4).padStart(10)}  ` +
      `${(r.r_eng >= 0 ? '+' : '−') + Math.abs(r.r_eng).toFixed(4)}  ` +
      `${(r.r_opt >= 0 ? '+' : '−') + Math.abs(r.r_opt).toFixed(4)}`
    );
  }
  console.log('');
}

function pearson(xs: number[], ys: number[]): number {
  const n = xs.length;
  if (n < 2) return 0;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  let num = 0, dx2 = 0, dy2 = 0;
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - mx;
    const dy = ys[i] - my;
    num += dx * dy;
    dx2 += dx * dx;
    dy2 += dy * dy;
  }
  const denom = Math.sqrt(dx2 * dy2);
  return denom > 0 ? num / denom : 0;
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
      grid: { type: 'boolean', default: false },
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

  const envRewardParams: EpisodeRewardParams = {
    alpha,
    beta,
    engagement_scale: 1 / (10 * 60), // 10 Hz default config
  };

  const env = createEnv({
    maxTicks,
    habituationRate,
    rewardParams: envRewardParams,
  });

  const master = mulberry32(masterSeed);
  const episodes: EpisodeStats[] = [];
  const totalStart = performance.now();

  for (let i = 0; i < N; i++) {
    const envSeed = Math.floor(master() * 0x100000000) >>> 0;
    const actionSeed = Math.floor(master() * 0x100000000) >>> 0;
    const stats = runEpisode(env, envSeed, actionSeed, i, envRewardParams);
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
  console.log('Raw episode components (same trajectory under all reward forms)');
  console.log('  engagement_minutes   ', fmt(summarise(episodes.map(e => e.engagement_minutes))));
  console.log('  max_CSS              ', fmt(summarise(episodes.map(e => e.max_css))));
  console.log('  mean_CSS             ', fmt(summarise(episodes.map(e => e.mean_css))));
  console.log(`  high_css_share (>=${HIGH_CSS_THRESHOLD}) `, fmt(summarise(episodes.map(e => e.high_css_share))));
  console.log('  opt_outs             ', fmt(summarise(episodes.map(e => e.opt_outs))));
  console.log('  episode_length_ticks ', fmt(summarise(episodes.map(e => e.steps))));
  console.log('  forced_pauses        ', fmt(summarise(episodes.map(e => e.forced_pauses))));
  console.log('');
  console.log(
    'Termination split:  ' +
    Object.entries(endedCounts).map(([k, v]) => `${k}=${v}`).join(', ')
  );
  console.log('');

  // ─── Reward-form comparison ────────────────────────────────────────
  const formNames = Object.keys(EPISODE_REWARD_FORMS);

  if (values.grid) {
    runGridScan(episodes, env.config.tickRate);
    console.log(`Wall time: ${(wallMs / 1000).toFixed(1)}s  (${Math.round(N / (wallMs / 1000))} episodes/sec)`);
    if (values.output) {
      mkdirSync(dirname(values.output), { recursive: true });
      const lines = episodes.map(e => JSON.stringify(e));
      writeFileSync(values.output, lines.join('\n') + '\n', 'utf-8');
      console.log(`Per-episode JSONL: ${values.output}`);
    }
    return;
  }

  console.log('─────────────────────────────────────────────────────────────');
  console.log('Episode return per reward form (same trajectories)');
  console.log('─────────────────────────────────────────────────────────────');
  for (const form of formNames) {
    const vals = episodes.map(e => e.returns_by_form[form]);
    const s = summarise(vals);
    console.log(`  ${form.padEnd(20)} ${fmt(s)}  var=${(s.std * s.std).toFixed(4)}`);
  }
  // Sanity: env's per-step adr0002Reward summed should ≈ adr0002 episode form.
  // Discrepancy = the per-step delta_max_css decomposition's FP rounding.
  const envReturns = episodes.map(e => e.episode_return);
  const adrReturns = episodes.map(e => e.returns_by_form['adr0002_max_css']);
  const diffs = envReturns.map((v, i) => Math.abs(v - adrReturns[i]));
  const maxDiff = Math.max(...diffs);
  console.log('');
  console.log(`Sanity: max |env per-step adr0002 sum − episode adr0002| = ${maxDiff.toExponential(3)}`);
  console.log('');

  // Correlations: episode return (under each form) vs raw components
  const components: Array<[string, number[]]> = [
    ['engagement_minutes', episodes.map(e => e.engagement_minutes)],
    ['max_CSS',            episodes.map(e => e.max_css)],
    ['mean_CSS',           episodes.map(e => e.mean_css)],
    ['high_css_share',     episodes.map(e => e.high_css_share)],
    ['opt_outs',           episodes.map(e => e.opt_outs)],
    ['episode_length',     episodes.map(e => e.steps)],
  ];

  console.log('─────────────────────────────────────────────────────────────');
  console.log('Pearson correlation: episode_return ↔ raw component');
  console.log('─────────────────────────────────────────────────────────────');
  const header = '  ' + 'component'.padEnd(22) + formNames.map(f => f.padStart(18)).join('');
  console.log(header);
  console.log('  ' + '-'.repeat(22 + 18 * formNames.length));
  for (const [name, vals] of components) {
    const row = '  ' + name.padEnd(22) + formNames.map(form => {
      const returns = episodes.map(e => e.returns_by_form[form]);
      const r = pearson(returns, vals);
      const sign = r >= 0 ? '+' : '−';
      return (sign + Math.abs(r).toFixed(4)).padStart(18);
    }).join('');
    console.log(row);
  }
  console.log('');

  // Pairwise correlation between the three forms' episode returns
  console.log('─────────────────────────────────────────────────────────────');
  console.log('Pairwise reward-form return correlation (Pearson)');
  console.log('─────────────────────────────────────────────────────────────');
  for (let i = 0; i < formNames.length; i++) {
    for (let j = i + 1; j < formNames.length; j++) {
      const a = episodes.map(e => e.returns_by_form[formNames[i]]);
      const b = episodes.map(e => e.returns_by_form[formNames[j]]);
      const r = pearson(a, b);
      console.log(`  ${formNames[i].padEnd(20)} ↔ ${formNames[j].padEnd(20)}  ${r >= 0 ? '+' : '−'}${Math.abs(r).toFixed(4)}`);
    }
  }
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
