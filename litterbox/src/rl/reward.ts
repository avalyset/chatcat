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
