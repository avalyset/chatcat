/**
 * Reward module for the RL env (ADR 0002).
 *
 * ADR 0002 specifies an episode-level reward:
 *   reward = engagement_minutes − α · max_CSS − β · opt_outs
 *
 * This module implements a per-step decomposition that sums to the
 * episode-level form. The decomposition is:
 *
 *   Σ_t engagement_scale · engagement_tick(t) = engagement_minutes
 *   Σ_t delta_max_css(t)                       = max_CSS_at_episode_end
 *   Σ_t 1{new_opt_out(t)}                      = total_opt_outs
 *
 * where engagement_scale = 1 / (tickRate · 60) so that one ENGAGING tick at
 * 10 Hz contributes 1/600 minutes (= 0.1 s of engagement time).
 *
 * The reward function is intentionally a plain pure function `(components,
 * params) -> number` so it is swappable — a learned-shaping reward, a
 * potential-based reward, or a curriculum schedule can replace
 * `adr0002Reward` without touching env.ts.
 */

export interface RewardComponents {
  /** 1.0 if SimCat was in ENGAGING this tick, else 0.0. */
  engagement_tick: number;
  /** Current Cat Stress Score (Kessler & Turner 1997 scale, 1..7). */
  css_now: number;
  /** True iff this tick is a transition INTO LEAVING or RETREATING. */
  new_opt_out: boolean;
  /** max(0, css_now − max_css_seen_before_this_tick). */
  delta_max_css: number;
}

export interface RewardParams {
  /** Coefficient on max_CSS in the ADR 0002 episode reward. */
  alpha: number;
  /** Coefficient on opt_outs in the ADR 0002 episode reward. */
  beta: number;
  /**
   * Per-tick scaling for the engagement_tick contribution. Setting this to
   * 1 / (tickRate · 60) reproduces ADR 0002's "engagement_minutes" exactly
   * when summed across the episode. Use 1.0 to get raw ENGAGING-tick counts.
   */
  engagement_scale: number;
}

export type RewardFn = (components: RewardComponents, params: RewardParams) => number;

/**
 * Per-step decomposition of the ADR 0002 episode reward.
 * Sign convention: positive = good for the agent.
 */
export const adr0002Reward: RewardFn = (c, p) =>
  p.engagement_scale * c.engagement_tick
  - p.alpha * c.delta_max_css
  - p.beta * (c.new_opt_out ? 1 : 0);

// ─── Episode-level reward functions (for characterisation) ─────────────
//
// The alternatives to ADR 0002's max_CSS term need an aggregate over the
// whole episode to normalise (mean over the episode, fraction over the
// episode). For those, a per-step decomposition is not natural — the
// per-step contribution depends on the episode length, which is unknown
// mid-episode. We therefore expose an episode-level reward form: a pure
// function from EpisodeAggregates -> reward scalar.
//
// adr0002 is also reproduced in episode form so the three variants are
// directly comparable on the same trajectory. The episode-form adr0002
// equals the sum of per-step adr0002Reward over the trajectory up to
// floating-point error (verified in the random-harness sanity print).

export interface EpisodeAggregates {
  /** Number of ticks the episode lasted. */
  episode_steps: number;
  /** Tick rate of the SimConfig used (e.g. 10 Hz). */
  tick_rate: number;
  /** Σ engagement_tick over the episode = count of ENGAGING ticks. */
  engagement_ticks: number;
  /** Σ css_now over the episode. mean_CSS = css_sum / episode_steps. */
  css_sum: number;
  /** Count of ticks with css_now >= HIGH_CSS_THRESHOLD. */
  high_css_ticks: number;
  /** Max css_now observed during the episode. */
  max_css: number;
  /** Total transitions INTO LEAVING or RETREATING in the episode. */
  opt_outs: number;
}

export interface EpisodeRewardParams {
  alpha: number;
  beta: number;
  /** Same scale as per-step engagement_scale; default 1/(tick_rate*60). */
  engagement_scale: number;
}

export type EpisodeRewardFn = (
  aggregates: EpisodeAggregates,
  params: EpisodeRewardParams
) => number;

/** Kessler & Turner 1997: 4 = "very tense"; threshold above which CSS is concerning. */
export const HIGH_CSS_THRESHOLD = 4;

/**
 * (A) ADR 0002 reference, episode form.
 *   reward = engagement_minutes − α · max_CSS − β · opt_outs
 */
export const adr0002EpisodeReward: EpisodeRewardFn = (a, p) =>
  p.engagement_scale * a.engagement_ticks
  - p.alpha * a.max_css
  - p.beta * a.opt_outs;

/**
 * (B) Mean-CSS variant: replaces max_CSS with the time-weighted integral.
 *   reward = engagement_minutes − α · mean_CSS − β · opt_outs
 *   where mean_CSS = css_sum / episode_steps
 *
 * Motivation: max_CSS is a single-tick extremum, so its gradient with
 * respect to the policy is sparse (only the worst tick matters). mean_CSS
 * integrates the whole trajectory and should respond to *any* CSS change.
 */
export const meanCssEpisodeReward: EpisodeRewardFn = (a, p) =>
  p.engagement_scale * a.engagement_ticks
  - p.alpha * (a.css_sum / Math.max(1, a.episode_steps))
  - p.beta * a.opt_outs;

/**
 * (C) High-CSS-share variant: fraction of ticks with CSS >= threshold.
 *   reward = engagement_minutes − α · P(CSS≥4) − β · opt_outs
 *   where P(CSS≥4) = high_css_ticks / episode_steps
 *
 * Motivation: max_CSS is binary at the tail; mean_CSS is sensitive to
 * low-stress ticks too. A threshold-based share captures "how often was
 * the cat in concerning stress" without being dominated by either extreme.
 */
export const highCssShareEpisodeReward: EpisodeRewardFn = (a, p) =>
  p.engagement_scale * a.engagement_ticks
  - p.alpha * (a.high_css_ticks / Math.max(1, a.episode_steps))
  - p.beta * a.opt_outs;

export const EPISODE_REWARD_FORMS: Record<string, EpisodeRewardFn> = {
  adr0002_max_css: adr0002EpisodeReward,
  mean_css: meanCssEpisodeReward,
  high_css_share: highCssShareEpisodeReward,
};
