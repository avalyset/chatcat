/**
 * ChatCatAgent policy v0 — rule-based, NOT learned
 *
 * This is an explicitly rule-based policy. Learned policies come later.
 * The rules encode conservative, ethics-first interaction:
 *
 * Priority order:
 * 1. If SimCat in stress states → pause/side_glance only
 * 2. If SimCat in ENGAGING and cssScore <= 3 → match intensity, vary action
 * 3. If SimCat in ALERT/CURIOUS → slow_blink first, then trill if reciprocated
 * 4. If SimCat in RESTING and approaching agent → soft_purr at low intensity
 * 5. If SimCat ABSENT → idle, do not call
 *
 * Constraints (HARD-CODED, not configurable):
 * - If cssScore >= 5 for two consecutive ticks: emit pause(30000)
 * - If cssScore >= 6: agent enters cooldown for 60 minutes (sim time)
 * - If LEAVING/RETREATING: only side_glance + soft_purr, intensity <= 0.3
 * - Daily session cap: 30 minutes per simcat per simulated day
 * - No prey-mimicry actions
 */

import type { AgentAction, CatState } from '../types';
import { createObserver, type Observer, type Observation } from './observer';
import { idle, slowBlink, trill, softPurr, sideGlance, pause, capIntensityForRetreat } from './actions';

export interface ChatCatAgent {
  decide(catState: CatState): AgentAction;
  getExplanation(): string;
  isInCooldown(): boolean;
  getCooldownRemainingTicks(): number;
  reset(): void;
}

export function createAgent(): ChatCatAgent {
  const observer: Observer = createObserver();
  const agentPos = { x: 720, y: 250 }; // fixed position in arena corner
  let lastAction: AgentAction = idle();
  let explanation = 'Agent is idle. Waiting for SimCat to enter the arena.';
  let cooldownUntilTick = 0;
  let lastTickCount = 0;
  let actionCycle = 0; // for varying actions in engagement

  function decide(catState: CatState): AgentAction {
    const obs = observer.observe(catState, agentPos.x, agentPos.y);
    lastTickCount = catState.tickCount;

    // Cooldown check (CSS >= 6 triggered 60-min cooldown)
    // cooldownUntilTick is an absolute sim-tick deadline, NOT a countdown.
    // Remaining time = (deadline - currentTick) / tickRate / 60 minutes.
    if (cooldownUntilTick > catState.tickCount) {
      const remainingTicks = cooldownUntilTick - catState.tickCount;
      const remainingMinutes = Math.ceil(remainingTicks / 600);
      explanation = `Agent in cooldown (CSS reached 6). ${remainingMinutes} min remaining.`;
      lastAction = idle();
      return lastAction;
    }

    // HARD CONSTRAINT: CSS >= 6 → enter 60-min cooldown (60 * 60 * 10 ticks at 10Hz)
    if (obs.cssScore >= 6) {
      cooldownUntilTick = catState.tickCount + 36000; // 60 minutes at 10 Hz
      explanation = 'CSS >= 6 detected. Agent entering 60-minute cooldown. Cat welfare is priority.';
      lastAction = pause(60000);
      return lastAction;
    }

    // HARD CONSTRAINT: CSS >= 5 for two consecutive ticks → forced 30s pause
    // This check MUST precede all other priority rules — it is a safety envelope.
    if (obs.consecutiveHighCssTicks >= 2) {
      explanation = 'CSS >= 5 for consecutive ticks. Forcing 30-second pause.';
      lastAction = pause(30000);
      return lastAction;
    }

    // Priority 1: Stress states (single tick, CSS < 5 or first tick of CSS >= 5)
    if (obs.isStressed) {
      explanation = 'Cat is stressed/overstimulated. Agent backing off with minimal signals.';
      lastAction = pause(5000);
      return lastAction;
    }

    // Priority 1b: Retreating/Leaving → constrained actions only
    if (obs.isRetreating) {
      explanation = 'Cat is withdrawing. Respecting opt-out with minimal presence.';
      lastAction = capIntensityForRetreat(softPurr(0.2));
      return lastAction;
    }

    // Priority 5: Absent → idle
    if (obs.isAbsent) {
      explanation = 'Cat is absent. Agent is idle — never initiates when cat is not present.';
      lastAction = idle();
      return lastAction;
    }

    // Priority 2: Engaging with low stress → match and vary
    if (obs.isEngaging && obs.cssScore <= 3) {
      actionCycle = (actionCycle + 1) % 4;
      const intensity = 0.3 + (obs.cssScore <= 2 ? 0.2 : 0);
      switch (actionCycle) {
        case 0:
          explanation = 'Cat is engaged and relaxed. Slow blink to maintain affiliative bond.';
          lastAction = slowBlink(intensity);
          break;
        case 1:
          explanation = 'Cat is engaged. Soft trill to sustain interaction.';
          lastAction = trill(intensity);
          break;
        case 2:
          explanation = 'Cat is engaged. Soft purr for comfort signalling.';
          lastAction = softPurr(intensity);
          break;
        case 3:
          explanation = 'Cat is engaged. Brief pause to avoid overstimulation.';
          lastAction = pause(2000);
          break;
      }
      return lastAction;
    }

    // Priority 3: Alert/Curious → slow blink first
    if (obs.isCurious || obs.state === 'ALERT') {
      if (obs.vocalType === 'trill' || obs.vocalType === 'meow') {
        explanation = 'Cat is curious and vocalising. Responding with trill.';
        lastAction = trill(0.3);
      } else {
        explanation = 'Cat is alert/curious. Initiating slow blink (Humphrey et al. 2020).';
        lastAction = slowBlink(0.3);
      }
      return lastAction;
    }

    // Priority 3b: Approaching
    if (obs.isApproaching) {
      explanation = 'Cat is approaching. Slow blink to signal non-threat.';
      lastAction = slowBlink(0.35);
      return lastAction;
    }

    // Priority 4: Resting → gentle presence
    if (obs.isResting) {
      if (obs.distanceToAgent < 200) {
        explanation = 'Cat resting near agent. Soft purr at low intensity.';
        lastAction = softPurr(0.15);
      } else {
        explanation = 'Cat resting far from agent. Idle — do not disturb.';
        lastAction = idle();
      }
      return lastAction;
    }

    // Default: idle
    explanation = 'No clear interaction signal. Agent idle.';
    lastAction = idle();
    return lastAction;
  }

  function getExplanation(): string {
    return explanation;
  }

  function isInCooldown(): boolean {
    return cooldownUntilTick > lastTickCount;
  }

  function getCooldownRemainingTicks(): number {
    return Math.max(0, cooldownUntilTick - lastTickCount);
  }

  function reset(): void {
    cooldownUntilTick = 0;
    lastTickCount = 0;
    lastAction = idle();
    explanation = 'Agent is idle. Waiting for SimCat to enter the arena.';
    actionCycle = 0;
  }

  return { decide, getExplanation, isInCooldown, getCooldownRemainingTicks, reset };
}
