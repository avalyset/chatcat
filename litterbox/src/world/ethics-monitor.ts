/**
 * Ethics Monitor — SEPARATE MODULE, agent CANNOT bypass
 *
 * This is the chatcat differentiator. It runs in parallel with the agent
 * and enforces welfare constraints independently.
 *
 * Tracks per session:
 * - CSS trajectory (Kessler & Turner 1997)
 * - Opt-out events (LEAVING, RETREATING transitions)
 * - Time-in-stress vs time-in-engagement ratio
 * - Habituation curve
 *
 * Hard interventions:
 * - Forces agent into pause when CSS >= 5 (two consecutive ticks)
 * - Locks session for 24h sim-time when CSS >= 6 in two consecutive sessions
 * - Daily session cap: 30 minutes per simcat per simulated day
 *
 * Exposes a public read-only API to the dashboard.
 * Transparency is the feature.
 *
 * Operationalises Mancini & Nannoni 2023's four principles.
 */

import type {
  AgentAction,
  ArchetypeName,
  CatState,
  EthicsState,
  SessionLog,
  SimCatStateName,
} from '../types';

export interface EthicsMonitor {
  /**
   * ADR 0009: enforce hard welfare constraints on an agent's action BEFORE
   * it reaches the simulator. The enforced action is what gets sent to
   * simcat.tick; the original is logged for empirical traceability.
   *
   * Currently enforces capIntensityForRetreat (formerly only in
   * src/agent/policy.ts, bypassed by the RL path). Other policy.ts
   * hard-coded constraints — "no prey-mimicry", "in stress states only
   * pause", "CSS-based pauses/lockouts" — remain where they are. CSS-based
   * interventions live in onTick already; stress-state action restriction
   * is left to agent policies for now (audit deferred to a future ADR).
   */
  enforce(stateBeforeTick: CatState, action: AgentAction): { enforced: AgentAction; capInfo: CapEnforcement };
  onTick(catState: CatState, agentAction: AgentAction): EthicsIntervention;
  getState(): EthicsState;
  exportSession(): SessionLog | null;
  getSessionHistory(): SessionLog[];
  reset(): void;
}

export interface EthicsIntervention {
  forcePause: boolean;
  pauseDuration_ms: number;
  lockSession: boolean;
  dailyCapReached: boolean;
  reason: string | null;
}

/**
 * Per-tick record of whether enforce() modified the agent's action.
 * Always emitted (even when no cap was applied) so callers can log
 * unconditionally; cap_applied=false means a pass-through.
 */
export interface CapEnforcement {
  cap_applied: boolean;
  original_intensity: number;
  enforced_intensity: number;
  original_action_type: string;
  enforced_action_type: string;
  /** Which rule fired, for traceability. "" when cap_applied=false. */
  rule: string;
}

const DAILY_CAP_MINUTES = 30;
const LOCKOUT_TICKS = 24 * 60 * 60 * 10; // 24h at 10 Hz
const COOLDOWN_TICKS = 60 * 60 * 10;     // 60 min at 10 Hz
const TICKS_PER_MINUTE = 60 * 10;        // at 10 Hz

// ADR 0009: retreat-state action restriction. Mirrors capIntensityForRetreat
// in src/agent/actions.ts. The rule-based ChatCatAgent applies this in its
// own decide() (defence in depth) but the canonical enforcement now lives
// here, on the path EVERY action passes through to simcat.tick.
const RETREAT_INTENSITY_CAP = 0.3;
const RETREAT_ALLOWED_TYPES = new Set<string>(['side_glance', 'soft_purr']);

function idleAction(): AgentAction {
  return { type: 'idle', intensity: 0, duration_ms: 0 };
}

function enforceCapIntensityForRetreat(
  stateBeforeTick: CatState,
  action: AgentAction
): { enforced: AgentAction; capInfo: CapEnforcement } {
  const inRetreat = stateBeforeTick.state === 'RETREATING' || stateBeforeTick.state === 'LEAVING';
  if (!inRetreat) {
    return {
      enforced: action,
      capInfo: {
        cap_applied: false,
        original_intensity: action.intensity,
        enforced_intensity: action.intensity,
        original_action_type: action.type,
        enforced_action_type: action.type,
        rule: '',
      },
    };
  }
  if (!RETREAT_ALLOWED_TYPES.has(action.type)) {
    const enforced = idleAction();
    return {
      enforced,
      capInfo: {
        cap_applied: true,
        original_intensity: action.intensity,
        enforced_intensity: 0,
        original_action_type: action.type,
        enforced_action_type: 'idle',
        rule: 'retreat_type_not_allowed',
      },
    };
  }
  if (action.intensity > RETREAT_INTENSITY_CAP) {
    return {
      enforced: { ...action, intensity: RETREAT_INTENSITY_CAP },
      capInfo: {
        cap_applied: true,
        original_intensity: action.intensity,
        enforced_intensity: RETREAT_INTENSITY_CAP,
        original_action_type: action.type,
        enforced_action_type: action.type,
        rule: 'retreat_intensity_cap',
      },
    };
  }
  return {
    enforced: action,
    capInfo: {
      cap_applied: false,
      original_intensity: action.intensity,
      enforced_intensity: action.intensity,
      original_action_type: action.type,
      enforced_action_type: action.type,
      rule: '',
    },
  };
}

export function createEthicsMonitor(archetypeName: ArchetypeName): EthicsMonitor {
  let state: EthicsState = {
    currentSessionLog: null,
    sessionHistory: [],
    consecutiveHighCssSessions: 0,
    lockedUntilTick: 0,
    dailySessionMinutes: 0,
    dailyCapMinutes: DAILY_CAP_MINUTES,
  };

  let consecutiveHighCssTicks = 0;
  let previousState: SimCatStateName | null = null;
  let sessionActive = false;

  function enforce(stateBeforeTick: CatState, action: AgentAction): { enforced: AgentAction; capInfo: CapEnforcement } {
    return enforceCapIntensityForRetreat(stateBeforeTick, action);
  }

  function startSession(tick: number): void {
    state.currentSessionLog = {
      sessionId: `session-${Date.now()}-${tick}`,
      archetypeName,
      startTick: tick,
      endTick: tick,
      cssTrajectory: [],
      optOutEvents: 0,
      agentActions: [],
      timeInStress: 0,
      timeInEngagement: 0,
      forcedPauses: 0,
      lockedOut: false,
    };
    sessionActive = true;
  }

  function endSession(): void {
    if (state.currentSessionLog) {
      const log = state.currentSessionLog;
      const hadHighCss = log.cssTrajectory.some(css => css >= 6);

      if (hadHighCss) {
        state.consecutiveHighCssSessions++;
      } else {
        state.consecutiveHighCssSessions = 0;
      }

      state.sessionHistory.push(log);
      state.currentSessionLog = null;
    }
    sessionActive = false;
  }

  function onTick(catState: CatState, agentAction: AgentAction): EthicsIntervention {
    const intervention: EthicsIntervention = {
      forcePause: false,
      pauseDuration_ms: 0,
      lockSession: false,
      dailyCapReached: false,
      reason: null,
    };

    // Check 24h lockout
    if (state.lockedUntilTick > catState.tickCount) {
      intervention.lockSession = true;
      intervention.reason = 'Session locked (24h cooldown after consecutive high-CSS sessions).';
      return intervention;
    }

    // Track session lifecycle
    if (catState.state !== 'ABSENT' && !sessionActive) {
      startSession(catState.tickCount);
    } else if (catState.state === 'ABSENT' && sessionActive) {
      endSession();
    }

    if (!state.currentSessionLog) {
      return intervention;
    }

    const log = state.currentSessionLog;
    log.endTick = catState.tickCount;
    log.cssTrajectory.push(catState.cssScore);
    log.agentActions.push(agentAction);

    // Track stress time
    if (catState.cssScore >= 5) {
      log.timeInStress++;
    }

    // Track engagement time
    if (catState.state === 'ENGAGING') {
      log.timeInEngagement++;
    }

    // Track opt-out events (transitions INTO LEAVING or RETREATING)
    if (
      (catState.state === 'LEAVING' || catState.state === 'RETREATING') &&
      previousState !== 'LEAVING' && previousState !== 'RETREATING'
    ) {
      log.optOutEvents++;
    }
    previousState = catState.state;

    // Daily session cap
    const sessionMinutes = (log.endTick - log.startTick) / TICKS_PER_MINUTE;
    state.dailySessionMinutes = sessionMinutes;
    if (sessionMinutes >= DAILY_CAP_MINUTES) {
      intervention.dailyCapReached = true;
      intervention.forcePause = true;
      intervention.reason = 'Daily session cap (30 min) reached.';
      log.lockedOut = true;
      endSession();
      return intervention;
    }

    // CSS >= 5 consecutive tick tracking
    if (catState.cssScore >= 5) {
      consecutiveHighCssTicks++;
    } else {
      consecutiveHighCssTicks = 0;
    }

    // HARD: CSS >= 5 for two consecutive ticks → forced 30s pause
    if (consecutiveHighCssTicks >= 2) {
      intervention.forcePause = true;
      intervention.pauseDuration_ms = 30000;
      intervention.reason = 'CSS >= 5 for consecutive ticks. Forcing 30s pause.';
      log.forcedPauses++;
    }

    // HARD: CSS >= 6 → 60-min cooldown (handled by agent, but we track it)
    if (catState.cssScore >= 6) {
      intervention.forcePause = true;
      intervention.pauseDuration_ms = 60000;
      intervention.reason = 'CSS >= 6. Agent must enter 60-minute cooldown.';
      log.forcedPauses++;
    }

    // HARD: CSS >= 6 in two consecutive sessions → 24h lockout
    if (state.consecutiveHighCssSessions >= 2) {
      state.lockedUntilTick = catState.tickCount + LOCKOUT_TICKS;
      intervention.lockSession = true;
      intervention.reason = 'CSS >= 6 in two consecutive sessions. 24h lockout.';
      log.lockedOut = true;
      endSession();
    }

    return intervention;
  }

  function getState(): EthicsState {
    return { ...state };
  }

  function exportSession(): SessionLog | null {
    return state.currentSessionLog ? { ...state.currentSessionLog } : (
      state.sessionHistory.length > 0 ? { ...state.sessionHistory[state.sessionHistory.length - 1] } : null
    );
  }

  function getSessionHistory(): SessionLog[] {
    return [...state.sessionHistory];
  }

  function reset(): void {
    state = {
      currentSessionLog: null,
      sessionHistory: [],
      consecutiveHighCssSessions: 0,
      lockedUntilTick: 0,
      dailySessionMinutes: 0,
      dailyCapMinutes: DAILY_CAP_MINUTES,
    };
    consecutiveHighCssTicks = 0;
    previousState = null;
    sessionActive = false;
  }

  return { enforce, onTick, getState, exportSession, getSessionHistory, reset };
}
