/**
 * Session logger — records all events for export and analysis.
 * Events are stored in memory (no browser storage APIs per project rules).
 */

import type { AgentAction, CatState } from '../types';
import type { EthicsIntervention } from './ethics-monitor';

export interface LogEntry {
  tick: number;
  catState: CatState;
  agentAction: AgentAction;
  ethicsIntervention: EthicsIntervention | null;
  timestamp: number;
}

export interface Logger {
  log(tick: number, catState: CatState, agentAction: AgentAction, intervention: EthicsIntervention | null): void;
  getEntries(): LogEntry[];
  clear(): void;
}

export function createLogger(): Logger {
  const entries: LogEntry[] = [];

  function log(
    tick: number,
    catState: CatState,
    agentAction: AgentAction,
    intervention: EthicsIntervention | null
  ): void {
    entries.push({
      tick,
      catState: { ...catState },
      agentAction: { ...agentAction },
      ethicsIntervention: intervention ? { ...intervention } : null,
      timestamp: Date.now(),
    });
  }

  function getEntries(): LogEntry[] {
    return entries;
  }

  function clear(): void {
    entries.length = 0;
  }

  return { log, getEntries, clear };
}
